import math
import logging
from typing import List, Dict, Any, Union

logger = logging.getLogger(__name__)

class CollapsibleThinkingCardAnomalyRadar:
    def __init__(self, data: List[Union[int, float, str, None]] = None, config: Dict[str, Any] = None):
        """
        Initialize the radar with raw data and configuration.
        Implements self-healing for missing/dirty parameters.
        """
        # Self-healing: Default fallbacks for missing parameters
        self.raw_data = data if data is not None else []
        self.config = config if config is not None else {}
        self.threshold_z = self.config.get('threshold_z', 2.0)
        self.top_percentile = self.config.get('top_percentile', 0.03)

        self.clean_data = self._clean_and_heal_data(self.raw_data)

    def _clean_and_heal_data(self, raw_data: List[Any]) -> List[float]:
        """
        Dirty data self-healing: converts valid strings to float, ignores None/unparseable.
        """
        clean = []
        for item in raw_data:
            if item is None:
                continue
            try:
                val = float(item)
                # Handle extreme boundary conditions (e.g. inf, nan)
                if math.isinf(val) or math.isnan(val):
                    continue
                clean.append(val)
            except (ValueError, TypeError):
                # Ignore dirty data that cannot be healed
                pass

        # If no valid data, provide a fallback to prevent crash
        if not clean:
            return [0.0]
        return clean

    def _calculate_z_scores(self) -> List[Dict[str, Any]]:
        """
        Calculate Z-Score for the clean data.
        """
        n = len(self.clean_data)
        if n == 0:
            return []

        mean = sum(self.clean_data) / n
        if n > 1:
            variance = sum((x - mean) ** 2 for x in self.clean_data) / n
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0

        results = []
        for val in self.clean_data:
            z_score = 0.0 if std_dev == 0.0 else (val - mean) / std_dev
            results.append({
                "value": val,
                "z_score": z_score,
                "abs_z_score": abs(z_score)
            })

        return results

    def analyze(self) -> Dict[str, Any]:
        """
        Analyzes the data and identifies top anomalies.
        Returns the processed anomaly report.
        """
        analyzed_data = self._calculate_z_scores()
        if not analyzed_data:
            return {"top_anomalies": [], "normal_items": []}

        # Sort by absolute Z-score descending to rank anomalies
        analyzed_data.sort(key=lambda x: x["abs_z_score"], reverse=True)

        total_items = len(analyzed_data)
        top_k = max(1, math.ceil(total_items * self.top_percentile))

        top_anomalies = []
        normal_items = []

        for i, item in enumerate(analyzed_data):
            # Top 3% and exceeds threshold Z
            if i < top_k and item["abs_z_score"] >= self.threshold_z:
                item["tag"] = "red"
                item["reason"] = f"Value {item['value']} significantly deviates from mean with Z-Score {item['z_score']:.2f}"
                top_anomalies.append(item)
            else:
                # 97% silent release
                # Assign yellow if somewhat high, green if low
                if item["abs_z_score"] >= (self.threshold_z / 2):
                    item["tag"] = "yellow"
                else:
                    item["tag"] = "green"
                normal_items.append(item)

        return {
            "top_anomalies": top_anomalies,
            "normal_items": normal_items,
            "total_items": total_items
        }

    def generate_feishu_card(self) -> Dict[str, Any]:
        """
        Generate Feishu (Lark) V2 Card payload.
        - Conclusions at the top.
        - Native collapsible_panel for detailed thinking process.
        - Undo action button.
        """
        analysis_result = self.analyze()
        top_anomalies = analysis_result["top_anomalies"]
        normal_items = analysis_result["normal_items"]
        total_items = analysis_result["total_items"]

        # 1. Conclusion at the top (Max 3 lines for core summary)
        if top_anomalies:
            conclusion_text = f"🚨 Detected {len(top_anomalies)} anomalies requiring attention.\n"
            conclusion_text += f"Top Issue: {top_anomalies[0]['reason']}\n"
            conclusion_text += f"✅ {len(normal_items)} items within normal range (Silent pass)."
            template_color = "red"
        else:
            conclusion_text = f"✅ All {total_items} items normal.\nSystem running smoothly.\nNo anomalies detected."
            template_color = "green"

        # 2. Detailed thinking process for collapsible_panel
        details_text = f"Analyzed {total_items} data points.\n"
        if top_anomalies:
            details_text += "Anomalies:\n"
            for a in top_anomalies:
                details_text += f"- [Red] {a['value']} (Z: {a['z_score']:.2f})\n"
        if normal_items:
            details_text += "Normal Items (Sample):\n"
            for n in normal_items[:3]:
                details_text += f"- [{n['tag'].capitalize()}] {n['value']} (Z: {n['z_score']:.2f})\n"
            if len(normal_items) > 3:
                details_text += f"... and {len(normal_items) - 3} more."

        card = {
            "config": {
                "update_multi": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "Anomaly Radar Report"
                },
                "template": template_color
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": conclusion_text
                },
                {
                    "tag": "collapsible_panel",
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "Detailed Thinking Process"
                        }
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": details_text
                        }
                    ]
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "Undo Action"
                            },
                            "type": "default",
                            "value": {
                                "action": "undo",
                                "module": "anomaly_radar"
                            }
                        }
                    ]
                }
            ]
        }

        return card

def build_radar_and_get_card(data: List[Any] = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Convenience method for extreme simple invocation (One-click, zero config).
    """
    radar = CollapsibleThinkingCardAnomalyRadar(data, config)
    return radar.generate_feishu_card()
