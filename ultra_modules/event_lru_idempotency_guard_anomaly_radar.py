import collections
import time
import uuid

class EventLRUIdempotencyGuardAnomalyRadar:
    """
    Feishu Webhook Event LRU Idempotency Guard & Anomaly Radar.
    Provides thousand-level LRU deduplication, IQR-based anomaly scanning for the top 3% abnormal items,
    and a very simple entry point with silent data self-healing and zero configuration.
    """

    def __init__(self, max_lru_size=1000):
        self.max_lru_size = max_lru_size
        self.lru_cache = collections.OrderedDict()
        self.history_metrics = []  # Stores historical metric values (e.g., event processing time or payload size) to compute IQR

    def _heal_dirty_data(self, event_data):
        if not isinstance(event_data, dict):
            event_data = {}

        # Self-healing: if event_id and message_id are missing, try to generate one to avoid crash,
        # but mark it as auto-generated if we want to trace it.
        # Often events have either 'event_id' or a nested header 'event_id'
        event_id = event_data.get('event_id') or event_data.get('header', {}).get('event_id') or event_data.get('message_id')
        if not event_id:
            event_id = f"auto-healed-{uuid.uuid4().hex}"

        metric_value = event_data.get('metric_value', 0.0)
        try:
            metric_value = float(metric_value)
        except (ValueError, TypeError):
            metric_value = 0.0

        return {
            'event_id': str(event_id),
            'metric_value': metric_value,
            'raw_data': event_data
        }

    def _update_history_and_detect_anomaly(self, metric_value):
        """
        Uses IQR to detect top 3% anomalies in a simplified way.
        If metric_value is an outlier, return True and the reason.
        """
        self.history_metrics.append(metric_value)
        # Keep history bounded for memory safety
        if len(self.history_metrics) > self.max_lru_size:
            self.history_metrics.pop(0)

        n = len(self.history_metrics)
        if n < 10:
            return False, ""

        sorted_metrics = sorted(self.history_metrics)
        q1_index = int(n * 0.25)
        q3_index = int(n * 0.75)
        q1 = sorted_metrics[q1_index]
        q3 = sorted_metrics[q3_index]
        iqr = q3 - q1

        # We want to identify the top 3% anomalies.
        # A standard IQR outlier threshold is Q3 + 1.5 * IQR.
        # For top 3%, we dynamically check if the value is in the top 3% of the sorted list
        # OR if it exceeds an upper bound. Let's use a hybrid approach.

        top_3_percent_index = max(0, int(n * 0.97))
        # Important: Don't use the just-inserted anomaly to raise the threshold so much that it's no longer an anomaly
        # If n > 10, we can use the previous n-1 elements to determine the threshold for this element.
        prev_n = n - 1
        prev_sorted_metrics = sorted_metrics[:-1]
        prev_q1 = prev_sorted_metrics[int(prev_n * 0.25)]
        prev_q3 = prev_sorted_metrics[int(prev_n * 0.75)]
        prev_iqr = prev_q3 - prev_q1
        prev_top_3_index = max(0, int(prev_n * 0.97))
        prev_threshold_top_3 = prev_sorted_metrics[prev_top_3_index]

        upper_bound = max(prev_q3 + 1.5 * prev_iqr, prev_threshold_top_3)

        if metric_value > upper_bound and metric_value > 0:
            return True, "指标数值显著高于历史97%的正常水位，涉嫌异常飙高"

        return False, ""

    def process_event(self, event_data=None):
        """
        Extremely simple entry point.
        Returns a dict with status and color tags.
        """
        if event_data is None:
            event_data = {}

        healed_data = self._heal_dirty_data(event_data)
        event_id = healed_data['event_id']
        metric_value = healed_data['metric_value']

        # 1. Idempotency Check (LRU)
        if event_id in self.lru_cache:
            # Move to end to mark as recently used
            self.lru_cache.move_to_end(event_id)
            return {
                "status": "ignored",
                "color": "yellow",
                "reason": "重复的事件，已防重放拦截",
                "event_id": event_id
            }

        # Add to LRU
        self.lru_cache[event_id] = time.time()
        if len(self.lru_cache) > self.max_lru_size:
            self.lru_cache.popitem(last=False)

        # 2. Anomaly Radar Scan
        is_anomaly, anomaly_reason = self._update_history_and_detect_anomaly(metric_value)

        if is_anomaly:
            return {
                "status": "flagged",
                "color": "red",
                "reason": f"需要人工关注: {anomaly_reason}",
                "event_id": event_id
            }

        # 97% normal items silently pass
        return {
            "status": "processed",
            "color": "green",
            "reason": "正常处理放行",
            "event_id": event_id
        }
