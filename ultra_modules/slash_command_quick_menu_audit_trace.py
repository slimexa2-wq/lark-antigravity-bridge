import re
from typing import Dict, Any, List

class SlashCommandQuickMenuAuditTraceRouter:
    """
    Router for slash commands (/周报, /提成, /漫剧, /标书, /状态) with a minimalist frontend output
    and a robust backend audit trace.
    """

    def __init__(self):
        self.audit_trace = []

    def _log_trace(self, action: str, details: str, diff: Dict[str, Any] = None):
        """Silently logs an audit trace entry."""
        entry = {"action": action, "details": details}
        if diff:
            entry["diff"] = diff
        self.audit_trace.append(entry)

    def _clean_input(self, text: Any) -> str:
        """Safely cast input to string and clean dirty data, logging if changes were made."""
        original = text
        if text is None:
            self._log_trace("type_conversion", "None converted to empty string.", {"original": None, "new": ""})
            return ""

        if not isinstance(text, str):
            text = str(text)
            self._log_trace("type_conversion", f"Non-string {type(original)} converted to string.", {"original": original, "new": text})

        # Remove control characters and trim
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text).strip()

        if cleaned != text:
             self._log_trace("dirty_data_repair", "Control characters or whitespace removed.", {"original": text, "new": cleaned})

        return cleaned

    def _deduplicate_kwargs(self, kwargs: List[tuple]) -> Dict[str, Any]:
        """Deduplicate keyword arguments (last one wins), logging deduplication."""
        result = {}
        for k, v in kwargs:
            clean_k = self._clean_input(k)
            clean_v = self._clean_input(v)
            if clean_k in result:
                self._log_trace("deduplication", f"Duplicate key '{clean_k}' found. Overwriting.", {"old_value": result[clean_k], "new_value": clean_v})
            result[clean_k] = clean_v
        return result

    def route(self, command: str, args: List[Any] = None, kwargs_list: List[tuple] = None) -> Dict[str, Any]:
        """
        Routes the command.
        Returns a minimalist dictionary for the frontend.
        """
        self.audit_trace = [] # Reset trace for new routing request

        self._log_trace("initialization", "Routing started", {"command": command})

        command = self._clean_input(command)

        if args is None:
            self._log_trace("defaulting", "args is None, defaulting to empty list.")
            args = []

        if kwargs_list is None:
             self._log_trace("defaulting", "kwargs_list is None, defaulting to empty list.")
             kwargs_list = []

        safe_kwargs = self._deduplicate_kwargs(kwargs_list)

        cmd_match = re.search(r'/(周报|提成|漫剧|标书|状态)', command)

        if not cmd_match:
            self._log_trace("routing_failure", "Unrecognized or empty command.")
            return {
                "status": "error",
                "message": "Unrecognized or empty command.",
                "data": None
            }

        cmd_type = cmd_match.group(1)
        self._log_trace("routing", f"Command identified as {cmd_type}.")

        result = {"status": "success"}

        if cmd_type == "周报":
            period = safe_kwargs.get("period")
            if not period:
                period = "this_week"
                self._log_trace("defaulting", "period missing, defaulting to 'this_week'")

            user = safe_kwargs.get("user")
            if not user:
                user = "self"
                self._log_trace("defaulting", "user missing, defaulting to 'self'")

            result.update({
                "action": "generate_weekly_report",
                "data": {"period": period, "user": user}
            })

        elif cmd_type == "提成":
            month = safe_kwargs.get("month")
            if not month:
                month = "current"
                self._log_trace("defaulting", "month missing, defaulting to 'current'")

            result.update({
                "action": "query_commission",
                "data": {"month": month}
            })

        elif cmd_type == "漫剧":
            workspace = safe_kwargs.get("workspace")
            if not workspace:
                workspace = "default"
                self._log_trace("defaulting", "workspace missing, defaulting to 'default'")

            result.update({
                "action": "open_comic_drama_workspace",
                "data": {"workspace": workspace}
            })

        elif cmd_type == "标书":
            doc_type = safe_kwargs.get("type")
            if not doc_type:
                doc_type = "latest"
                self._log_trace("defaulting", "type missing, defaulting to 'latest'")

            result.update({
                "action": "retrieve_bidding_document",
                "data": {"type": doc_type}
            })

        elif cmd_type == "状态":
            target = safe_kwargs.get("target")
            if not target:
                target = "all"
                self._log_trace("defaulting", "target missing, defaulting to 'all'")

            result.update({
                "action": "check_status",
                "data": {"target": target}
            })

        self._log_trace("routing_success", "Routing completed successfully.", {"result": result})

        return result
