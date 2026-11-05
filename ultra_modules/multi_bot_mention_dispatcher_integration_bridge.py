import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class MultiBotMentionDispatcherIntegrationBridge:
    def __init__(self):
        # Configuration mapping
        self.bot_handlers = {
            "大肥鱼": self._handle_dafeiyu,
            "招聘": self._handle_zhaopin,
            "数据": self._handle_shuju,
            "量化": self._handle_lianghua
        }

    def _safe_get(self, data: Any, key: str, default: Any = None) -> Any:
        if not isinstance(data, dict):
            return default
        return data.get(key, default)

    def adapt_schema(self, payload: Any) -> Dict[str, Any]:
        """
        Silently maps old version fields to new versions for schema compatibility.
        """
        if not isinstance(payload, dict):
            return {"mentions": [], "content": str(payload) if payload else ""}

        result = {}

        # Extract mentions (handle v1: 'at_list', v2: 'mentions')
        mentions = payload.get("mentions") or payload.get("at_list") or []
        if not isinstance(mentions, list):
            mentions = []
        result["mentions"] = [str(m) for m in mentions]

        # Extract content (handle v1: 'text', v2: 'content', v3: 'msg')
        content = payload.get("content") or payload.get("text") or payload.get("msg") or ""
        result["content"] = str(content)

        # Additional metadata
        result["message_id"] = str(payload.get("message_id", payload.get("msg_id", "")))

        return result

    def _handle_dafeiyu(self, content: str) -> str:
        return "Processed by 大肥鱼: OK"

    def _handle_zhaopin(self, content: str) -> str:
        return "Processed by 招聘: OK"

    def _handle_shuju(self, content: str) -> str:
        return "Processed by 数据: OK"

    def _handle_lianghua(self, content: str) -> str:
        return "Processed by 量化: OK"

    def dispatch(self, mentions: List[str], content: str) -> List[Dict[str, str]]:
        """
        Routes content to specific bots based on mentions.
        """
        results = []
        for mention in mentions:
            # Handle large amount of mentions (boundary case)
            if len(results) > 100:
                results.append({"bot": "System", "status": "Error: Too many mentions"})
                break

            bot_name = mention.replace("@", "").strip()
            if bot_name in self.bot_handlers:
                try:
                    result = self.bot_handlers[bot_name](content)
                    results.append({"bot": bot_name, "status": result})
                except Exception as e:
                    logger.error(f"Error handling bot {bot_name}: {e}")
                    results.append({"bot": bot_name, "status": f"Error: {str(e)}"})
            else:
                results.append({"bot": bot_name, "status": "Unknown bot"})

        return results

    def generate_summary_card(self, dispatch_results: List[Dict[str, str]]) -> str:
        """
        Generates a Feishu card format string.
        Core rule: Max 3 lines text summary to prevent mobile screen flooding.
        """
        if not dispatch_results:
            return "No bots mentioned.\nNo actions taken.\nEnd of report."

        success_count = sum(1 for r in dispatch_results if "Processed by" in r.get("status", ""))
        error_count = sum(1 for r in dispatch_results if "Error" in r.get("status", ""))
        unknown_count = sum(1 for r in dispatch_results if "Unknown" in r.get("status", ""))

        total = len(dispatch_results)

        line1 = f"Total mentions: {total}, Processed successfully: {success_count}."
        line2 = f"Errors: {error_count}, Unknown bots: {unknown_count}."

        if success_count == total:
            line3 = "All bots processed the request successfully."
        elif success_count > 0:
            line3 = "Partial success. Review errors/unknowns."
        else:
            line3 = "No successful processing occurred."

        return f"{line1}\n{line2}\n{line3}"

    def process_webhook(self, payload: Any) -> str:
        """
        Main entry point for processing incoming webhooks.
        """
        # 1. Adapt schema (self-healing for dirty data)
        adapted_data = self.adapt_schema(payload)

        # 2. Dispatch to bots
        results = self.dispatch(adapted_data["mentions"], adapted_data["content"])

        # 3. Generate summary card (max 3 lines)
        return self.generate_summary_card(results)
