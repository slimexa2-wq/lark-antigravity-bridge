import json
import re
from typing import Any, Dict, Optional

def heal_markdown(text: str) -> str:
    if not text:
        return ""

    # Heal unclosed code blocks
    # Count occurrences of ```
    code_block_matches = list(re.finditer(r'```', text))
    if len(code_block_matches) % 2 != 0:
        # If there's an odd number of ```, append closing ```
        if not text.endswith('\n'):
            text += '\n'
        text += '```'

    # Heal unclosed bold markers
    # We find all non-overlapping **
    bold_matches = list(re.finditer(r'\*\*', text))
    # Note: A real markdown parser is complex, but for heuristics, we just close dangling `**` if it's odd
    if len(bold_matches) % 2 != 0:
        text += '**'

    # Heal unclosed tables
    # Check if the last line is part of a table but doesn't have a closing pipe if it started with one,
    # or just simple heuristics: if we are in a table block and it's truncated,
    # we don't strictly *need* to close it in markdown unless the markdown parser fails.
    # We will close the last row if it's missing a trailing `|` while it has a leading `|`.
    lines = text.split('\n')
    if lines:
        last_line = lines[-1].strip()
        if last_line.startswith('|') and not last_line.endswith('|'):
            lines[-1] = lines[-1] + ' |'
            text = '\n'.join(lines)

    return text

def heal_json(text: str) -> Any:
    if not text:
        return {}

    text = text.strip()

    # Try parsing first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Heuristic based healing for truncated json

    # Remove trailing commas
    text = re.sub(r',\s*$', '', text)
    # Remove trailing colon
    text = re.sub(r':\s*$', '', text)

    # Count quotes
    if text.count('"') % 2 != 0:
        text += '"'

    # Count brackets
    open_curly = text.count('{')
    close_curly = text.count('}')

    open_square = text.count('[')
    close_square = text.count(']')

    # We need to determine the correct closing order.
    # The simplest heuristic is to just count and close them.
    # For a perfect heuristic we'd track a stack. Let's do a stack.
    stack = []
    in_string = False
    escape = False

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
            if char in '{[':
                stack.append(char)
            elif char == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
            elif char == ']':
                if stack and stack[-1] == '[':
                    stack.pop()

    # Now close everything in the stack in reverse order
    while stack:
        char = stack.pop()
        if char == '{':
            text += '}'
        elif char == '[':
            text += ']'

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback to string if completely broken
        return {"error": "unrecoverable json", "raw_content": text}

def generate_explainer_card(raw_content: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if raw_content is None:
        raw_content = ""
    if context is None:
        context = {}

    healed_markdown = heal_markdown(raw_content)

    # Try to extract JSON if there's any JSON block, otherwise heal_json the whole text if it looks like json
    json_data = {}
    if raw_content.strip().startswith('{') or raw_content.strip().startswith('['):
        json_data = heal_json(raw_content)
    else:
        # Try to find a JSON block
        json_match = re.search(r'```json(.*?)```', healed_markdown, re.DOTALL)
        if json_match:
            json_data = heal_json(json_match.group(1))

    # Generate Plain Explainer Markdown (一页纸摘要)
    plain_markdown = f"""# 分析结论卡\n\n## 内容摘要\n{healed_markdown}"""

    # Generate Simplified HTML Card
    # A simple HTML representation
    html_card = f"""
    <div class="explainer-card" style="padding: 16px; border: 1px solid #ccc; border-radius: 8px;">
        <h2 style="margin-top: 0;">分析结论卡</h2>
        <div class="card-content">
            <pre style="white-space: pre-wrap; font-family: sans-serif;">{healed_markdown}</pre>
        </div>
        <div class="card-meta" style="font-size: 0.8em; color: #666; margin-top: 16px;">
            <p><strong>Context:</strong> {json.dumps(context)}</p>
            <p><strong>Extracted Data:</strong> {json.dumps(json_data)}</p>
        </div>
    </div>
    """

    return {
        "markdown": plain_markdown,
        "html": html_card.strip(),
        "json_data": json_data
    }
