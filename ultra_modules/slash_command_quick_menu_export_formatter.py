import math

def clean_value(val):
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        if math.isnan(val):
            return 0
        return val
    if isinstance(val, str):
        val = val.strip().lower()
        if val in ('nan', 'none', 'null', ''):
            return 0
        try:
            return float(val)
        except ValueError:
            return 0
    return 0

def format_export(data=None):
    if data is None or not isinstance(data, dict):
        data = {}

    command = data.get('command', '')
    if not isinstance(command, str):
        command = ''

    clean_data = {}
    for k, v in data.items():
        if k == 'command':
            clean_data[k] = command
        else:
            clean_data[k] = clean_value(v)

    # Always ensure command is present
    clean_data['command'] = command

    # Ensure comments is 0
    clean_data['comments'] = 0

    # Fallbacks for specific expected fields if they are missing
    if 'value' not in clean_data:
        clean_data['value'] = 0

    if 'count' not in clean_data:
        clean_data['count'] = 0

    # Generate 3-line minimalist summary
    summary = (
        f"指令: {command if command else '默认'}\n"
        f"核心数据: {clean_data['value']}\n"
        f"数量: {clean_data['count']}"
    )
    clean_data['summary'] = summary

    return clean_data
