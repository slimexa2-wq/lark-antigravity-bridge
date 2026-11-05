import math

class AdaptiveStreamThrottlerExportFormatter:
    """
    Feishu/Lark stream adaptive throttler & export formatter.
    Implements a monotonic sequence lock and dynamic window sizing.
    """

    def __init__(self):
        self._last_sequence = 0
        self._min_window = 150
        self._max_window = 500

    def _clean_data(self, data):
        """Recursively clean dirty data: replace NaN and None with 0."""
        if isinstance(data, dict):
            return {k: self._clean_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_data(v) for v in data]
        elif data is None:
            return 0
        elif isinstance(data, float) and math.isnan(data):
            return 0
        else:
            return data

    def process_and_format(self, data=None, window=300, sequence=None):
        # 1. Missing parameter fallback & type checking
        if data is None:
            data = {}
        if not isinstance(data, dict):
            data = {"value": data}

        # 2. Adaptive window clamping
        try:
            window = float(window)
            if math.isnan(window):
                window = 300
        except (ValueError, TypeError):
            window = 300

        window = max(self._min_window, min(self._max_window, int(window)))

        # 3. Sequence lock
        try:
            seq = int(sequence) if sequence is not None else 0
        except (ValueError, TypeError):
            seq = 0

        if seq <= self._last_sequence:
            seq = self._last_sequence + 1

        self._last_sequence = seq

        # 4. Dirty data cleaning
        cleaned_data = self._clean_data(data)

        # 5. Force comments=0
        cleaned_data['comments'] = 0

        # 6. Generate 3-line minimalist report
        # We need a predictable short report text.
        report = (
            f"🚀 [Stream Export] Sequence: {seq}\n"
            f"⏱️ Adaptive Window: {window}ms\n"
            f"✅ Data Cleaned & Ready"
        )

        return {
            "data": cleaned_data,
            "window": window,
            "sequence": seq,
            "report": report
        }

# Global instance for one-click access
_global_formatter = AdaptiveStreamThrottlerExportFormatter()

def format_export(data=None, window=300, sequence=None):
    """
    One-click export formatter.
    Zero-configuration, automatically falls back on missing params.
    """
    return _global_formatter.process_and_format(data=data, window=window, sequence=sequence)
