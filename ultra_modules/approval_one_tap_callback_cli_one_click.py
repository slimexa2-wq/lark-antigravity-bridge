import json
import csv
import io
import sys

def process_callback_status(action=None, payload=None, output_mode="json", **kwargs):
    """
    Synchronizes the status of one-tap approve/reject callbacks.
    """
    # 1. Fallback for missing/dirty parameters
    if action is None:
        action = "approve"
    if not isinstance(action, str):
        action = str(action)

    action = action.strip().lower()
    if action not in ["approve", "reject"]:
        action = "approve" # auto-healing to a safe default

    if payload is None or not isinstance(payload, dict):
        payload = {"status": "unknown"}

    # clean payload (e.g. stringify non-string keys, remove weird values)
    clean_payload = {}
    for k, v in payload.items():
        clean_key = str(k).strip()
        if not clean_key:
            clean_key = "unknown_key"
        clean_payload[clean_key] = v

    if output_mode is None:
        output_mode = "json"
    if not isinstance(output_mode, str):
        output_mode = str(output_mode)

    output_mode = output_mode.strip().lower()
    if output_mode not in ["json", "excel", "csv"]:
        output_mode = "json"

    # 2. Prepare standardized response
    result_data = {
        "sync_status": "success",
        "final_action": action,
        "processed_payload": clean_payload
    }

    # 3. Output adaptation
    if output_mode in ["excel", "csv"]:
        output = io.StringIO()
        writer = csv.writer(output)
        # Flatten for Excel/CSV
        headers = ["sync_status", "final_action", "payload_summary"]
        writer.writerow(headers)
        writer.writerow([result_data["sync_status"], result_data["final_action"], json.dumps(result_data["processed_payload"])])
        return output.getvalue()
    else:
        return json.dumps(result_data, sort_keys=True)

def run_cli():
    """
    Zero-parameter one-click CLI entry point.
    """
    # Simplest call without any parameters
    print(process_callback_status())
    return True

if __name__ == "__main__":
    run_cli()
