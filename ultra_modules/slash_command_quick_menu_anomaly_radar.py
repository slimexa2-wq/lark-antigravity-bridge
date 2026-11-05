import math
import statistics
from typing import List, Dict, Any, Union

class AnomalyRadar:
    """
    飞书免记指令极简快捷菜单异常项雷达（/周报 /提成 /漫剧 /标书 /状态）
    静默扫描统计分布异常值(Z-Score)，高亮Top 3%或绝对异常项，其余静默放行。
    要求极致容错：缺参自动设合理默认值，脏数据自愈。
    """

    def __init__(self, anomaly_threshold: float = None, top_percentile: float = None):
        """
        初始化雷达
        :param anomaly_threshold: Z-Score绝对异常阈值，默认2.0
        :param top_percentile: Top异常比例，默认0.03 (3%)
        """
        # 缺参自动设合理默认值，零配置容错
        self.anomaly_threshold = anomaly_threshold if anomaly_threshold is not None else 2.0
        self.top_percentile = top_percentile if top_percentile is not None else 0.03

        # 脏数据自愈，确保配置合法性
        if not isinstance(self.anomaly_threshold, (int, float)):
            self.anomaly_threshold = 2.0

        if not isinstance(self.top_percentile, (int, float)) or not (0 < self.top_percentile < 1):
            self.top_percentile = 0.03

    def _clean_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        内部静默清理脏数据：剔除/修复非数字、缺失值
        """
        cleaned = []
        if not data or not isinstance(data, list):
            return cleaned

        for item in data:
            if not isinstance(item, dict):
                continue

            # 如果没有值字段，补齐默认值0
            val = item.get("value", 0)

            # 处理字符串类型的数字
            if isinstance(val, str):
                try:
                    val = float(val)
                except ValueError:
                    val = 0.0

            # 处理非数字类型(如None, 列表等)
            if not isinstance(val, (int, float)):
                val = 0.0

            cleaned.append({
                "id": item.get("id", "unknown"),
                "name": item.get("name", "未命名"),
                "value": float(val),
                "original": item # 保留原始数据以备回溯
            })

        return cleaned

    def scan(self, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        一键触发雷达扫描，返回极简的标记结果

        返回格式:
        {
            "anomalies": [
                {"id": "...", "name": "...", "value": 100, "status": "red", "reason": "异常原因大白话"}
            ],
            "normal_count": 97,
            "status": "green"  # 整体状态
        }
        """
        # 1. 脏数据自愈清洗
        cleaned_data = self._clean_data(raw_data)

        # 空数据边界处理
        if not cleaned_data:
            return {
                "anomalies": [],
                "normal_count": 0,
                "status": "green"
            }

        # 极少数据边界处理：无法计算有意义的Z-Score
        if len(cleaned_data) < 3:
            return {
                "anomalies": [],
                "normal_count": len(cleaned_data),
                "status": "green"
            }

        # 2. 核心数学统计 (静默计算，后端复杂)
        values = [item["value"] for item in cleaned_data]
        mean = statistics.mean(values)
        try:
            stdev = statistics.stdev(values)
        except statistics.StatisticsError:
            stdev = 0.0

        # 标准差极小的情况(数值全一样)，直接全部视为正常
        if stdev < 1e-6:
            return {
                "anomalies": [],
                "normal_count": len(cleaned_data),
                "status": "green"
            }

        # 3. 计算Z-Score和绝对偏离
        scored_data = []
        for item in cleaned_data:
            val = item["value"]
            z_score = (val - mean) / stdev
            item["z_score"] = z_score
            item["abs_z_score"] = abs(z_score)
            scored_data.append(item)

        # 4. 识别Top 3% 或 绝对异常项
        # 按照异常程度(abs_z_score)降序排列
        scored_data.sort(key=lambda x: x["abs_z_score"], reverse=True)

        # 确定Top比例的数量上限
        top_k_count = max(1, int(math.ceil(len(scored_data) * self.top_percentile)))

        anomalies = []
        normal_count = 0

        for i, item in enumerate(scored_data):
            # 满足两个条件之一即视为异常：
            # 1. 位于Top K 且 超过了一定绝对阈值(防止全正常数据集硬挑异常)
            # 2. 或者超出了极其严重的异常阈值(即使不在Top K内，比如极端离群)
            is_anomaly = False

            if i < top_k_count and item["abs_z_score"] >= self.anomaly_threshold:
                is_anomaly = True
            elif item["abs_z_score"] >= self.anomaly_threshold * 1.5:
                # 极端离群点
                is_anomaly = True

            if is_anomaly:
                # 赋予极简大白话解释
                if item["z_score"] > 0:
                    reason = f"数值过高，超出均值水平 {item['z_score']:.1f} 倍标准差，需重点关注其合规性或爆款潜力"
                    status = "red"
                else:
                    reason = f"数值过低，低于均值水平 {abs(item['z_score']):.1f} 倍标准差，需排查是否漏报、消极怠工或故障"
                    status = "yellow"

                anomalies.append({
                    "id": item["id"],
                    "name": item["name"],
                    "value": item["value"],
                    "status": status,
                    "reason": reason
                })
            else:
                normal_count += 1

        # 前端极简返回组装
        overall_status = "red" if any(a["status"] == "red" for a in anomalies) else ("yellow" if anomalies else "green")

        return {
            "anomalies": anomalies,
            "normal_count": normal_count,
            "status": overall_status
        }
