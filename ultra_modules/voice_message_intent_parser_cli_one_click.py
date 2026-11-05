import argparse
import json
import csv
import io
import sys

def parse_voice_command(text: str = "") -> dict:
    """
    Parses voice text into intent.
    Zero configuration, self-healing from dirty data.
    """
    if text is None:
        text = ""
    elif not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            text = ""

    # Clean non-printable characters except space
    cleaned_text = "".join(c for c in text if c.isprintable() or c.isspace())
    cleaned_text = cleaned_text.strip()

    if not cleaned_text:
        return {"action": "unknown", "target": "unknown", "time": "unknown", "raw": ""}

    action = "unknown"
    target = "unknown"
    time = "unknown"

    # Robust but simple heuristic keyword matching
    if "核" in cleaned_text or "查" in cleaned_text or "审" in cleaned_text:
        action = "核对"
    elif "发" in cleaned_text or "推" in cleaned_text or "传" in cleaned_text:
        action = "发送"
    elif "做" in cleaned_text or "建" in cleaned_text or "写" in cleaned_text:
        action = "创建"

    if "提成" in cleaned_text:
        target = "提成表"
    elif "工资" in cleaned_text:
        target = "工资单"
    elif "报告" in cleaned_text or "总结" in cleaned_text:
        target = "报告"

    if "这月" in cleaned_text or "本月" in cleaned_text:
        time = "本月"
    elif "上月" in cleaned_text:
        time = "上月"
    elif "今天" in cleaned_text or "今日" in cleaned_text:
        time = "今天"

    return {
        "action": action,
        "target": target,
        "time": time,
        "raw": cleaned_text
    }

def export_result(data: dict = None, fmt: str = "json") -> str:
    """
    Exports intent data to JSON or Excel/CSV format.
    Zero-config fault tolerance.
    """
    if not isinstance(data, dict):
        data = {}

    if not isinstance(fmt, str):
        fmt = "json"

    fmt = fmt.lower().strip()
    if not fmt:
        fmt = "json"

    safe_data = {
        "action": str(data.get("action", "unknown")),
        "target": str(data.get("target", "unknown")),
        "time": str(data.get("time", "unknown")),
        "raw": str(data.get("raw", ""))
    }

    if fmt in ["excel", "csv"]:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["action", "target", "time", "raw"], lineterminator="\n")
        writer.writeheader()
        writer.writerow(safe_data)
        return output.getvalue().strip()
    else:
        return json.dumps(safe_data, ensure_ascii=False)

def cli_main(args=None):
    """
    One-click CLI entry point.
    """
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Voice Message Intent Parser CLI")
    parser.add_argument("--text", type=str, default="把这月提成表核一下", help="Voice text to parse")
    parser.add_argument("--format", type=str, default="json", choices=["json", "excel", "csv"], help="Output format")

    parsed_args, _ = parser.parse_known_args(args)

    parsed_intent = parse_voice_command(parsed_args.text)
    result = export_result(parsed_intent, parsed_args.format)
    print(result)
    return result

if __name__ == "__main__":
    cli_main()
