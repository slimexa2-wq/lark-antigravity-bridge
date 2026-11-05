import time

class ErrorPlainChineseTranslatorIntegrationBridge:
    def __init__(self):
        # Zero configuration, strict zero-crash architecture
        pass

    def translate_error_to_card(self, error_payload=None):
        """
        Translates backend error payloads into a user-friendly plain Chinese card.
        Tolerates missing parameters, dirty data, and multiple schema versions automatically.
        """
        if error_payload is None or not isinstance(error_payload, dict):
            error_payload = {}

        extracted_code = self._extract_field(error_payload, ['error_code', 'code', 'status', 'errCode'])
        extracted_msg = self._extract_field(error_payload, ['error_message', 'message', 'err_msg', 'msg', 'details'])
        extracted_trace = self._extract_field(error_payload, ['stack_trace', 'trace', 'stack', 'exception'])
        timestamp = self._extract_field(error_payload, ['timestamp', 'time', 'date', 'created_at'])

        error_code = str(extracted_code) if extracted_code is not None else 'UNKNOWN_ERROR'
        error_msg = str(extracted_msg) if extracted_msg is not None else '系统繁忙，请稍后再试'
        stack_trace = str(extracted_trace) if extracted_trace is not None else ''

        parsed_timestamp = self._parse_and_clean_timestamp(timestamp)

        error_msg_lower = error_msg.lower()
        error_code_lower = error_code.lower()
        stack_trace_lower = stack_trace.lower()

        plain_chinese = "遇到了一点小状况，我们正在努力解决"
        suggestion = "建议您稍后刷新重试，或联系管理员获取帮助。"
        action_button = "一键重试"
        auto_snapshot = False

        if "timeout" in error_msg_lower or "timeout" in error_code_lower or "超时" in error_msg_lower:
            plain_chinese = "网络请求超时或后端服务响应太慢"
            suggestion = "系统尝试与服务器通信时等待时间过长。建议检查网络连接。"
            action_button = "一键诊断网络并重试"
        elif "permission" in error_msg_lower or "auth" in error_msg_lower or "403" in error_code_lower or "forbidden" in error_code_lower:
            plain_chinese = "您目前没有执行此操作的权限"
            suggestion = "系统拦截了您的请求，因为缺少必要的权限。建议重新登录或申请权限。"
            action_button = "一键申请权限 / 重新登录"
        elif "not found" in error_msg_lower or "404" in error_code_lower:
            plain_chinese = "找不到您请求的资源或数据"
            suggestion = "请求的文件、数据或页面不存在，可能已被删除或移动。"
            action_button = "一键返回首页"
        elif "database" in error_msg_lower or "sql" in error_msg_lower or "db" in error_code_lower:
            plain_chinese = "底层数据库出现异常"
            suggestion = "系统在读取或保存您的数据时遇到了问题，已为您自动保存快照。"
            action_button = "一键恢复最后状态并重试"
            auto_snapshot = True
        elif "memory" in error_msg_lower or "oom" in error_code_lower or "out of memory" in stack_trace_lower:
            plain_chinese = "服务器内存不足导致处理失败"
            suggestion = "您请求处理的数据量可能过大。建议减少单次处理的数据量。"
            action_button = "一键清理缓存并重试"
        elif "typeerror" in error_msg_lower or "valueerror" in error_msg_lower:
            plain_chinese = "系统内部数据处理格式错误"
            suggestion = "系统接收到了不符合预期格式的数据。"
            action_button = "一键上报此错误"
            auto_snapshot = True
        elif "connection refused" in stack_trace_lower:
            plain_chinese = "无法连接到后台服务"
            suggestion = "后台服务可能正在重启或维护中。"
            action_button = "一键重连"

        return {
            "title": "出错了",
            "plain_chinese_reason": plain_chinese,
            "suggestion": suggestion,
            "action_button_text": action_button,
            "original_error_code": error_code,
            "is_auto_healed_suggestion": True,
            "auto_snapshot_enabled": auto_snapshot,
            "timestamp": parsed_timestamp
        }

    def _extract_field(self, payload: dict, candidate_keys: list):
        """
        Extracts a field from a payload using a list of candidate keys (schema automatic forward compatibility).
        Also recursively searches within common wrapper objects.
        """
        for key in candidate_keys:
            if key in payload and payload[key] is not None:
                return payload[key]

        # Check in common wrappers
        for wrapper in ['data', 'error', 'body', 'response']:
            if wrapper in payload and isinstance(payload[wrapper], dict):
                for key in candidate_keys:
                    if key in payload[wrapper] and payload[wrapper][key] is not None:
                        return payload[wrapper][key]
        return None

    def _parse_and_clean_timestamp(self, ts):
        """
        Cleans and normalizes timestamps. Tolerates dirty data, cross-year/month extremes, invalid types.
        """
        current_time = int(time.time())
        if ts is None:
            return current_time

        try:
            if isinstance(ts, str):
                ts_val = int(ts)
            elif isinstance(ts, (int, float)):
                ts_val = int(ts)
            else:
                return current_time

            # If timestamp is in milliseconds, convert to seconds
            if ts_val > 10000000000:
                ts_val = ts_val // 1000
            # If still huge, probably microseconds
            if ts_val > 10000000000:
                ts_val = ts_val // 1000

            # If extreme boundary (before 1970 or after 2100)
            if ts_val < 0 or ts_val > 4102444800:
                return current_time

            return ts_val

        except (ValueError, TypeError, OverflowError):
            return current_time
