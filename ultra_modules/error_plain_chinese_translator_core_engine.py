def translate_error_to_plain_chinese(error_trace=None):
    """
    将后台堆栈报错自动翻译为大白话原因说明与一键自愈建议。
    支持缺参默认值、脏数据静默清洗。
    """
    # 脏数据处理与静默清洗
    if error_trace is None:
        error_trace = ""

    if not isinstance(error_trace, str):
        try:
            error_trace = str(error_trace)
        except Exception:
            # 极端情况：对象无法转换为字符串，兜底为空字符串
            error_trace = ""

    error_trace = error_trace.strip()

    # 缺参或完全空字符串的兜底
    if not error_trace:
        return {
            "title": "未知错误",
            "reason": "系统遇到了未知的情况，未获取到具体的错误日志。",
            "suggestion": "请刷新页面重试，或联系技术支持团队排查。"
        }

    error_lower = error_trace.lower()

    # 核心映射算法
    if "nullpointerexception" in error_lower or "nonetype" in error_lower:
        return {
            "title": "数据缺失异常",
            "reason": "系统在处理数据时，发现某个关键信息是空的（不存在），但程序依然尝试去读取它。",
            "suggestion": "请检查相关操作是否遗漏了必填项，或尝试刷新页面重新加载数据。"
        }

    if "timeout" in error_lower or "connection refused" in error_lower or "econnrefused" in error_lower:
        return {
            "title": "网络请求失败",
            "reason": "当前网络环境不稳定，或者服务器正忙，导致请求超时或被拒绝。",
            "suggestion": "请检查您的网络连接是否正常，稍等片刻后重试。"
        }

    if "outofmemory" in error_lower or "oom" in error_lower or "memoryerror" in error_lower:
        return {
            "title": "内存不足",
            "reason": "系统当前处理的数据量过大，导致内存资源被耗尽。",
            "suggestion": "请尝试重启应用，或者减少单次处理的数据量后重试。"
        }

    if "permission denied" in error_lower or "unauthorized" in error_lower or "403" in error_lower or "401" in error_lower:
        return {
            "title": "无访问权限",
            "reason": "当前账号没有执行此操作或访问该数据的权限。",
            "suggestion": "请确认账号状态是否正常，或联系管理员申请开通相关权限。"
        }

    if "syntaxerror" in error_lower or "parseerror" in error_lower or "jsondecodeerror" in error_lower:
        return {
            "title": "数据格式解析失败",
            "reason": "系统接收到的数据或配置文件格式不符合规范，无法正确理解。",
            "suggestion": "请检查输入的数据内容是否完整正确。"
        }

    # 无法精准匹配的未识别错误（自动提取部分日志）
    snippet = error_trace[:50] + "..." if len(error_trace) > 50 else error_trace
    return {
        "title": "系统运行异常",
        "reason": f"系统在运行过程中遇到了未预期的状况。日志摘要：{snippet}",
        "suggestion": "建议您重新执行刚才的操作；如果持续报错，请截图当前页面反馈给技术支持。"
    }
