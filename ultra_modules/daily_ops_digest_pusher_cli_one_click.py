import json
from datetime import datetime
from typing import Dict, Any, Optional

def clean_data(data: Any, default: Any) -> Any:
    """Helper to clean dirty data or use a fallback default."""
    if data is None:
        return default
    if isinstance(data, str) and not data.strip():
        return default
    if isinstance(data, (int, float)) and data < 0:
        return default
    return data

class DailyOpsDigestPusher:
    def __init__(self, mode: str = "json"):
        # Default mode is json if not excel
        self.mode = "excel" if mode and isinstance(mode, str) and mode.strip().lower() == "excel" else "json"

    def fetch_jules_fleet_progress(self, raw_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetches fleet progress. Cleans input data or uses defaults."""
        raw_data = raw_data or {}

        # Self-healing missing/dirty values
        completed = clean_data(raw_data.get("completed_tasks"), 0)
        ongoing = clean_data(raw_data.get("ongoing_tasks"), 0)
        efficiency = clean_data(raw_data.get("efficiency_rate"), 0.85)

        return {
            "completed_tasks": completed,
            "ongoing_tasks": ongoing,
            "efficiency_rate": float(efficiency)
        }

    def fetch_recruitment_status(self, raw_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetches recruitment status. Cleans input data or uses defaults."""
        raw_data = raw_data or {}

        interviews = clean_data(raw_data.get("interviews_conducted"), 0)
        offers = clean_data(raw_data.get("offers_extended"), 0)

        return {
            "interviews_conducted": interviews,
            "offers_extended": offers
        }

    def fetch_system_health(self, raw_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetches system health. Cleans input data or uses defaults."""
        raw_data = raw_data or {}

        uptime = clean_data(raw_data.get("uptime_percentage"), 99.9)
        active_incidents = clean_data(raw_data.get("active_incidents"), 0)

        # Bound uptime between 0 and 100
        uptime = max(0.0, min(100.0, float(uptime)))

        return {
            "uptime_percentage": uptime,
            "active_incidents": active_incidents
        }

    def generate_digest(self,
                       fleet_data: Optional[Dict[str, Any]] = None,
                       recruitment_data: Optional[Dict[str, Any]] = None,
                       health_data: Optional[Dict[str, Any]] = None) -> str:
        """Generates the one-page digest report."""
        try:
            fleet = self.fetch_jules_fleet_progress(fleet_data)
            recruitment = self.fetch_recruitment_status(recruitment_data)
            health = self.fetch_system_health(health_data)

            digest_payload = {
                "timestamp": datetime.now().isoformat(),
                "fleet_progress": fleet,
                "recruitment_status": recruitment,
                "system_health": health
            }

            if self.mode == "excel":
                # Simulate excel CSV/tabular format generation
                lines = ["Section,Metric,Value"]
                for k, v in fleet.items():
                    lines.append(f"FleetProgress,{k},{v}")
                for k, v in recruitment.items():
                    lines.append(f"Recruitment,{k},{v}")
                for k, v in health.items():
                    lines.append(f"SystemHealth,{k},{v}")
                return "\n".join(lines)
            else:
                return json.dumps(digest_payload, indent=2)
        except Exception as e:
            # Fallback error payload
            return json.dumps({"error": "Failed to generate digest", "details": str(e)})

def cli_entry(mode: str = "json",
              fleet_data: Optional[Dict[str, Any]] = None,
              recruitment_data: Optional[Dict[str, Any]] = None,
              health_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Zero-parameter one-click entry point.
    All missing parameters are automatically filled with sensible defaults.
    """
    pusher = DailyOpsDigestPusher(mode=mode)
    return pusher.generate_digest(fleet_data, recruitment_data, health_data)

if __name__ == "__main__":
    # One-click execution without any parameters
    print("--- JSON Output ---")
    print(cli_entry())
    print("\n--- Excel (Tabular) Output ---")
    print(cli_entry(mode="excel"))
