def explain_digest_in_plain_language(data: dict) -> dict:
    """
    Translates complex daily ops data into a plain-language (大白话) Feishu card.
    Handles dirty data self-healing, missing parameters fallback, and bounds checking.
    """
    if not isinstance(data, dict):
        data = {}

    def extract_dict(key):
        val = data.get(key)
        return val if isinstance(val, dict) else {}

    progress_data = extract_dict("progress")
    recruitment_data = extract_dict("recruitment")
    health_data = extract_dict("health")

    # 1. Progress Status (String handling)
    progress_status = str(progress_data.get("status", "未知"))
    if not progress_status.strip() or progress_status.strip().lower() == "none":
        progress_status = "未知"
    else:
        progress_status = progress_status.strip()

    progress_details = str(progress_data.get("details", "无详细进度信息。"))
    if len(progress_details) > 1000:
        progress_details = progress_details[:997] + "..."

    # 2. Recruitment (Int handling)
    def parse_int(val, default=0):
        try:
            parsed = int(float(val)) # handles "5.5" -> 5
            return parsed if parsed >= 0 else default
        except (ValueError, TypeError):
            return default

    hired = parse_int(recruitment_data.get("hired"), 0)
    target = parse_int(recruitment_data.get("target"), 0)
    if target < hired:
        target = hired

    recruitment_details = str(recruitment_data.get("details", "无详细招聘信息。"))
    if len(recruitment_details) > 1000:
        recruitment_details = recruitment_details[:997] + "..."

    # 3. System Health (Float handling)
    def parse_float(val, default=100.0):
        try:
            parsed = float(val)
            if parsed < 0.0 or parsed > 100.0:
                return default
            return parsed
        except (ValueError, TypeError):
            return default

    health_score = parse_float(health_data.get("score"), 100.0)
    health_details = str(health_data.get("details", "系统运行平稳。"))
    if len(health_details) > 1000:
        health_details = health_details[:997] + "..."

    # Create the 3-line simple plain language summary
    line1 = f"🚩 【进度】Jules舰队当前状态：{progress_status}。"
    line2 = f"🤝 【招聘】当前已入职 {hired} 人（目标 {target} 人）。"
    line3 = f"🩺 【健康】系统健康度评分：{health_score:.1f}%。"
    core_summary = f"{line1}\n{line2}\n{line3}"

    # Feishu Card Output
    card = {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "Jules舰队每日简报"
            },
            "template": "blue"
        },
        "elements": [
            {
                "tag": "markdown",
                "content": core_summary
            },
            {
                "tag": "collapsible_panel",
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "展开查看详细数据"
                    }
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": f"**进度详情**\n{progress_details}\n\n**招聘详情**\n{recruitment_details}\n\n**健康详情**\n{health_details}"
                    }
                ]
            }
        ]
    }

    return card
