import json

class MultiBotMentionDispatcherAuditTrace:
    def __init__(self):
        self.audit_trace = []

    def log_trace(self, action: str, details: dict):
        self.audit_trace.append({
            "action": action,
            "details": details
        })

    def process_mentions(self, mentions=None, **kwargs):
        """
        Process multiple bot mentions with strict fault tolerance, deduplication, and tracing.
        Returns a simplified result card.
        """
        # Ensure fallback for missing mentions
        if mentions is None:
            mentions = []

        self.audit_trace = []
        self.log_trace("init", {"raw_mentions": mentions, "kwargs": kwargs})

        result_card = {
            "valid_mentions": [],
            "summary": "No mentions processed"
        }

        try:
            # Type self-healing
            if not isinstance(mentions, list):
                if isinstance(mentions, dict):
                    mentions = [mentions]
                else:
                    mentions = []

            self.log_trace("type_correction", {"corrected_mentions": mentions})

            seen_bot_ids = set()
            processed_mentions = []

            for item in mentions:
                try:
                    if not isinstance(item, dict):
                        self.log_trace("dirty_data_dropped", {"item": item, "reason": "Not a dict"})
                        continue

                    bot_id = item.get("bot_id")
                    bot_name = item.get("bot_name", "Unknown Bot")
                    message = item.get("message", "")

                    if not bot_id:
                        self.log_trace("dirty_data_dropped", {"item": item, "reason": "Missing bot_id"})
                        continue

                    if bot_id in seen_bot_ids:
                        self.log_trace("duplicate_dropped", {"bot_id": bot_id})
                        continue

                    seen_bot_ids.add(bot_id)
                    processed_item = {
                        "bot_id": bot_id,
                        "bot_name": bot_name,
                        "message": str(message)
                    }
                    processed_mentions.append(processed_item)
                    self.log_trace("mention_accepted", {"processed_item": processed_item})
                except Exception as e:
                    self.log_trace("item_processing_error", {"item": item, "error": str(e)})
                    # Silent self-healing per item
                    continue

            if processed_mentions:
                result_card["valid_mentions"] = processed_mentions
                result_card["summary"] = f"Processed {len(processed_mentions)} valid mention(s)"
            else:
                result_card["summary"] = "No valid mentions found"

            self.log_trace("finalize", {"result_card": result_card})

        except Exception as e:
            # Extreme boundary crash prevention
            self.log_trace("extreme_failure_caught", {"error": str(e)})
            result_card["valid_mentions"] = []
            result_card["summary"] = "Internal error handled safely"

        return result_card

    def get_audit_trace(self):
        return self.audit_trace
