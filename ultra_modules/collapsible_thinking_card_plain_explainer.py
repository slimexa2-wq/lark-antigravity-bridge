import json

class PlainExplainerCardBuilder:
    """
    A builder for translating complex background logic into a plain-language summary card.
    Supports default collapse for thinking process, conclusion first, and one-click undo.
    Outputs to Lark JSON, Markdown, and HTML.
    """

    def __init__(self, data=None):
        self.data = self._heal_data(data)

    def _heal_data(self, data):
        """
        Auto-heal dirty data and provide sensible defaults for missing parameters.
        """
        if not isinstance(data, dict):
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    data = {}
            else:
                data = {}

        # Fill missing with sensible defaults
        healed_data = {
            "conclusion": data.get("conclusion", "系统已完成处理，一切正常。"),
            "thinking_process": data.get("thinking_process", "后台自动推导与处理过程已隐藏。"),
            "undo_action_id": data.get("undo_action_id", "default_undo_id"),
            "status": data.get("status", "success")
        }

        # Guard against extreme values or incorrect types in provided dict
        if not isinstance(healed_data["conclusion"], str):
            healed_data["conclusion"] = str(healed_data["conclusion"])
        if not isinstance(healed_data["thinking_process"], str):
            healed_data["thinking_process"] = str(healed_data["thinking_process"])
        if not isinstance(healed_data["undo_action_id"], str):
            healed_data["undo_action_id"] = str(healed_data["undo_action_id"])

        # Truncate extremely long strings to prevent layout breaks (e.g. max 5000 chars)
        healed_data["conclusion"] = healed_data["conclusion"][:5000]
        healed_data["thinking_process"] = healed_data["thinking_process"][:10000]

        return healed_data

    def build_json_card(self):
        """
        Build Feishu (Lark) message card JSON string.
        """
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "blue" if self.data["status"] == "success" else "red",
                "title": {
                    "content": "业务处理摘要",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**💡 结论**\n{self.data['conclusion']}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "lark_md",
                            "content": f"<details><summary>查看推理过程 (后台已自动处理复杂逻辑)</summary>\n{self.data['thinking_process']}\n</details>"
                        }
                    ]
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "content": "撤回 (Undo)",
                                "tag": "plain_text"
                            },
                            "type": "primary",
                            "value": {
                                "action_type": "undo",
                                "undo_id": self.data["undo_action_id"]
                            }
                        }
                    ]
                }
            ]
        }
        return json.dumps(card, ensure_ascii=False)

    def build_markdown(self):
        """
        Build plain Markdown representation.
        """
        return (
            f"## 业务处理摘要\n\n"
            f"**💡 结论**\n{self.data['conclusion']}\n\n"
            f"---\n\n"
            f"<details><summary>查看推理过程 (后台已自动处理复杂逻辑)</summary>\n\n"
            f"{self.data['thinking_process']}\n\n"
            f"</details>\n\n"
            f"---\n"
            f"[撤回 (Undo) - ActionID: {self.data['undo_action_id']}]"
        )

    def build_html(self):
        """
        Build simple HTML representation.
        """
        return (
            f"<div>\n"
            f"  <h2>业务处理摘要</h2>\n"
            f"  <p><strong>💡 结论</strong><br>{self.data['conclusion']}</p>\n"
            f"  <hr>\n"
            f"  <details>\n"
            f"    <summary>查看推理过程 (后台已自动处理复杂逻辑)</summary>\n"
            f"    <p>{self.data['thinking_process']}</p>\n"
            f"  </details>\n"
            f"  <hr>\n"
            f"  <button data-action-id='{self.data['undo_action_id']}'>撤回 (Undo)</button>\n"
            f"</div>"
        )


def build_explainer_card(data=None, output_format="json"):
    """
    Build a plain explainer card in the requested format.

    Args:
        data: Dictionary of data including conclusion, thinking_process, undo_action_id.
              Supports dirty/empty data by auto-healing.
        output_format: The format to export. Options: "json", "markdown" (or "md"), "html".
    """
    builder = PlainExplainerCardBuilder(data)

    if not isinstance(output_format, str):
        output_format = "json"

    fmt = output_format.lower()
    if fmt in ["markdown", "md"]:
        return builder.build_markdown()
    elif fmt == "html":
        return builder.build_html()
    else:
        # Default to Lark JSON card format
        return builder.build_json_card()
