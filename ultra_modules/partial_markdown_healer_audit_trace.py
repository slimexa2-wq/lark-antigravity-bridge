import logging
from typing import Dict, Any, Tuple, List, Optional

logger = logging.getLogger(__name__)

class AuditLog:
    def __init__(self):
        self.traces = []

    def record(self, step: str, details: Dict[str, Any]):
        self.traces.append({"step": step, "details": details})
        logger.debug(f"Audit trace - {step}: {details}")

    def get_traces(self) -> List[Dict[str, Any]]:
        return self.traces

def _heal_json_with_audit(text: str, audit: AuditLog) -> str:
    stack = []
    in_string = False
    escape = False

    audit.record("json_heal_start", {"original_length": len(text)})

    for char in text:
        if escape:
            escape = False
            continue

        if char == '\\':
            escape = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if not in_string:
            if char == '{':
                stack.append('{')
            elif char == '[':
                stack.append('[')
            elif char == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
            elif char == ']':
                if stack and stack[-1] == '[':
                    stack.pop()

    res = text
    healed_parts = []

    if in_string:
        res += '"'
        healed_parts.append("closed_string")

    while stack:
        top = stack.pop()
        if top == '{':
            res += '}'
            healed_parts.append("closed_object")
        else:
            res += ']'
            healed_parts.append("closed_array")

    audit.record("json_heal_end", {
        "healed_parts": healed_parts,
        "final_length": len(res),
        "is_modified": res != text
    })

    return res

def _heal_markdown_with_audit(text: str, audit: AuditLog) -> str:
    res = text
    audit.record("markdown_heal_start", {"original_length": len(text)})
    healed_parts = []

    # Fix unclosed code block
    lines = res.split('\n')
    in_code_block = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block

    if in_code_block:
        if res and not res.endswith('\n'):
            res += '\n'
        res += '```'
        healed_parts.append("closed_code_block")

    # Fix unclosed bold
    bold_count = res.count('**')
    if bold_count % 2 != 0:
        res += '**'
        healed_parts.append("closed_bold")

    # Fix unclosed table
    lines = res.split('\n')
    last_line = lines[-1].strip() if lines else ""
    if last_line.startswith('|') and not last_line.endswith('|'):
        res += '|'
        healed_parts.append("closed_table")

    audit.record("markdown_heal_end", {
        "healed_parts": healed_parts,
        "final_length": len(res),
        "is_modified": res != text
    })

    return res

def heal_content_with_audit(content: Any = "", format: str = "auto") -> Tuple[str, List[Dict[str, Any]]]:
    """
    Heals partial markdown or truncated JSON streaming output with full audit trace.
    Returns a tuple of (healed_content, audit_traces).
    """
    audit = AuditLog()

    if content is None:
        content = ""

    if not isinstance(content, str):
        try:
            content = str(content)
        except Exception:
            content = ""

    audit.record("input_normalized", {"is_empty": not bool(content.strip())})

    if not content.strip():
        return content, audit.get_traces()

    format_lower = str(format).lower() if format else "auto"

    is_json = False
    if format_lower == "json":
        is_json = True
    elif format_lower == "auto":
        stripped = content.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            is_json = True

    audit.record("format_determined", {"determined_format": "json" if is_json else "markdown"})

    if is_json:
        healed_text = _heal_json_with_audit(content, audit)
    else:
        healed_text = _heal_markdown_with_audit(content, audit)

    return healed_text, audit.get_traces()
