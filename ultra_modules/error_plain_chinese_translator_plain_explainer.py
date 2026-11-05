import json
import re

def generate_error_card(error_trace: str = "", format_type: str = "markdown") -> str:
    """
    Translates complex backend error stack traces into simple, plain Chinese explanations
    with a one-click self-healing suggestion card.

    Args:
        error_trace: The raw error message or stack trace. Coerced to string.
        format_type: The output format: 'markdown', 'html', or 'json'.
                     Defaults to 'markdown'. Invalid types fallback to 'markdown'.

    Returns:
        A formatted string (or JSON string) representing the error card.
    """
    # Silent cleaning of dirty data: Coerce error_trace to string
    if error_trace is None:
        error_trace = ""
    elif not isinstance(error_trace, str):
        try:
            error_trace = str(error_trace)
        except Exception:
            error_trace = "未知错误数据"

    # Default fallback for missing/invalid parameter
    if format_type not in ["markdown", "html", "json"]:
        format_type = "markdown"

    # Extreme boundary conditions: very long strings
    # Truncate if insanely long (e.g., > 100,000 characters)
    if len(error_trace) > 100000:
        error_trace = error_trace[:100000]

    # Simple logic to determine the cause based on common error patterns
    error_lower = error_trace.lower()

    if "connection refused" in error_lower or "timeout" in error_lower:
        title = "🔌 网络连接不通"
        explanation = "系统尝试连接外部服务失败，可能是网络波动或者对方服务器正在维护。"
        suggestion = "请检查您的网络连接是否正常，稍等片刻后点击下方按钮重试。如果持续报错，请联系IT支持检查防火墙设置。"
    elif "nullpointerexception" in error_lower or "nonetype" in error_lower:
        title = "📉 数据缺失"
        explanation = "系统在处理任务时，发现有一个必要的数据是空的，导致流程走不下去了。"
        suggestion = "请检查您刚刚输入或上传的数据是否完整。如果有必填项遗漏，补充后重试即可。"
    elif "permission denied" in error_lower or "unauthorized" in error_lower or "403" in error_lower:
        title = "🔒 权限不足"
        explanation = "您当前的账号没有执行这个操作的权限。"
        suggestion = "请确认您是否登录了正确的账号。如果确实需要此功能，请点击申请权限或联系管理员开通。"
    elif "out of memory" in error_lower or "memoryerror" in error_lower:
        title = "💾 内存不足"
        explanation = "这次处理的数据量太大了，超出了系统当前能承受的极限。"
        suggestion = "建议您把大文件拆分成几个小文件，分批次上传或处理。或者联系技术人员扩大系统资源池。"
    else:
        title = "⚠️ 系统开小差了"
        explanation = "系统遇到了一点小状况，暂时无法完成您的请求。技术人员已经收到了通知。"
        suggestion = "您可以尝试刷新页面或点击重试。如果业务紧急，请直接截图本卡片发给技术支持人员。"

    # Ensure output is perfectly simple for frontends
    if format_type == "json":
        return json.dumps({
            "title": title,
            "explanation": explanation,
            "suggestion": suggestion,
            "action": "一键重试 / 自愈"
        }, ensure_ascii=False)

    elif format_type == "html":
        return f"""<div class="error-card" style="border: 1px solid #ffcccc; padding: 20px; border-radius: 8px; background-color: #fff9f9; font-family: sans-serif;">
    <h3 style="color: #d32f2f; margin-top: 0;">{title}</h3>
    <p style="color: #333; font-size: 16px;"><strong>原因：</strong>{explanation}</p>
    <p style="color: #555; font-size: 14px;"><strong>建议：</strong>{suggestion}</p>
    <button style="background-color: #d32f2f; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 14px;">一键重试 / 自愈</button>
</div>"""

    else:  # markdown
        return f"""### {title}

**原因：** {explanation}

**建议：** {suggestion}

[ 一键重试 / 自愈 ]"""
