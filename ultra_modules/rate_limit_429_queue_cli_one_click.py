import json
import csv
import sys
import os
import time
from typing import Any, Dict, List, Optional
try:
    from .rate_limit_429_queue_core_engine import init_state, process_request, process_queue
except ImportError:
    from rate_limit_429_queue_core_engine import init_state, process_request, process_queue

class DualModeOutputAdapter:
    """
    Adapter to output data in JSON or Excel/CSV format with zero-configuration tolerance.
    """
    def __init__(self, mode: str = "json", output_path: str = "output"):
        self.mode = mode if mode in ["json", "csv"] else "json"
        self.output_path = output_path if output_path else "output"

    def export(self, data: Any, fallback_mode: bool = True) -> bool:
        """
        Exports data. If dirty data is given, it tries to heal it.
        If file writing fails, it falls back to print or fails silently if fallback_mode is False.
        """
        if not isinstance(data, list):
            data = [data] if data else []

        # Clean data elements
        clean_data = []
        for item in data:
            if isinstance(item, dict):
                clean_data.append(item)
            elif item is not None:
                clean_data.append({"data": str(item)})

        if self.mode == "json":
            return self._export_json(clean_data, fallback_mode)
        else:
            return self._export_csv(clean_data, fallback_mode)

    def _export_json(self, data: List[Dict[str, Any]], fallback_mode: bool) -> bool:
        file_path = f"{self.output_path}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            if fallback_mode:
                print(json.dumps(data, ensure_ascii=False, indent=2))
                return True
            return False

    def _export_csv(self, data: List[Dict[str, Any]], fallback_mode: bool) -> bool:
        file_path = f"{self.output_path}.csv"
        try:
            if not data:
                with open(file_path, "w", encoding="utf-8") as f:
                    pass
                return True

            keys = set()
            for item in data:
                keys.update(item.keys())

            with open(file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(keys))
                writer.writeheader()
                writer.writerows(data)
            return True
        except Exception:
            if fallback_mode:
                print(f"Failed to write CSV to {file_path}, falling back to JSON print")
                print(json.dumps(data, ensure_ascii=False, indent=2))
                return True
            return False


def one_click_cli_entry(
    requests: Optional[List[Any]] = None,
    mode: str = "json",
    output_path: str = "output"
) -> bool:
    """
    Zero-parameter one-click CLI entry.
    """
    # Missing param defaults
    if requests is None:
        requests = [{"id": 1, "req": "default_1"}, {"id": 2, "req": "default_2"}]
    if not isinstance(requests, list):
        requests = [requests]

    # Initialize rate limit engine with very small capacity to trigger queueing
    state = init_state(capacity=1, refill_rate=0.5)

    final_results = []

    # Process incoming requests
    for req in requests:
        state, success = process_request(state, req)
        if success:
            final_results.append({"status": "processed", "request": req})

    # Simulate waiting for token bucket to refill so queue can be processed
    time.sleep(2.1)

    # Process remaining queue
    state, processed_from_queue = process_queue(state)
    for req in processed_from_queue:
         final_results.append({"status": "processed_from_queue", "request": req})

    # Any requests still in queue
    for req in state.get("queue", []):
         final_results.append({"status": "queued", "request": req})

    adapter = DualModeOutputAdapter(mode=mode, output_path=output_path)
    return adapter.export(final_results)

def run_cli():
    """
    CLI runner, zero parameters required.
    """
    print("Running rate limit queue one-click CLI...")
    args = sys.argv[1:]
    mode = "json"
    if args and args[0] in ["json", "csv"]:
        mode = args[0]

    success = one_click_cli_entry(mode=mode)
    if success:
        print("Success")
    else:
        print("Failed")

if __name__ == "__main__":
    run_cli()
