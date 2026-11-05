import json
from typing import Any, Dict, Optional

class QuickCommandRouter:
    VALID_COMMANDS = ["/周报", "/提成", "/漫剧", "/标书", "/状态"]

    def __init__(self, default_command: str = "/状态"):
        self.default_command = default_command

    def clean_args(self, args: Any) -> Dict[str, Any]:
        if args is None:
            return {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                return {"raw_input": args}
        if not isinstance(args, dict):
            return {"raw_input": str(args)}

        # Clean dirty data in dict
        cleaned = {}
        for k, v in args.items():
            if k is None or str(k).strip() == "":
                k = "unknown_key"
            cleaned[str(k).strip()] = v
        return cleaned

    def execute(self, command: Optional[str] = None, args: Any = None, output_format: Optional[str] = None) -> Dict[str, Any]:
        if command is None or not isinstance(command, str) or command.strip() not in self.VALID_COMMANDS:
            command = self.default_command
        else:
            command = command.strip()

        clean_args = self.clean_args(args)

        if output_format is None or not isinstance(output_format, str) or output_format.lower() not in ["json", "excel", "csv"]:
            output_format = "json"
        else:
            output_format = output_format.lower()

        data = self._route_command(command, clean_args)

        return self._format_output(data, output_format)

    def _route_command(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if command == "/周报":
            return {"title": "Weekly Report", "content": args.get("content", "Default weekly report content"), "status": "generated"}
        elif command == "/提成":
            amount = args.get("amount", 0)
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                amount = 0.0
            return {"title": "Commission", "amount": amount, "calculated": amount * 0.1}
        elif command == "/漫剧":
            return {"title": "Manga Drama", "name": args.get("name", "Unknown Drama"), "episodes": args.get("episodes", 1)}
        elif command == "/标书":
            return {"title": "Bid Document", "project": args.get("project", "Default Project"), "price": args.get("price", 10000)}
        else: # /状态 is the fallback and one of the commands
            return {"title": "System Status", "health": "ok", "uptime": "99.9%"}

    def _format_output(self, data: Dict[str, Any], output_format: str) -> Dict[str, Any]:
        result = {
            "status": "success",
            "format": output_format,
            "data": data,
            "output": ""
        }
        if output_format == "json":
            result["output"] = json.dumps(data, ensure_ascii=False)
        else:
            # Generate a mock csv/excel string
            headers = list(data.keys())
            values = [str(data[k]) for k in headers]
            csv_str = ",".join(headers) + "\n" + ",".join(values)
            result["output"] = csv_str

        return result

def cli_entry_point(command: Optional[str] = None, args: Any = None, output_format: Optional[str] = None) -> Dict[str, Any]:
    """
    Zero-parameter one-click CLI entry point.
    """
    router = QuickCommandRouter()
    return router.execute(command, args, output_format)

if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(cli_entry_point(), ensure_ascii=False, indent=2))
