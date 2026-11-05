import json

def format_mobile_table_digest(
    table_data=None,
    summary_columns=None,
    anomaly_rules=None,
    attachment_url=None,
    attachment_name=None,
    title=None
):
    """
    Core engine to format wide table data into a mobile-friendly 3-line digest
    with anomaly highlighting and an attachment download card for Lark.
    Zero configuration, robust self-healing, and automatic default values.
    """

    # 1. Handle Defaults and Silent Type Casting
    if title is None:
        title = "数据摘要"
    else:
        title = str(title)

    if attachment_name is None:
        attachment_name = "附件下载"
    else:
        attachment_name = str(attachment_name)

    if attachment_url is None:
        attachment_url = ""
    else:
        attachment_url = str(attachment_url)

    if anomaly_rules is None or not isinstance(anomaly_rules, dict):
        anomaly_rules = {}

    # 2. Clean dirty table_data
    if isinstance(table_data, str):
        try:
            parsed = json.loads(table_data)
            table_data = parsed if isinstance(parsed, list) else []
        except Exception:
            table_data = []
    elif not isinstance(table_data, list):
        table_data = []

    cleaned_table_data = [item for item in table_data if isinstance(item, dict)]

    # 3. Clean and auto-fill summary_columns (Zero Config)
    if isinstance(summary_columns, str):
        summary_columns = [summary_columns]
    elif not isinstance(summary_columns, list):
        summary_columns = []
    else:
        summary_columns = [str(c) for c in summary_columns]

    if not summary_columns and cleaned_table_data:
        # Auto-extract up to 3 keys from the first row
        first_row_keys = list(cleaned_table_data[0].keys())
        summary_columns = first_row_keys[:3]

    # 4. Extract max 3 rows for digest
    rows_to_show = cleaned_table_data[:3]

    # 5. Build elements
    elements = []
    if not rows_to_show:
        elements.append({
            "tag": "markdown",
            "content": "暂无摘要数据"
        })
    else:
        for row in rows_to_show:
            row_strs = []
            for col in summary_columns:
                val = row.get(col, "-")
                val_str = str(val)

                # Check anomaly
                is_anomaly = False
                if col in anomaly_rules:
                    rule = anomaly_rules[col]
                    if callable(rule):
                        try:
                            is_anomaly = bool(rule(val))
                        except Exception:
                            is_anomaly = False
                    elif isinstance(rule, list):
                        is_anomaly = val in rule
                    else:
                        is_anomaly = (val == rule)

                # Format
                if is_anomaly:
                    # using markdown red text for Lark
                    row_strs.append(f"{col}: <font color='red'>{val_str}</font>")
                else:
                    row_strs.append(f"{col}: {val_str}")

            content = " | ".join(row_strs) if row_strs else "暂无摘要数据"
            elements.append({
                "tag": "markdown",
                "content": content
            })

    # 6. Build Attachment Card
    if attachment_url.strip():
        elements.append({
            "tag": "hr"
        })
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": attachment_name
                    },
                    "type": "primary",
                    "url": attachment_url
                }
            ]
        })

    # Return Lark interactive card dict
    card = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "blue",
                "title": {
                    "tag": "plain_text",
                    "content": title
                }
            },
            "elements": elements
        }
    }

    return card
