import re
from typing import Dict, Any, List

def clean_input(text: Any) -> str:
    """Safely cast input to string and clean dirty data."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    # Basic dirty data cleaning: trim whitespace and control characters
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    return cleaned.strip()

def route_slash_command(command: str, args: List[Any] = None, kwargs: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Route slash commands with extreme fallback and fault tolerance.
    Supported commands: /周报 (weekly report), /提成 (commission), /漫剧 (comic drama),
    /标书 (bidding document), /状态 (status).
    """
    command = clean_input(command)
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    safe_args = [clean_input(arg) for arg in args]
    safe_kwargs = {clean_input(k): clean_input(v) for k, v in kwargs.items()}

    # Extract command part if there's leading text
    cmd_match = re.search(r'/(周报|提成|漫剧|标书|状态)', command)
    if not cmd_match:
        return {
            "status": "error",
            "message": "Unrecognized or empty command.",
            "data": None
        }

    cmd_type = cmd_match.group(1)

    if cmd_type == "周报":
        # Default: current week
        period = safe_kwargs.get("period", "this_week")
        user = safe_kwargs.get("user", "self")
        return {
            "status": "success",
            "action": "generate_weekly_report",
            "data": {"period": period, "user": user}
        }

    elif cmd_type == "提成":
        # Default: current month
        month = safe_kwargs.get("month", "current")
        return {
            "status": "success",
            "action": "query_commission",
            "data": {"month": month}
        }

    elif cmd_type == "漫剧":
        # Default: default workspace
        workspace = safe_kwargs.get("workspace", "default")
        return {
            "status": "success",
            "action": "open_comic_drama_workspace",
            "data": {"workspace": workspace}
        }

    elif cmd_type == "标书":
        # Default: latest
        doc_type = safe_kwargs.get("type", "latest")
        return {
            "status": "success",
            "action": "retrieve_bidding_document",
            "data": {"type": doc_type}
        }

    elif cmd_type == "状态":
        # Default: all systems
        target = safe_kwargs.get("target", "all")
        return {
            "status": "success",
            "action": "check_status",
            "data": {"target": target}
        }

    return {
        "status": "error",
        "message": "Fallback route failed.",
        "data": None
    }
