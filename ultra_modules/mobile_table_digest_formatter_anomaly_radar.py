import json
import statistics
from typing import List, Dict, Any, Tuple, Optional


class MobileTableDigestFormatterAnomalyRadar:
    """
    Identifies the top 3% anomalies in a dataset using Z-Score/IQR and
    generates a Lark Card V2 representation with a 3-line core summary,
    a collapsible panel for anomalies, and an attachment download button.
    """

    def __init__(self, anomaly_threshold_percent: float = 0.03):
        self.anomaly_threshold_percent = anomaly_threshold_percent

    def _clean_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Self-heals dirty data by ensuring 'value' exists and is a float.
        """
        cleaned = []
        for item in data:
            if not isinstance(item, dict):
                continue

            val = item.get("value")
            name = item.get("name", "Unknown")

            if val is None:
                continue

            try:
                # Convert value to float, ignoring non-numeric strings
                clean_val = float(val)
                cleaned.append({"name": str(name), "value": clean_val})
            except (ValueError, TypeError):
                continue

        return cleaned

    def _detect_anomalies(self, data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Detects anomalies using Z-Score/IQR and returns (anomalies, normal).
        Identifies top ~3% anomalies.
        """
        if not data:
            return [], []

        values = [item["value"] for item in data]
        n = len(values)

        if n < 3:
             # Not enough data for stats, consider all normal
             return [], data

        mean_val = statistics.mean(values)
        try:
            stdev_val = statistics.stdev(values)
        except statistics.StatisticsError:
            stdev_val = 0.0

        # If all values are the same, no anomalies
        if stdev_val == 0:
            return [], data

        # Calculate Z-Scores
        scored_data = []
        for item in data:
            z_score = abs(item["value"] - mean_val) / stdev_val
            scored_data.append((z_score, item))

        # Sort by z-score descending
        scored_data.sort(key=lambda x: x[0], reverse=True)

        # Calculate how many items constitute the top 3% (minimum 1 if any exists, but bounded by Z-score threshold typically)
        # We also enforce a Z-Score threshold (e.g. > 1.5) to be considered an anomaly
        anomalies = []
        normal = []

        target_anomaly_count = max(1, int(n * self.anomaly_threshold_percent))

        for z_score, item in scored_data:
            if len(anomalies) < target_anomaly_count and z_score > 1.5:
                # Generate reason
                direction = "higher" if item["value"] > mean_val else "lower"
                diff_percent = abs(item["value"] - mean_val) / mean_val * 100 if mean_val != 0 else 0
                item["reason"] = f"Value {item['value']:.2f} is significantly {direction} than average ({mean_val:.2f}) by {diff_percent:.1f}%."
                anomalies.append(item)
            else:
                normal.append(item)

        return anomalies, normal

    def format_table(self, data: Optional[List[Dict[str, Any]]] = None, file_token: str = "default_token") -> str:
        """
        Formats the table data into a Lark Card V2 JSON string.
        """
        if data is None:
            data = []

        cleaned_data = self._clean_data(data)
        anomalies, normal = self._detect_anomalies(cleaned_data)

        total_count = len(cleaned_data)
        anomaly_count = len(anomalies)
        normal_count = len(normal)

        if total_count == 0:
            summary = "Total items: 0\nAnomalies: 0\nStatus: No data available."
        else:
            summary = f"Total items: {total_count}\nAnomalies: {anomaly_count} (Top 3% flagged)\nStatus: {normal_count} items are within normal range."

        # Build anomalies elements
        anomaly_elements = []
        if anomalies:
            for item in anomalies:
                # Determine color based on value vs threshold
                # Red: top 3% anomaly
                color = "red"
                text = f"<font color='{color}'>**{item['name']}**</font>: {item['value']} - {item.get('reason', '')}"
                anomaly_elements.append({
                    "tag": "markdown",
                    "content": text
                })
        else:
             anomaly_elements.append({
                    "tag": "markdown",
                    "content": "No significant anomalies detected."
             })

        card = {
            "type": "template",
            "data": {
                "template_variable": {
                    "summary": summary
                }
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": summary
                },
                {
                    "tag": "collapsible_panel",
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"View Anomalies ({anomaly_count})"
                        }
                    },
                    "elements": anomaly_elements
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "Download Full Table"
                            },
                            "type": "primary",
                            "value": {
                                "file_token": file_token
                            }
                        }
                    ]
                }
            ]
        }

        return json.dumps(card, ensure_ascii=False)
