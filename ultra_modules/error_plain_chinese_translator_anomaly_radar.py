import statistics
from typing import List, Dict, Any, Optional

class ErrorAnomalyRadar:
    """
    后台堆栈报错自动翻译为大白话原因说明与一键自愈建议卡片生成器
    (统计分布异常值(Z-Score/IQR)后台静默扫描与红黄绿三色极简标记器)
    """

    def __init__(self):
        self.error_translations = {
            "NullPointerException": {
                "reason": "遇到了空指针异常，通常是因为代码试图访问一个不存在的对象。",
                "suggestion": "请检查相关变量是否已被正确初始化。"
            },
            "TimeoutError": {
                "reason": "请求超时，可能是网络延迟或服务器响应过慢导致。",
                "suggestion": "建议增加超时时间或检查网络连通性。"
            }
        }

        self.default_translation = {
            "reason": "发生了未知错误。",
            "suggestion": "请查看详细的后台日志以获取更多线索。"
        }

    def _clean_data(self, item: Any) -> Dict[str, Any]:
        """
        Dirty data self-healing.
        """
        if not isinstance(item, dict):
            return {"error_msg": str(item), "severity": 0.0}

        cleaned = dict(item)

        # Heal severity
        raw_severity = cleaned.get("severity", 0.0)
        if raw_severity is None:
            cleaned["severity"] = 0.0
        else:
            try:
                cleaned["severity"] = float(raw_severity)
            except (ValueError, TypeError):
                cleaned["severity"] = 0.0

        # Ensure error_msg exists
        if "error_msg" not in cleaned or not isinstance(cleaned["error_msg"], str):
            cleaned["error_msg"] = str(cleaned.get("error_msg", "Unknown error"))

        return cleaned

    def scan_and_translate(self, errors: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        自动高亮真正需要人工关注的Top 3%异常项并给出大白话原因，其余97%正常项静默放行。
        """
        if errors is None or not isinstance(errors, list):
            return []

        if not errors:
            return []

        cleaned_errors = [self._clean_data(err) for err in errors]

        severities = [err["severity"] for err in cleaned_errors]

        if len(severities) < 2:
            # Not enough data for statistics, treat all as green or handle individually
            for err in cleaned_errors:
                err["color"] = "green"
            return cleaned_errors

        # We calculate the thresholds for 97th percentile and 90th percentile
        sorted_severities = sorted(severities)
        n = len(sorted_severities)

        # Calculate indexes for percentiles
        idx_97 = max(0, int(0.97 * n) - 1)
        idx_90 = max(0, int(0.90 * n) - 1)

        threshold_97 = sorted_severities[idx_97]
        threshold_90 = sorted_severities[idx_90]

        # Note: we also want strictly top 3% to be red if we sort by severity.
        # But if all severities are equal, percentiles might overlap.
        # Let's mark exactly by slicing if there are enough elements, or use threshold if we want to handle ties.
        # To be robust with ties and exact counts:

        # Alternative: sort the original items by severity descending
        # Top 3% are red, next 7% are yellow, remaining are green.
        # But order of items should probably be preserved.

        # Let's count how many to mark red/yellow based on length
        num_red = max(1, int(n * 0.03)) if int(n * 0.03) > 0 else (1 if n >= 34 else 0) # 1 if n >= 34, else based on percentile or strict rank?
        # Actually, let's use a strict ranking approach to ensure exactly top 3% (rounded) are red.
        num_red = round(n * 0.03)
        num_yellow = round(n * 0.10) - num_red

        # To handle boundary conditions elegantly and deterministically, we sort by severity (desc) and index (to maintain stable sort)
        indexed_errors = list(enumerate(cleaned_errors))
        indexed_errors.sort(key=lambda x: (x[1]["severity"], x[0]), reverse=True)

        for i, (original_idx, err) in enumerate(indexed_errors):
            if i < num_red:
                err["color"] = "red"
                self._enrich_translation(err)
            elif i < num_red + num_yellow:
                err["color"] = "yellow"
            else:
                err["color"] = "green"

        return cleaned_errors

    def _enrich_translation(self, err: Dict[str, Any]) -> None:
        """
        Enrich error with plain Chinese explanation.
        """
        error_msg = err.get("error_msg", "")

        matched = False
        for key, trans in self.error_translations.items():
            if key in error_msg:
                err["plain_chinese_reason"] = trans["reason"]
                err["self_healing_suggestion"] = trans["suggestion"]
                matched = True
                break

        if not matched:
            err["plain_chinese_reason"] = self.default_translation["reason"]
            err["self_healing_suggestion"] = self.default_translation["suggestion"]
