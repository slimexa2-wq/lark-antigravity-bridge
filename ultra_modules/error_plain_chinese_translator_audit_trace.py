import traceback
import uuid
import datetime
import json
from typing import Dict, Any, List, Optional

class ErrorTranslator:
    def __init__(self, default_fallback_message: str = "系统遇到未知错误，请稍后再试或联系技术支持。"):
        self.default_fallback_message = default_fallback_message
        self.audit_logs: List[Dict[str, Any]] = []

    def _generate_trace_id(self) -> str:
        return str(uuid.uuid4())

    def _clean_input(self, data: Any) -> str:
        if data is None:
            return ""
        if isinstance(data, str):
            return data
        if isinstance(data, BaseException):
            try:
                return "".join(traceback.format_exception(type(data), data, data.__traceback__))
            except Exception:
                return "Failed to format exception"
        try:
            return str(data)
        except Exception:
            return "Unparseable Data"

    def _translate_to_plain_chinese(self, error_text: str) -> str:
        if not error_text:
            return self.default_fallback_message

        error_text_lower = error_text.lower()
        if "connection refused" in error_text_lower or "timeout" in error_text_lower or "network" in error_text_lower:
            return "网络连接失败，请检查您的网络设置后重试。"
        elif "nullpointer" in error_text_lower or "none type" in error_text_lower or "nonetype" in error_text_lower:
            return "程序处理到空数据，导致无法继续运行。"
        elif "permission denied" in error_text_lower or "unauthorized" in error_text_lower or "forbidden" in error_text_lower:
            return "您当前没有权限执行此操作，请联系管理员分配权限。"
        elif "out of memory" in error_text_lower or "memoryerror" in error_text_lower or "oom" in error_text_lower:
            return "系统内存不足，请尝试关闭一些程序后重试。"
        elif "index out of range" in error_text_lower or "indexerror" in error_text_lower:
            return "尝试访问的数据超出了正常范围。"
        elif "syntax error" in error_text_lower or "syntaxerror" in error_text_lower:
            return "代码或输入存在语法错误，无法解析。"
        elif "not found" in error_text_lower or "404" in error_text_lower:
            return "您要寻找的资源或数据未找到，请确认后重试。"
        elif "duplicate entry" in error_text_lower or "unique constraint" in error_text_lower:
            return "提交的数据已经存在，请不要重复提交。"

        return self.default_fallback_message

    def _generate_healing_suggestions(self, error_text: str) -> List[str]:
        if not error_text:
            return ["一键重试", "联系客服"]

        error_text_lower = error_text.lower()
        if "connection refused" in error_text_lower or "timeout" in error_text_lower or "network" in error_text_lower:
            return ["检查网络连接并重试", "切换到其他网络环境", "联系网络管理员"]
        elif "permission denied" in error_text_lower or "unauthorized" in error_text_lower or "forbidden" in error_text_lower:
            return ["重新登录账户", "一键申请访问权限"]
        elif "out of memory" in error_text_lower or "memoryerror" in error_text_lower or "oom" in error_text_lower:
            return ["一键清理后台缓存", "重启应用程序"]
        elif "not found" in error_text_lower or "404" in error_text_lower:
            return ["返回首页", "检查输入网址是否正确"]
        elif "duplicate entry" in error_text_lower or "unique constraint" in error_text_lower:
            return ["修改数据后重新提交", "查看已有数据"]

        return ["一键刷新页面", "稍后重试", "提交工单给技术支持"]

    def _generate_diff_highlight(self, original: str, translated: str) -> str:
        # A simple diff highlighter representation for the audit log
        # In a real heavy system this might be a complex HTML or delta,
        # but here we generate a clean string representation.
        if not original:
            return f"+ {translated}"

        # Take a bit more context for the diff snippet so that key words
        # (like the exception type) don't get truncated.
        snippet = original[:200].replace('\n', ' ').replace('\\n', ' ')
        if len(original) > 200:
            snippet += "..."

        return f"- [Raw Error] {snippet}\n+ [Plain Chinese] {translated}"

    def process_error(self, raw_error: Any = None, context: Any = None) -> Dict[str, Any]:
        """
        Processes an error, translates it, generates self-healing suggestions,
        records a detailed audit trace in the background, and returns a clean result for the frontend.
        """
        trace_id = self._generate_trace_id()
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        cleaned_error = self._clean_input(raw_error)
        cleaned_context = self._clean_input(context)

        # Self-healing for extremely massive strings (dirty data)
        if len(cleaned_error) > 10000:
            cleaned_error = cleaned_error[:10000] + "...(truncated due to length)"

        if len(cleaned_context) > 5000:
            cleaned_context = cleaned_context[:5000] + "...(truncated)"

        translation = self._translate_to_plain_chinese(cleaned_error)
        suggestions = self._generate_healing_suggestions(cleaned_error)
        diff_highlight = self._generate_diff_highlight(cleaned_error, translation)

        # Record trace in background for audit
        audit_entry = {
            "trace_id": trace_id,
            "timestamp": timestamp,
            "original_error_length": len(cleaned_error),
            "original_error_snippet": cleaned_error[:200],
            "context_info": cleaned_context if cleaned_context else "No Context Provided",
            "translation_applied": translation,
            "suggestions_generated": suggestions,
            "diff_highlight": diff_highlight,
            "status": "PROCESSED_SUCCESSFULLY"
        }
        self.audit_logs.append(audit_entry)

        # Frontend only gets clean result
        result = {
            "trace_id": trace_id,
            "plain_chinese_message": translation,
            "healing_suggestions": suggestions,
            "diff_highlight": diff_highlight
        }

        return result

    def get_audit_logs(self) -> List[Dict[str, Any]]:
        return self.audit_logs

    def clear_audit_logs(self) -> None:
        self.audit_logs.clear()
