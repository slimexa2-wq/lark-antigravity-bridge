import json
import logging
from typing import Any, Dict, Optional, Union

# Set up logging silently
logger = logging.getLogger(__name__)


class VoiceMessageIntentParserPlainExplainer:
    """
    A robust, fault-tolerant intent parser and explainer.
    Converts complex backend voice message intent calculations into
    simple, business-oriented conclusion cards in various formats.
    """

    def __init__(self) -> None:
        # Strict zero-configuration fault tolerance requires no complex setup.
        pass

    def _sanitize_confidence(self, confidence: Any) -> float:
        """Sanitizes confidence to be a float between 0.0 and 1.0."""
        try:
            val = float(confidence)
            if val < 0.0:
                return 0.0
            if val > 1.0:
                return 1.0
            return val
        except (ValueError, TypeError):
            return 0.0

    def _sanitize_intent(self, intent: Any) -> str:
        """Sanitizes intent string, providing a fallback."""
        if not intent or not isinstance(intent, str):
            return "未知操作"
        return intent.strip()

    def _sanitize_entities(self, entities: Any) -> Dict[str, Any]:
        """Sanitizes entities to ensure it is always a dictionary."""
        if not isinstance(entities, dict):
            return {}
        return entities

    def _generate_plain_summary(self, intent: str, entities: Dict[str, Any], confidence: float) -> str:
        """Generates a plain, understandable summary based on intent and entities."""
        # Provide plain language summaries
        if confidence < 0.3:
            return "无法确定您的需求，请尝试重新发送语音或换个说法。"

        summary = f"识别到的操作：{intent}。"
        if entities:
            details = []
            for k, v in entities.items():
                if v is not None and str(v).strip() != "":
                    details.append(f"【{k}】设为 {v}")
            if details:
                summary += " 涉及关键信息：" + "，".join(details) + "。"
        else:
            summary += " 暂未发现相关的补充细节。"

        return summary

    def parse_to_card(
        self,
        raw_data: Optional[Union[str, Dict[str, Any]]] = None,
        export_format: str = "markdown"
    ) -> str:
        """
        Parses intent data into a conclusion card.

        Args:
            raw_data: A dictionary containing 'intent', 'confidence', 'entities' or a JSON string.
            export_format: Output format ('json', 'markdown', 'html'). Defaults to 'markdown'.

        Returns:
            A string containing the formatted card.
        """
        # 1. Zero-configuration fault tolerance: silently handle raw_data missing or wrong type
        data = {}
        if isinstance(raw_data, str):
            try:
                data = json.loads(raw_data)
            except (json.JSONDecodeError, TypeError):
                # Silently fail to an empty dict for recovery
                data = {}
        elif isinstance(raw_data, dict):
            data = raw_data

        # 2. Extract and sanitize parameters, providing sensible defaults
        intent_raw = data.get("intent", "未知操作")
        confidence_raw = data.get("confidence", 0.0)
        entities_raw = data.get("entities", {})

        intent = self._sanitize_intent(intent_raw)
        confidence = self._sanitize_confidence(confidence_raw)
        entities = self._sanitize_entities(entities_raw)

        # 3. Generate content
        summary = self._generate_plain_summary(intent, entities, confidence)
        confidence_percentage = int(confidence * 100)

        # 4. Export to requested format, defaulting to markdown on unrecognized format
        safe_format = str(export_format).strip().lower() if isinstance(export_format, str) else "markdown"

        if safe_format == "json":
            result = {
                "title": "语音指令解析结果",
                "summary": summary,
                "confidence_score": f"{confidence_percentage}%",
                "intent": intent,
                "entities": entities
            }
            return json.dumps(result, ensure_ascii=False, indent=2)

        elif safe_format == "html":
            entities_html = ""
            if entities:
                items = "".join(f"<li><strong>{k}:</strong> {v}</li>" for k, v in entities.items())
                entities_html = f"<ul>{items}</ul>"
            else:
                entities_html = "<p>无附加参数</p>"

            return f"""
<div class="intent-card" style="border: 1px solid #ccc; padding: 16px; border-radius: 8px;">
    <h3 style="margin-top: 0; color: #333;">语音指令解析结果</h3>
    <p class="summary" style="font-size: 16px; font-weight: bold; color: #0056b3;">{summary}</p>
    <div class="details" style="background: #f9f9f9; padding: 12px; border-radius: 4px; margin-top: 12px;">
        <p><strong>核心动作:</strong> {intent}</p>
        <p><strong>可信度:</strong> {confidence_percentage}%</p>
        <strong>参数详情:</strong>
        {entities_html}
    </div>
</div>
""".strip()

        else: # Default to markdown
            entities_md = ""
            if entities:
                entities_md = "\n".join(f"- **{k}**: {v}" for k, v in entities.items())
            else:
                entities_md = "无附加参数"

            return f"""
### 🎙️ 语音指令解析结果

> **{summary}**

---

**核心动作**: `{intent}`
**可信度**: {confidence_percentage}%

**参数详情**:
{entities_md}
""".strip()
