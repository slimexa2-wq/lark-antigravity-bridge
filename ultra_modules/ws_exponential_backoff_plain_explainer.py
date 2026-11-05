import math
import json

def explain_reconnect_status(attempt=None, delay_ms=None, format_type='markdown'):
    """
    Generate a plain-language explanation card of the WebSocket reconnection state.

    Args:
        attempt (int, optional): The current retry attempt number. Defaults to 0.
        delay_ms (float, optional): The current delay in milliseconds. Defaults to 0.
        format_type (str, optional): The output format ('markdown', 'html', or 'json'). Defaults to 'markdown'.

    Returns:
        str: The formatted plain-language explanation.
    """

    # --- Extreme Robustness: Dirty Data Self-Healing ---

    # Clean attempt
    try:
        if attempt is None or math.isnan(float(attempt)):
            clean_attempt = 0
        else:
            clean_attempt = int(float(attempt))
    except (TypeError, ValueError):
        clean_attempt = 0
    clean_attempt = max(0, clean_attempt)

    # Clean delay_ms
    try:
        if delay_ms is None or math.isnan(float(delay_ms)):
            clean_delay = 0.0
        else:
            clean_delay = float(delay_ms)
    except (TypeError, ValueError):
        clean_delay = 0.0
    clean_delay = max(0.0, clean_delay)

    # Clean format_type
    if not isinstance(format_type, str):
        format_type = 'markdown'

    format_type = format_type.strip().lower()
    valid_formats = ['markdown', 'html', 'json']
    if format_type not in valid_formats:
        format_type = 'markdown'

    # --- Plain-language translation ---
    delay_sec = clean_delay / 1000.0

    status_summary = "断线重连中" if clean_attempt > 0 else "初次连接准备"

    # User-friendly explanation
    if clean_attempt == 0:
        detail_msg = "系统即将发起初次连接，目前没有退避延迟。"
    else:
        detail_msg = f"这是第 {clean_attempt} 次尝试重连。为了防止网络拥堵（雪崩效应），系统使用了指数退避与随机抖动算法，本次将等待约 {delay_sec:.2f} 秒后再次尝试。"

    # --- Formatting Output ---
    if format_type == 'json':
        return json.dumps({
            "status": status_summary,
            "attempt": clean_attempt,
            "delay_ms": clean_delay,
            "delay_sec_approx": round(delay_sec, 2),
            "message": detail_msg
        }, ensure_ascii=False)

    elif format_type == 'html':
        return f"""<div class="reconnect-card" style="border:1px solid #ccc; padding:15px; border-radius:8px; font-family:sans-serif;">
    <h3 style="margin-top:0; color:#d9534f;">🔌 状态: {status_summary}</h3>
    <p><strong>当前重试次数:</strong> {clean_attempt}</p>
    <p><strong>预计等待时间:</strong> {delay_sec:.2f} 秒</p>
    <p style="color:#555; font-size:0.9em;"><em>💡 <strong>说明:</strong> {detail_msg}</em></p>
</div>"""

    else:
        # Default to Markdown
        return f"""### 🔌 状态: {status_summary}
- **当前重试次数:** {clean_attempt}
- **预计等待时间:** {delay_sec:.2f} 秒

> 💡 **说明:** {detail_msg}"""
