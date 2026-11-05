import logging
import math

logger = logging.getLogger(__name__)

class RateLimit429AnomalyRadar:
    """
    A radar module to detect anomalies in HTTP 429 rate limit queues.
    It identifies the top 3% of anomalous queue items using Z-Score,
    while ensuring zero-configuration, robust self-healing for dirty data,
    and returning a minimal, intuitive summary for the frontend.
    """

    @staticmethod
    def _clean_and_heal_data(items):
        """Silently clean dirty data and apply sensible defaults."""
        cleaned_items = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                logger.info(f"Item at index {index} is not a dict, skipping or converting. Type: {type(item)}")
                # If it's totally garbage, we skip or could wrap it, but let's just create a dummy dict
                item = {"original_data": item}

            queue_time = item.get("queue_time_ms", 0)

            # Heal queue_time_ms
            try:
                queue_time = float(queue_time)
                if math.isnan(queue_time) or math.isinf(queue_time):
                    queue_time = 0.0
                if queue_time < 0:
                    queue_time = 0.0
            except (ValueError, TypeError):
                queue_time = 0.0

            # Copy the original item and inject the cleaned queue_time_ms
            cleaned_item = dict(item)
            cleaned_item["queue_time_ms"] = queue_time
            cleaned_items.append(cleaned_item)

        return cleaned_items

    @staticmethod
    def _calculate_z_scores(cleaned_items):
        """Calculate Z-scores for all items based on queue_time_ms."""
        n = len(cleaned_items)
        if n == 0:
            return []

        times = [item["queue_time_ms"] for item in cleaned_items]
        mean = sum(times) / n

        # Calculate standard deviation
        if n > 1:
            variance = sum((t - mean) ** 2 for t in times) / (n - 1)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0

        logger.info(f"Calculated stats - Mean: {mean}, StdDev: {std_dev}")

        scored_items = []
        for item in cleaned_items:
            # If standard deviation is zero (all times are the same or only 1 item), z-score is 0
            z_score = 0.0 if std_dev == 0.0 else (item["queue_time_ms"] - mean) / std_dev

            scored_item = dict(item)
            scored_item["_z_score"] = z_score
            scored_items.append(scored_item)

        return scored_items

    def analyze_queues(self, items):
        """
        Analyze the queue items, identify anomalies, and return a simple summary.

        Args:
            items: A list of dictionaries representing queue items.

        Returns:
            A dictionary with a minimal frontend-friendly summary.
        """
        if not items or not isinstance(items, list):
            logger.info("Received empty or invalid items list.")
            return {
                "top_anomalies": [],
                "normal_items_count": 0,
                "status": "green"
            }

        logger.info(f"Starting analysis for {len(items)} items.")

        # 1. Clean and Heal Data
        cleaned_items = self._clean_and_heal_data(items)

        # 2. Calculate Statistics and Scores
        scored_items = self._calculate_z_scores(cleaned_items)

        # 3. Identify Top 3% Anomalies
        # Sort by z-score descending
        scored_items.sort(key=lambda x: x["_z_score"], reverse=True)

        total_items = len(scored_items)
        top_3_percent_count = max(1, int(math.ceil(total_items * 0.03))) if total_items >= 1 else 0

        anomalies = []
        normal_count = 0

        # For statistical anomalies we could use IQR or Z-score threshold.
        # But we only want to flag items as anomalies if they are significantly higher than the norm.
        # Z-score > 2 is a typical anomaly threshold. But let's say if z-score > 1.5 it is an anomaly.
        # wait, the test test_normal_data failed because some normal variations hit z-score > 1.5.
        # Uniform data from 100 to 109 has mean 104.5. max is 109. variance is ~8.25. std dev is ~2.87.
        # 109 - 104.5 = 4.5. 4.5 / 2.87 = 1.56 > 1.5.

        # We can use IQR to be robust.
        times = [item["queue_time_ms"] for item in cleaned_items]
        times.sort()
        n = len(times)

        q1 = times[int(n * 0.25)] if n > 0 else 0
        q3 = times[int(n * 0.75)] if n > 0 else 0
        iqr = q3 - q1

        upper_bound = q3 + 1.5 * iqr

        for i, item in enumerate(scored_items):
            # Must be in top 3% AND be an outlier by IQR method AND have high Z-score
            if i < top_3_percent_count and item["queue_time_ms"] > upper_bound and item["_z_score"] > 1.0:
                # Format for frontend
                frontend_anomaly = dict(item)
                # Remove internal tracking field
                del frontend_anomaly["_z_score"]
                frontend_anomaly["reason"] = "排队时间过长，可能需要人工关注"
                anomalies.append(frontend_anomaly)
            else:
                normal_count += 1

        # 4. Determine Status Color
        if len(anomalies) == 0:
            status = "green"
        elif len(anomalies) < top_3_percent_count:
            status = "yellow"
        else:
            status = "red"

        logger.info(f"Analysis complete. Anomalies found: {len(anomalies)}. Status: {status}")

        return {
            "top_anomalies": anomalies,
            "normal_items_count": normal_count,
            "status": status
        }
