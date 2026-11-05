import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class VoiceMessageIntentParserBridge:
    """
    Feishu voice-to-text spoken command zero-config intent extractor.
    Cross-system data contract seamless bridge and Schema version automatic forward compatibility converter.
    """

    def __init__(self):
        pass

    def _sanitize_input(self, raw_input: Any) -> str:
        """Self-healing for dirty data"""
        if raw_input is None:
            return ""

        if isinstance(raw_input, str):
            return raw_input.strip()

        if isinstance(raw_input, bytes):
            try:
                return raw_input.decode('utf-8').strip()
            except UnicodeDecodeError:
                return ""

        if isinstance(raw_input, dict):
            # Look for common text fields
            for field in ['text', 'content', 'msg', 'voice_text', 'message']:
                if field in raw_input:
                    val = raw_input[field]
                    if isinstance(val, str):
                        return val.strip()
            # Fallback to json string if no common fields
            try:
                return json.dumps(raw_input, ensure_ascii=False)
            except Exception:
                return str(raw_input)

        return str(raw_input).strip()

    def _extract_intent_and_entities(self, text: str) -> Dict[str, Any]:
        """Extract intent and entities from spoken text."""
        text_lower = text.lower().replace(" ", "")

        intent = "unknown_intent"
        entities = {}

        # Simple rule-based extraction
        if any(keyword in text_lower for keyword in ["提成", "工资", "薪水", "算一下", "核一下"]):
            intent = "finance_commission_query"
            entities["target_module"] = "finance"
            if "提成" in text_lower:
                entities["subject"] = "commission"
        elif any(keyword in text_lower for keyword in ["请假", "年假", "病假", "调休"]):
            intent = "hr_leave_request"
            entities["target_module"] = "hr"
            if "年假" in text_lower:
                entities["leave_type"] = "annual"
            elif "病假" in text_lower:
                entities["leave_type"] = "sick"
        elif any(keyword in text_lower for keyword in ["开会", "会议", "日程"]):
            intent = "calendar_meeting_schedule"
            entities["target_module"] = "calendar"

        # Time period extraction
        if any(kw in text_lower for kw in ["这月", "本月", "这个月"]):
            entities["period"] = "current_month"
        elif any(kw in text_lower for kw in ["上月", "上个月"]):
            entities["period"] = "last_month"
        elif any(kw in text_lower for kw in ["下月", "下个月"]):
            entities["period"] = "next_month"

        confidence = 0.9 if intent != "unknown_intent" else 0.1
        if not text_lower:
            confidence = 0.0

        return {
            "intent_code": intent,
            "extracted_entities": entities,
            "parse_confidence": confidence,
            "raw_text": text
        }

    def _dynamic_schema_map(self, source_data: Dict[str, Any], target_schema_template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically identify new and old version field differences and silently map and convert.
        No manual configuration needed.
        """
        if not target_schema_template:
            return source_data

        mapped_result = {}
        for target_key, default_val in target_schema_template.items():
            tk_normalized = target_key.lower().replace("_", "")

            # 1. Exact match
            if target_key in source_data:
                mapped_result[target_key] = source_data[target_key]
                continue

            # 2. Semantic / Fuzzy match heuristics
            heuristic_map = {
                "action": "intent_code",
                "intent": "intent_code",
                "score": "parse_confidence",
                "confidence": "parse_confidence",
                "target": "extracted_entities",
                "entities": "extracted_entities",
                "text": "raw_text",
                "content": "raw_text",
                "version": "schema_version"
            }

            if target_key in heuristic_map and heuristic_map[target_key] in source_data:
                mapped_result[target_key] = source_data[heuristic_map[target_key]]
                continue

            # 3. Substring fuzzy match
            best_match_key = None
            for src_key in source_data.keys():
                sk_normalized = src_key.lower().replace("_", "")
                if tk_normalized in sk_normalized or sk_normalized in tk_normalized:
                    best_match_key = src_key
                    break

            if best_match_key:
                mapped_result[target_key] = source_data[best_match_key]
            else:
                mapped_result[target_key] = default_val # missing parameter default fallback

        return mapped_result

    def parse_intent(self, voice_text: Any, target_schema_template: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Main entry point: zero-config intent extraction and automatic schema version mapping.
        - voice_text: The spoken command string or dirty data struct.
        - target_schema_template: Optional dict representing the desired output schema format (e.g. from an older system version).
        """
        try:
            # 1. Dirty data self-healing & default fallbacks for missing params
            clean_text = self._sanitize_input(voice_text)
            if not clean_text and kwargs.get("default_text"):
                clean_text = self._sanitize_input(kwargs.get("default_text"))

            # 2. Extract intent
            canonical_data = self._extract_intent_and_entities(clean_text)
            canonical_data["schema_version"] = kwargs.get("schema_version", "v_latest")

            # 3. Schema auto-mapping and conversion
            if target_schema_template is not None:
                final_schema = self._dynamic_schema_map(canonical_data, target_schema_template)
            else:
                # If no template provided, provide a superset of fields for max forward compatibility
                final_schema = dict(canonical_data)
                final_schema["action"] = canonical_data["intent_code"]
                final_schema["score"] = canonical_data["parse_confidence"]

            return final_schema

        except Exception as e:
            logger.error(f"Intent parsing failed, triggering default fallback. Error: {e}")
            # Extreme boundary fallback - guarantee returning a valid schema struct
            fallback = {
                "intent_code": "fallback_error",
                "extracted_entities": {},
                "parse_confidence": 0.0,
                "raw_text": str(voice_text),
                "error": str(e)
            }
            if target_schema_template is not None:
                return self._dynamic_schema_map(fallback, target_schema_template)
            return fallback
