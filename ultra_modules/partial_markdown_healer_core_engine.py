def heal_content(content: str = "", format: str = "auto") -> str:
    """
    Heals partial markdown or truncated JSON streaming output.
    Zero configuration, automatic fault tolerance.
    """
    if content is None:
        content = ""
    if not isinstance(content, str):
        try:
            content = str(content)
        except Exception:
            content = ""

    if not content.strip():
        return content

    format = str(format).lower() if format else "auto"

    is_json = False
    if format == "json":
        is_json = True
    elif format == "auto":
        stripped = content.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            is_json = True

    if is_json:
        return _heal_json(content)
    else:
        return _heal_markdown(content)


def _heal_json(text: str) -> str:
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
    if in_string:
        res += '"'

    while stack:
        top = stack.pop()
        if top == '{':
            res += '}'
        else:
            res += ']'

    return res


def _heal_markdown(text: str) -> str:
    res = text

    # 修复未闭合的代码块
    lines = res.split('\n')
    in_code_block = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block

    if in_code_block:
        if res and not res.endswith('\n'):
            res += '\n'
        res += '```'

    # 修复未闭合的粗体 (只处理包含 ** 的情况)
    bold_count = res.count('**')
    if bold_count % 2 != 0:
        res += '**'

    # 修复未闭合的表格 (最后一行以 | 开头但未以 | 结尾)
    lines = res.split('\n')
    last_line = lines[-1].strip()
    if last_line.startswith('|') and not last_line.endswith('|'):
        res += '|'

    return res
