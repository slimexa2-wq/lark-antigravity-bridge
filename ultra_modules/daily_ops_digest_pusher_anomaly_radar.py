import math
from typing import Any, Dict, List

class DailyOpsDigestPusherAnomalyRadar:
    """
    Daily Ops Digest Pusher Anomaly Radar.
    Provides a simple interface to scan a list of items for anomalies.
    """

    def __init__(self):
        pass

    def _clean_data(self, data: Any, value_key: str) -> List[Dict[str, Any]]:
        """
        Silently cleans dirty data.
        Returns a list of valid dictionaries with float values.
        """
        if not isinstance(data, list):
            return []

        cleaned = []
        for item in data:
            if not isinstance(item, dict):
                continue

            val = item.get(value_key)
            if val is None:
                val = 0.0

            try:
                # Convert to float
                val = float(val)
                # Handle inf and nan
                if math.isinf(val) or math.isnan(val):
                    val = 0.0
            except (ValueError, TypeError):
                val = 0.0

            new_item = item.copy()
            new_item[value_key] = val
            cleaned.append(new_item)

        return cleaned

    def analyze(self, data: Any = None, value_key: str = 'value', name_key: str = 'name') -> List[Dict[str, Any]]:
        """
        Main entry point for anomaly scanning.
        """
        if data is None:
            data = []

        cleaned_data = self._clean_data(data, value_key)

        if not cleaned_data:
            return []

        values = [item[value_key] for item in cleaned_data]
        n = len(values)

        # Calculate mean and standard deviation
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n
        std_dev = math.sqrt(variance)

        # Calculate IQR
        sorted_values = sorted(values)

        def percentile(p):
            k = (n - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_values[int(k)]
            d0 = sorted_values[int(f)] * (c - k)
            d1 = sorted_values[int(c)] * (k - f)
            return d0 + d1

        if n >= 2:
            q1 = percentile(0.25)
            q3 = percentile(0.75)
            iqr = q3 - q1
        else:
            q1, q3, iqr = values[0], values[0], 0.0

        # Mark each item based on deviation
        results = []
        for item in cleaned_data:
            val = item[value_key]

            # Use z-score if std_dev > 0, else IQR, else fallback
            if std_dev > 0:
                score = abs((val - mean) / std_dev)
                # To get top 3% roughly, we can use a z-score threshold (e.g., 2.17 for ~3% tails, but let's strictly sort or use thresholds)
            else:
                score = 0.0

            # If we need exact top 3%, we should sort by score
            item['_anomaly_score'] = score
            results.append(item)

        # Determine exact top 3% anomalies if possible based on counts
        # Top 3% logic
        top_3_count = max(1, math.ceil(n * 0.03)) if n > 0 else 0

        # Sort by score descending
        results.sort(key=lambda x: x['_anomaly_score'], reverse=True)

        for i, item in enumerate(results):
            score = item['_anomaly_score']
            name = item.get(name_key, 'Unknown')
            val = item.get(value_key, 0.0)

            if i < top_3_count and (score > 1.0 or iqr > 0 and (val > q3 + 1.5 * iqr or val < q1 - 1.5 * iqr)):
                # Red: Top 3% and significantly far (Z-score > 1.0 or IQR outlier)
                item['status'] = 'Red'
                item['reason'] = f"{name}的数值({val})异常偏离群体(平均值:{mean:.2f})"
            elif i < top_3_count * 2 and (score > 0.5 or iqr > 0 and (val > q3 + 0.5 * iqr or val < q1 - 0.5 * iqr)):
                # Yellow: Near-miss anomalies
                item['status'] = 'Yellow'
                item['reason'] = f"{name}的数值({val})存在偏离趋势，建议关注"
            else:
                # Green: Quiet pass
                item['status'] = 'Green'
                item['reason'] = "正常"

            # Remove temporary score
            del item['_anomaly_score']

        # Restore original order if desired, or keep sorted by severity. Let's keep sorted by severity for easy reading.
        return results
