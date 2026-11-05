import math
from typing import List, Dict, Any, Optional

class AttachmentAutoRouterAnomalyRadar:
    """
    Attachment Auto Router & Anomaly Radar
    Routes attachments to specific processing engines based on filename,
    and performs statistical anomaly detection (Z-Score/IQR) on extracted data points.
    """

    def __init__(self):
        self.route_rules = {
            "周报": "WeeklyReportEngine",
            "提成": "CommissionEngine",
            "标书": "BidDocumentEngine",
            "漫剧": "ComicEngine"
        }
        self.default_engine = "DefaultFallbackEngine"

    def determine_route(self, filename: Optional[str]) -> str:
        """
        Determines the routing engine based on filename keywords.
        """
        if not filename or not isinstance(filename, str):
            return self.default_engine

        for keyword, engine in self.route_rules.items():
            if keyword in filename:
                return engine

        return self.default_engine

    def scan_anomalies(self, data_points: Optional[List[Any]]) -> List[Dict[str, Any]]:
        """
        Scans data points for statistical anomalies using Z-Score and IQR.
        Returns a list of items with RED/YELLOW/GREEN markers.
        Highlighting the Top 3% anomalies (and specifically Top 1% as RED, next 2% as YELLOW).
        The remaining 97% are silently passed as GREEN.
        """
        if data_points is None:
            return []

        parsed_data = []
        valid_values = []

        # 1. Dirty data self-healing and extraction
        for idx, item in enumerate(data_points):
            item_id = idx
            raw_val = item

            if isinstance(item, dict):
                item_id = item.get("id", idx)
                raw_val = item.get("value", None)

            healed_val = None
            is_valid = False

            if raw_val is not None:
                # Exclude booleans since they act as integers in Python but aren't metrics
                if not isinstance(raw_val, bool):
                    try:
                        if isinstance(raw_val, str):
                            clean_str = raw_val.strip().replace(',', '')
                            healed_val = float(clean_str)
                        else:
                            healed_val = float(raw_val)

                        # Handle extreme boundary conditions like inf and nan
                        if not math.isinf(healed_val) and not math.isnan(healed_val):
                            is_valid = True
                            valid_values.append(healed_val)
                    except (ValueError, TypeError):
                        pass

            parsed_data.append({
                "original_id": item_id,
                "raw_val": raw_val,
                "healed_val": healed_val,
                "is_valid": is_valid,
                "original_index": idx
            })

        n = len(valid_values)
        if n == 0:
            # Fallback for empty or completely invalid data
            return self._format_results(parsed_data, {})

        # 2. Statistical Computations (Mean, StdDev, IQR)
        mean = sum(valid_values) / n
        variance = sum((x - mean) ** 2 for x in valid_values) / n
        std_dev = math.sqrt(variance)

        sorted_vals = sorted(valid_values)

        def get_percentile(p: float) -> float:
            k = (n - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_vals[int(k)]
            return sorted_vals[int(f)] * (c - k) + sorted_vals[int(c)] * (k - f)

        q1 = get_percentile(0.25) if n > 1 else valid_values[0]
        q3 = get_percentile(0.75) if n > 1 else valid_values[0]
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # 3. Calculate deviation scores
        deviation_scores = []
        for item in parsed_data:
            if not item["is_valid"]:
                continue

            val = item["healed_val"]
            z_score = abs(val - mean) / std_dev if std_dev > 1e-9 else 0.0

            iqr_outlier = 1.0 if (val < lower_bound or val > upper_bound) else 0.0

            # Composite deviation score
            deviation = z_score + (iqr_outlier * 2.0)

            deviation_scores.append({
                "index": item["original_index"],
                "deviation": deviation,
                "val": val,
                "mean": mean
            })

        # 4. Rank anomalies and highlight Top 3%
        deviation_scores.sort(key=lambda x: x["deviation"], reverse=True)

        red_threshold_count = max(1, math.ceil(n * 0.01))
        yellow_threshold_count = max(1, math.ceil(n * 0.03))

        status_map = {}
        for rank, score_item in enumerate(deviation_scores):
            idx = score_item["index"]
            dev = score_item["deviation"]
            val = score_item["val"]
            mean_val = score_item["mean"]

            direction = "超高" if val > mean_val else "超低"

            if dev > 1.0: # Ensure it is genuinely somewhat anomalous
                if rank < red_threshold_count:
                    status_map[idx] = {
                        "status": "RED",
                        "reason": f"【高危异常】数值表现为{direction}，严重偏离正常基准（Z-Score/IQR双重触发），强烈建议人工介入核查！"
                    }
                elif rank < yellow_threshold_count:
                    status_map[idx] = {
                        "status": "YELLOW",
                        "reason": f"【轻微波动】数值处于{direction}边缘，表现出一定程度的异常，建议后续观测。"
                    }
                else:
                    status_map[idx] = {
                        "status": "GREEN",
                        "reason": "系统静默放行：数值在安全波动范围内（归属97%正常区间）。"
                    }
            else:
                status_map[idx] = {
                    "status": "GREEN",
                    "reason": "系统静默放行：未检测到明显异常。"
                }

        return self._format_results(parsed_data, status_map)

    def _format_results(self, parsed_data: List[Dict], status_map: Dict[int, Dict]) -> List[Dict[str, Any]]:
        results = []
        for item in parsed_data:
            idx = item["original_index"]
            if not item["is_valid"]:
                results.append({
                    "id": item["original_id"],
                    "value": item["raw_val"],
                    "status": "GREEN",
                    "reason": "系统静默放行：空值或非数字内容。"
                })
            else:
                status_info = status_map.get(idx, {
                    "status": "GREEN",
                    "reason": "系统静默放行：安全数据。"
                })
                results.append({
                    "id": item["original_id"],
                    "value": item["raw_val"],
                    "healed_value": item["healed_val"],
                    "status": status_info["status"],
                    "reason": status_info["reason"]
                })
        return results

    def process(self, filename: Optional[str] = None, data_points: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        End-to-end processing pipeline for a file and its data points.
        """
        engine = self.determine_route(filename)
        scan_results = self.scan_anomalies(data_points)

        return {
            "routed_engine": engine,
            "anomaly_scan_results": scan_results
        }
