from ultra_modules.daily_ops_digest_pusher_core_engine import generate_daily_digest

def push_daily_digest(data: dict = None) -> dict:
    """
    Feishu / Lark integration bridge for pushing a daily digest.
    Provides extreme simplicity (one-click, zero config), zero confirmation,
    missing parameter fallback, and dirty data self-healing.

    Implements silent schema mapping from v1 to v2:
    v1 format:
    {"old_progress": "...", "old_recruitment_hired": 3, "old_recruitment_target": 10, "old_health": 90}
    v2 format:
    {"progress": {"status": "..."}, "recruitment": {"hired": 3, "target": 10}, "health": {"score": 90}}
    """
    if not isinstance(data, dict):
        data = {}

    # Copy data to avoid mutating the original
    processed_data = dict(data)

    # V1 to V2 Schema Mapping (silent conversion)

    # Progress mapping
    if "old_progress" in processed_data and "progress" not in processed_data:
        processed_data["progress"] = {"status": processed_data["old_progress"]}

    # Recruitment mapping
    if "old_recruitment_hired" in processed_data or "old_recruitment_target" in processed_data:
        if "recruitment" not in processed_data:
            processed_data["recruitment"] = {}
        if "old_recruitment_hired" in processed_data and "hired" not in processed_data["recruitment"]:
            processed_data["recruitment"]["hired"] = processed_data["old_recruitment_hired"]
        if "old_recruitment_target" in processed_data and "target" not in processed_data["recruitment"]:
            processed_data["recruitment"]["target"] = processed_data["old_recruitment_target"]

    # Health mapping
    if "old_health" in processed_data and "health" not in processed_data:
        processed_data["health"] = {"score": processed_data["old_health"]}

    # Delegate core logic to engine which handles missing parameter fallback and dirty data
    return generate_daily_digest(processed_data)
