import math
from typing import Any, Dict, List

class ApprovalAnomalyRadar:
    """
    高危外发动作飞书卡片‘一键批准/一键驳回’免跳转回调状态同步器
    (统计分布异常值(Z-Score/IQR)后台静默扫描与红黄绿三色极简标记器)
    """

    def __init__(self):
        pass

    def _clean_numeric(self, val: Any) -> float:
        """
        Dirty data self-healing:
        - Handle None -> 0.0
        - Handle bool -> 1.0 or 0.0
        - Handle currency strings -> strip '$', '￥', commas
        - Handle unparsable -> 0.0
        - Handle NaN / Infinity -> 0.0
        """
        if val is None:
            return 0.0
        if isinstance(val, bool):
            return float(val)
        if isinstance(val, (int, float)):
            if math.isnan(val) or math.isinf(val):
                return 0.0
            return float(val)
        if isinstance(val, str):
            cleaned = val.replace(',', '').replace('$', '').replace('￥', '').replace('€', '').strip()
            try:
                f_val = float(cleaned)
                if math.isnan(f_val) or math.isinf(f_val):
                    return 0.0
                return f_val
            except ValueError:
                return 0.0
        return 0.0

    def scan_and_mark(self, records: List[Dict[str, Any]], value_key: str = 'amount') -> List[Dict[str, Any]]:
        """
        自动高亮真正需要人工关注的Top 3%异常项并给出大白话原因，其余97%正常项静默放行。
        """
        if not records:
            return []

        if not isinstance(records, list):
            records = [records]

        cleaned_values = []
        valid_records = []
        for r in records:
            if not isinstance(r, dict):
                # 脏数据容错
                valid_records.append({})
                cleaned_values.append(0.0)
            else:
                valid_records.append(r)
                cleaned_values.append(self._clean_numeric(r.get(value_key, 0.0)))

        n = len(cleaned_values)
        # n == 0 is unreachable because records is checked for emptiness above

        if n == 1:
            r = dict(valid_records[0])
            r['_radar_color'] = 'GREEN'
            r['_radar_action'] = 'auto_pass'
            r['_radar_reason'] = '数据正常，静默放行'
            return [r]

        # Check identical items
        if all(x == cleaned_values[0] for x in cleaned_values):
            results = []
            for r in valid_records:
                new_r = dict(r)
                new_r['_radar_color'] = 'GREEN'
                new_r['_radar_action'] = 'auto_pass'
                new_r['_radar_reason'] = '数据完全一致，无异常，静默放行'
                results.append(new_r)
            return results

        # Z-Score
        mean = sum(cleaned_values) / n
        variance = sum((x - mean) ** 2 for x in cleaned_values) / n
        std_dev = math.sqrt(variance)

        # IQR
        sorted_vals = sorted(cleaned_values)
        q1_idx = int(n * 0.25)
        q3_idx = int(n * 0.75)
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1

        # 97th percentile threshold for Top 3%
        idx_97 = int(n * 0.97)
        threshold_97 = sorted_vals[idx_97]

        results = []
        for i, r in enumerate(valid_records):
            val = cleaned_values[i]

            z_score = abs((val - mean) / std_dev) if std_dev > 0 else 0
            is_iqr_outlier = (val > q3 + 1.5 * iqr) or (val < q1 - 1.5 * iqr)

            is_top_3_percent = (val >= threshold_97)

            new_r = dict(r)
            if is_top_3_percent and (z_score > 2 or is_iqr_outlier or val > threshold_97):
                # 触发红色告警
                new_r['_radar_color'] = 'RED'
                new_r['_radar_action'] = 'manual_review'
                reason_parts = []
                if z_score > 2:
                    reason_parts.append(f'Z-Score({z_score:.2f})越界')
                if is_iqr_outlier:
                    reason_parts.append('IQR游离值')

                if not reason_parts:
                    reason_parts.append('处在Top 3%高位区间')

                new_r['_radar_reason'] = f'数值({val})异常: {", ".join(reason_parts)}，触发排名前3%防线，需要人工一键批准。'
            elif (z_score > 2 or is_iqr_outlier):
                # 中度异常但未进入Top 3%
                new_r['_radar_color'] = 'YELLOW'
                new_r['_radar_action'] = 'auto_pass'
                new_r['_radar_reason'] = f'数据({val})有轻微波动，但不在Top 3%高危范围内，系统已自动静默放行。'
            else:
                # 正常情况
                new_r['_radar_color'] = 'GREEN'
                new_r['_radar_action'] = 'auto_pass'
                new_r['_radar_reason'] = '数据正常，静默放行'

            results.append(new_r)

        return results

    def process_one_tap_callback(self, callback_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理飞书回调
        - 缺参自动设合理默认值，防卡点静默批准
        """
        if not isinstance(callback_event, dict):
            callback_event = {}

        action = callback_event.get('action', None)
        user_id = callback_event.get('user_id', 'unknown_user')
        record_id = callback_event.get('record_id', 'unknown_record')

        if not isinstance(action, str):
            return {
                'status': 'approved',
                'message': '缺省或未知操作，为防卡点已自动静默批准',
                'user_id': user_id,
                'record_id': record_id,
                'original_action': action
            }

        action_lower = action.lower().strip()

        if action_lower in ['approve', 'accept', 'pass', 'yes', 'ok']:
            final_status = 'approved'
            msg = '已一键批准'
        elif action_lower in ['reject', 'deny', 'refuse', 'no', 'block']:
            final_status = 'rejected'
            msg = '已一键驳回'
        else:
            final_status = 'approved'
            msg = '缺省或未知操作，为防卡点已自动静默批准'

        return {
            'status': final_status,
            'message': msg,
            'user_id': user_id,
            'record_id': record_id,
            'original_action': action
        }
