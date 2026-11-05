import argparse
import json
import os
import sys

class AttachmentAutoRouter:
    """
    Routes files to different business logic engines automatically.
    Supported engines: Weekly Report (周报), Commission (提成), Bid Document (标书), Comic (漫剧).
    """

    def __init__(self, mode="json"):
        self.mode = mode if mode in ["json", "excel"] else "json"

    def heal_data(self, filename: str) -> str:
        """
        Self-heals dirty data (e.g., stripping spaces, lowercasing, handling unexpected prefixes).
        """
        if not filename:
            return "unknown_file.txt"
        # Basic healing: strip spaces, lowercase for matching, remove paths
        healed = os.path.basename(filename).strip().lower()
        if not healed:
            return "unknown_file.txt"
        return healed

    def route(self, filename: str) -> dict:
        """
        Routes the file to the correct engine based on healed filename heuristics.
        """
        healed_name = self.heal_data(filename)

        if "周报" in healed_name or "weekly" in healed_name or "report" in healed_name:
            engine = "Weekly Report Engine"
            category = "周报"
        elif "提成" in healed_name or "commission" in healed_name or "bonus" in healed_name:
            engine = "Commission Engine"
            category = "提成"
        elif "标书" in healed_name or "bid" in healed_name or "tender" in healed_name:
            engine = "Bid Document Engine"
            category = "标书"
        elif "漫剧" in healed_name or "comic" in healed_name or "manga" in healed_name:
            engine = "Comic Engine"
            category = "漫剧"
        else:
            engine = "Fallback Engine"
            category = "未知/默认"

        result = {
            "original_filename": filename,
            "healed_filename": healed_name,
            "engine": engine,
            "category": category,
            "status": "routed",
        }

        return result

    def process_and_output(self, filename: str) -> str:
        """
        Processes the file and returns the output in the requested format.
        """
        result = self.route(filename)

        if self.mode == "excel":
            # For simplicity, returning a simulated CSV/Excel format as string
            return f"Filename,HealedName,Engine,Category,Status\n{result['original_filename']},{result['healed_filename']},{result['engine']},{result['category']},{result['status']}"
        else:
            return json.dumps(result, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Attachment Auto Router CLI")
    # Zero parameter one-click execution: we provide default fallback file and mode
    parser.add_argument("--file", type=str, default="周报_2023.xlsx", help="File to route (optional)")
    parser.add_argument("--mode", type=str, choices=["json", "excel"], default="json", help="Output mode (optional)")

    # For zero-config CLI, we allow running without any arguments
    args = parser.parse_args()

    router = AttachmentAutoRouter(mode=args.mode)
    output = router.process_and_output(args.file)
    print(output)

if __name__ == "__main__":
    main()
