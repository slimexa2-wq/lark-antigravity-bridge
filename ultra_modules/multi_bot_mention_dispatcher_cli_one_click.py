import json
import logging
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiBotMentionDispatcherCliOneClick:
    """
    Feishu/Lark Multi-Bot Mention Dispatcher & Result Aggregator.
    Provides simple UI/UX, zero-configuration fault tolerance, and JSON/Excel dual-mode outputs.
    """
    SUPPORTED_BOTS = ["@大肥鱼", "@招聘", "@数据", "@量化"]

    def __init__(self):
        pass

    def _clean_data(self, record: Any) -> str:
        """
        Auto-heal dirty data. Converts None to empty string, and handles dicts gracefully.
        """
        if record is None:
            return ""
        if isinstance(record, dict):
            return str(record.get('text', record.get('content', record)))
        return str(record).strip()

    def dispatch(self, records: Optional[List[Any]] = None, output_format: str = "json") -> Any:
        """
        Dispatches mentions from a list of records.
        Records can be missing (defaults to empty list), or a single item (defaults to list containing item).
        """
        if records is None:
            records = []

        if not isinstance(records, (list, tuple)):
            records = [records]

        # Fault tolerance, if format is not supported, default to json
        if output_format not in ["json", "excel"]:
            output_format = "json"

        results = []
        for record in records:
            cleaned_text = self._clean_data(record)

            mentions = []
            if cleaned_text:
                for bot in self.SUPPORTED_BOTS:
                    if bot in cleaned_text:
                        mentions.append(bot)

            status = "success" if cleaned_text else "ignored_empty"

            results.append({
                "original_record_type": type(record).__name__,
                "cleaned_text": cleaned_text,
                "mentions": mentions,
                "status": status,
            })

        return self._format_output(results, output_format)

    def _format_output(self, results: List[Dict[str, Any]], output_format: str) -> Any:
        """
        Format output into JSON dictionary or Excel-like string (CSV simulation for simplicity in backend output).
        """
        success_count = sum(1 for r in results if r["status"] == "success")
        empty_count = sum(1 for r in results if r["status"] == "ignored_empty")

        mention_counts = {bot: 0 for bot in self.SUPPORTED_BOTS}
        for r in results:
            for m in r["mentions"]:
                if m in mention_counts:
                    mention_counts[m] += 1
                else:
                    mention_counts[m] = 1 # boundary case protection

        # Filter out 0 counts to only show hit counts
        mention_counts = {k: v for k, v in mention_counts.items() if v > 0}

        summary = {
            "total_records": len(results),
            "processed_successfully": success_count,
            "ignored_empty": empty_count,
            "mention_statistics": mention_counts
        }

        if output_format == "json":
            return {
                "summary": summary,
                "details": results
            }
        elif output_format == "excel":
            # Simulate Excel output as CSV string representation
            excel_str = "Status\tCleaned Text\tMentions\n"
            for r in results:
                mentions_str = ",".join(r["mentions"]) if r["mentions"] else "None"
                excel_str += f'{r["status"]}\t{r["cleaned_text"]}\t{mentions_str}\n'

            return {
                "summary": summary,
                "excel_csv_simulation": excel_str
            }


def cli_main(records: Optional[List[Any]] = None, output_format: str = "json") -> Any:
    """
    Zero-configuration one-click CLI entry point.
    Missing parameters receive sensible defaults.
    """
    dispatcher = MultiBotMentionDispatcherCliOneClick()
    return dispatcher.dispatch(records=records, output_format=output_format)
