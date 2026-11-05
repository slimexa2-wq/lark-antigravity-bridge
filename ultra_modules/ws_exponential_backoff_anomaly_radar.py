import random
import math

class WSRecoveryRadar:
    """
    A class for managing WebSocket recovery using exponential backoff with jitter,
    and analyzing metrics to detect anomalies.
    """

    def __init__(self, base_delay=1.0, max_delay=60.0):
        try:
            self.base_delay = float(base_delay)
            if self.base_delay <= 0 or math.isnan(self.base_delay) or math.isinf(self.base_delay):
                self.base_delay = 1.0
        except (ValueError, TypeError):
            self.base_delay = 1.0

        try:
            self.max_delay = float(max_delay)
            if self.max_delay <= 0 or math.isnan(self.max_delay) or math.isinf(self.max_delay):
                self.max_delay = 60.0
        except (ValueError, TypeError):
            self.max_delay = 60.0

        if self.base_delay > self.max_delay:
            self.base_delay, self.max_delay = self.max_delay, self.base_delay

    def calculate_backoff(self, retry_count):
        """
        Calculates the backoff time for a given retry count using exponential backoff
        with full jitter.
        """
        try:
            retry_count = int(retry_count)
            if retry_count < 0:
                retry_count = 0
        except (ValueError, TypeError):
            retry_count = 0

        # Exponential backoff: base_delay * 2^retry_count
        # To avoid extremely large numbers before capping, we cap the exponent
        if retry_count > 30:
            retry_count = 30

        exponential_delay = self.base_delay * (2 ** retry_count)
        capped_delay = min(exponential_delay, self.max_delay)

        # Apply full jitter
        jitter_delay = random.uniform(0, capped_delay)
        return jitter_delay

    def analyze_metrics(self, metrics):
        """
        Analyzes a list of numerical metrics to identify the top anomalies.
        Returns a list of dictionaries, each containing the 'value', 'status',
        and 'reason' (if anomalous).
        Highlights the top 3% anomalies (approx Z > 1.88) with plain text reason.
        Silently cleans dirty data.
        """
        if not isinstance(metrics, (list, tuple)):
            return []

        clean_metrics = []
        original_data = []

        # Silently clean dirty data
        for m in metrics:
            try:
                val = float(m)
                if not math.isnan(val) and not math.isinf(val):
                    clean_metrics.append(val)
                    original_data.append({'value': val, 'original': m})
                else:
                    # Ignore NaN and Inf quietly
                    pass
            except (ValueError, TypeError):
                # Ignore non-convertible data quietly
                pass

        n = len(clean_metrics)
        if n == 0:
            return []

        if n < 3:
            # Cannot calculate standard deviation properly or meaningful Z-score
            return [{'value': item['value'], 'status': 'green'} for item in original_data]

        mean = sum(clean_metrics) / n
        variance = sum((x - mean) ** 2 for x in clean_metrics) / n
        std_dev = math.sqrt(variance)

        results = []

        for item in original_data:
            val = item['value']

            if std_dev == 0:
                results.append({'value': val, 'status': 'green'})
                continue

            z_score = abs(val - mean) / std_dev

            # Highlight top ~3% anomalies (Z > 1.88 roughly corresponds to top 3% tail in normal distribution)
            if z_score > 1.88:
                reason = f"偏离正常指标极值(Z-Score: {z_score:.2f} > 1.88)，需人工关注"
                results.append({
                    'value': val,
                    'status': 'red',
                    'reason': reason
                })
            else:
                results.append({'value': val, 'status': 'green'})

        return results
