import math

def sanitize_value(val):
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        if math.isnan(val):
            return 0
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val or val.lower() in ('nan', 'none'):
            return 0
        try:
            return float(val)
        except ValueError:
            return 0
    return 0

def process_slash_command(command, raw_data):
    if raw_data is None or not isinstance(raw_data, dict):
        raw_data = {}

    export_data = {}
    report_lines = []

    # Map commands to titles and field extractions
    # format: command: (title, [fields...])
    routers = {
        "/周报": ("【周报汇报】", ["完成任务数", "待办任务数", "风险项"]),
        "/提成": ("【提成汇报】", ["销售额", "提成比例", "预计发放"]),
        "/漫剧": ("【漫剧汇报】", ["新增集数", "总播放量", "完播率"]),
        "/标书": ("【标书汇报】", ["完成页数", "审核进度", "距离截标(天)"]),
        "/状态": ("【状态汇报】", ["今日工时", "有效产出", "疲劳度"])
    }

    if command not in routers:
        command = "/状态" # Default fallback

    title, fields = routers[command]

    report_lines.append(title)

    for field in fields:
        val = sanitize_value(raw_data.get(field, 0))
        export_data[field] = val
        report_lines.append(f"{field}: {val}")

    export_data["comments"] = 0
    report_lines.append(f"comments: {export_data['comments']}")

    report_text = "\n".join(report_lines[:3]) # Only return first 3 lines for text as requested

    return {
        "report_text": report_text,
        "export_data": export_data
    }
