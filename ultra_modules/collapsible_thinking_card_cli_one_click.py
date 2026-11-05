import json
from typing import Any, Dict, Optional, Union
from ultra_modules.collapsible_thinking_card_core_engine import build_collapsible_thinking_card


def adapt_input_data(data: Any = None) -> Dict[str, Any]:
    """
    JSON/Excel dual-mode adapter with extreme fault tolerance.
    Silently cleans dirty data and provides fallback defaults.
    """
    if data is None:
        return {}

    # If it's a string, try parsing as JSON.
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return parsed
            return {"raw_value": parsed}
        except Exception:
            # Not valid JSON, maybe a plain string from Excel
            return {"raw_value": data.strip() if data.strip() else None}

    if isinstance(data, dict):
        return data

    if isinstance(data, list):
        if not data:
            return {}
        first_item = data[0]
        if isinstance(first_item, dict):
            return first_item
        return {"raw_list": data}

    try:
        # Catch all other objects
        return {"raw_object": str(data)}
    except Exception:
        return {}


def generate_one_click_cli_output(
    input_data: Optional[Any] = None,
    title: Optional[str] = None,
    link: Optional[str] = None
) -> Dict[str, Any]:
    """
    Zero-parameter one-click CLI entry.
    Extracts 'conclusion' and 'thinking_process' from adapted data if available.
    """
    adapted = adapt_input_data(input_data)

    # Try to extract reasonable fields if present, else fallback
    conclusion = adapted.get("conclusion", adapted.get("raw_value", adapted.get("raw_list", adapted.get("raw_object"))))
    thinking = adapted.get("thinking_process", adapted.get("thinking", adapted.get("process")))

    # If title was provided in data but not as explicit arg
    if title is None:
        title = adapted.get("title")

    if link is None:
        link = adapted.get("link", adapted.get("url"))

    return build_collapsible_thinking_card(
        conclusion=conclusion,
        thinking_process=thinking,
        title=title,
        card_link=link,
        show_undo=True
    )

if __name__ == "__main__":
    # One-click CLI execution
    print(json.dumps(generate_one_click_cli_output(), ensure_ascii=False, indent=2))
