import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MobileTableDigestFormatterCliOneClick:
    def __init__(self):
        # Setting up defaults for fallback
        self.default_data = {
            "summary": "Demo table summary: everything is OK.",
            "anomalies": [],
            "file_url": "https://example.com/demo.xlsx",
            "file_name": "demo.xlsx",
            "total_rows": 100,
            "processed_rows": 100
        }

    def _parse_input(self, data_input: Optional[str] = None) -> Dict[str, Any]:
        """
        Parses JSON strings, mock-parses .xlsx file paths, and falls back gracefully for dirty data.
        """
        if not data_input:
            return self.default_data

        data_input_str = str(data_input).strip()

        if data_input_str.endswith('.xlsx'):
            # Mock parse .xlsx path
            return {
                "summary": f"Data parsed from {data_input_str}",
                "anomalies": [],
                "file_url": f"https://example.com/{data_input_str}",
                "file_name": data_input_str,
                "total_rows": 50,
                "processed_rows": 50
            }

        try:
            parsed_data = json.loads(data_input_str)
            if not isinstance(parsed_data, dict):
                logger.warning("Input is valid JSON but not a dictionary. Falling back to default.")
                return self.default_data

            # Merge with default to handle missing keys gracefully
            result = self.default_data.copy()
            result.update(parsed_data)
            return result
        except json.JSONDecodeError:
            logger.warning("Invalid JSON input. Falling back to default.")
            return self.default_data
        except Exception as e:
            logger.error(f"Unexpected error parsing input: {e}. Falling back to default.")
            return self.default_data

    def _format_card(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a Lark interactive card JSON with exactly a 3-line core digest,
        highlighted anomalies (if any), and an attachment download button.
        """
        summary = parsed_data.get('summary', 'No summary available.')
        total_rows = parsed_data.get('total_rows', 0)
        processed_rows = parsed_data.get('processed_rows', 0)

        # Line 1: Summary
        # Line 2: Stats
        # Line 3: Anomalies info
        line1 = f"**Summary:** {summary}"
        line2 = f"**Stats:** Processed {processed_rows}/{total_rows} rows."

        anomalies = parsed_data.get('anomalies', [])
        if anomalies:
            anomaly_str = ", ".join(str(a) for a in anomalies[:3]) # Show up to 3 anomalies
            if len(anomalies) > 3:
                anomaly_str += "..."
            line3 = f"**<font color='red'>Anomalies Detected:</font>** {anomaly_str}"
        else:
            line3 = "**Anomalies:** None detected."

        digest_text = f"{line1}\n{line2}\n{line3}"

        file_url = parsed_data.get('file_url', '')
        file_name = parsed_data.get('file_name', 'attachment')

        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "Table Digest"
                },
                "template": "blue" if not anomalies else "red"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": digest_text
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": f"Download {file_name}"
                            },
                            "type": "primary",
                            "url": file_url
                        }
                    ]
                }
            ]
        }
        return card

    def run_cli(self, data_input: Optional[str] = None) -> str:
        """
        Main entry point for CLI usage. Defaults to demo data if no arguments are provided.
        Returns the JSON string of the Lark interactive card.
        """
        parsed_data = self._parse_input(data_input)
        card = self._format_card(parsed_data)
        return json.dumps(card, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    import sys
    formatter = MobileTableDigestFormatterCliOneClick()

    if len(sys.argv) > 1:
        # Pass all arguments as a single string or the first argument
        input_data = " ".join(sys.argv[1:])
        print(formatter.run_cli(input_data))
    else:
        print(formatter.run_cli())
