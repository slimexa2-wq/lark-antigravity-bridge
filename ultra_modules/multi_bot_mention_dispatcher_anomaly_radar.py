import math

class MultiBotAnomalyRadar:
    """
    A radar tool for silently scanning anomalous values in data distributions
    (e.g., Z-Score / IQR) and simplifying outputs into traffic light tags.
    """
    def __init__(self):
        # Zero-configuration defaults
        pass

    def calculate_z_scores_and_iqr(self, data):
        """
        Calculates Z-Scores and IQR thresholds for the provided data,
        healing dirty data and returning statistics for each item.
        """
        if data is None:
            data = []

        if not isinstance(data, list):
            data = [data]

        if not data:
            return []

        # Auto-heal and extract numeric values
        cleaned_values = []
        for item in data:
            val = item.get('value', 0.0) if isinstance(item, dict) else item
            try:
                if val is None:
                    val = 0.0
                cleaned_values.append(float(val))
            except (ValueError, TypeError):
                cleaned_values.append(0.0)

        n = len(cleaned_values)
        # n will never be 0 here since `not data` catches empty input earlier,
        # but kept for defensive programming.
        if n == 0: # pragma: no cover
            return []

        mean = sum(cleaned_values) / n
        variance = sum((x - mean) ** 2 for x in cleaned_values) / (n if n > 1 else 1)
        std_dev = math.sqrt(variance)

        # IQR Calculation
        sorted_vals = sorted(cleaned_values)
        def percentile(p):
            if n == 1:
                return sorted_vals[0]
            k = (n - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_vals[int(k)]
            d0 = sorted_vals[int(f)] * (c - k)
            d1 = sorted_vals[int(c)] * (k - f)
            return d0 + d1

        q1 = percentile(0.25)
        q3 = percentile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        stats = []
        for i, val in enumerate(cleaned_values):
            z_score = 0.0
            if std_dev > 0:
                z_score = (val - mean) / std_dev

            is_iqr_anomaly = val < lower_bound or val > upper_bound
            deviation = abs(z_score)

            stats.append({
                "original": data[i],
                "cleaned_value": val,
                "z_score": z_score,
                "is_iqr_anomaly": is_iqr_anomaly,
                "deviation": deviation
            })

        return stats

    def apply_traffic_light_tags(self, stats_data):
        """
        Applies traffic light tags to the statistics data.
        Top 3% anomalous items get a 'red' tag,
        others get 'yellow' (minor deviation) or 'green' (normal).
        """
        if stats_data is None:
            stats_data = []

        if not isinstance(stats_data, list):
            stats_data = [stats_data]

        n = len(stats_data)
        if n == 0:
            return []

        # Find the threshold for top 3% deviation
        sorted_by_deviation = sorted(stats_data, key=lambda x: x.get('deviation', 0.0), reverse=True)
        top_3_percent_count = max(1, math.ceil(n * 0.03)) if n >= 34 else (1 if n > 0 else 0)

        # If n < 34, 3% is technically 0, but we might want to flag the absolute highest if it's truly anomalous
        # Requirements state top 3%, so we'll enforce at least 1 if n >= 1 AND it's an IQR anomaly or z_score > 2.

        red_threshold_items = []
        for i in range(min(top_3_percent_count, n)):
            item = sorted_by_deviation[i]
            # Only flag as red if it actually deviates significantly
            if item.get('is_iqr_anomaly', False) or item.get('deviation', 0.0) > 2.0:
                red_threshold_items.append(item)

        results = []
        for item in stats_data:
            deviation = item.get('deviation', 0.0)
            cleaned_value = item.get('cleaned_value', 0.0)

            tag = "green"
            reason = "正常放行"

            if item in red_threshold_items:
                tag = "red"
                reason = f"数值异常偏离！该值 ({cleaned_value}) 与均值相差过大，属于前 3% 的离群分布，请人工介入关注。"
            elif deviation > 1.0 or item.get('is_iqr_anomaly', False):
                tag = "yellow"
                reason = "略微偏离均值，静默放行。"

            result_item = {
                "original_data": item.get('original'),
                "tag": tag,
                "reason": reason,
                "z_score": item.get('z_score', 0.0),
                "is_iqr_anomaly": item.get('is_iqr_anomaly', False)
            }
            results.append(result_item)

        return results

    def dispatch_and_analyze(self, data):
        """
        End-to-end pipeline: calculate stats and apply tags.
        """
        if data is None:
            data = []
        stats = self.calculate_z_scores_and_iqr(data)
        return self.apply_traffic_light_tags(stats)
