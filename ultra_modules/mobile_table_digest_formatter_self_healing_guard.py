import json
import time

class MobileTableDigestFormatter:
    def __init__(self):
        self._snapshots = {}

    def format_digest(self, data, max_rows=3, default_title="Table Digest"):
        if data is None:
            data = []
        if not isinstance(data, list):
            try:
                data = list(data)
            except TypeError:
                data = []

        cleaned_data = []
        for row in data:
            if isinstance(row, dict):
                cleaned_data.append(row)
            elif isinstance(row, (list, tuple)):
                cleaned_data.append({f"col_{i}": v for i, v in enumerate(row)})
            else:
                cleaned_data.append({"value": row})

        anomalies = []
        digest_rows = []

        for i, row in enumerate(cleaned_data):
            has_anomaly = False
            # naive anomaly detection for demonstration
            for k, v in row.items():
                if v is None or v == "" or str(v).lower() in ("error", "null", "nan"):
                    has_anomaly = True
                    anomalies.append({"row": i, "column": k, "value": v})

            if len(digest_rows) < max_rows:
                digest_rows.append(row)

        snapshot_id = str(int(time.time() * 1000))
        self._snapshots[snapshot_id] = {
            "timestamp": time.time(),
            "original_data": data
        }

        # clean up old snapshots (older than 5 seconds)
        current_time = time.time()
        self._snapshots = {
            k: v for k, v in self._snapshots.items()
            if current_time - v["timestamp"] <= 5
        }

        return {
            "title": default_title,
            "digest": digest_rows,
            "anomalies": anomalies,
            "attachment_card": {
                "download_url": "#",
                "text": "Download Full Table"
            },
            "snapshot_id": snapshot_id
        }

    def undo(self, snapshot_id):
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return None
        if time.time() - snapshot["timestamp"] > 5:
            del self._snapshots[snapshot_id]
            return None
        return snapshot["original_data"]
