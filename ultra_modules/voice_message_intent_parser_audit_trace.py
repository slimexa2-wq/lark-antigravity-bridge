import re
import time
import datetime
from typing import Dict, Any, List, Optional

class AuditTrail:
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def record(self, step: str, before: Any, after: Any, rule: str):
        self.logs.append({
            "timestamp_ms": int(time.time() * 1000),
            "step": step,
            "before": before,
            "after": after,
            "rule": rule
        })

class IntentExtractionResult:
    def __init__(self, raw_input: Any):
        self.raw_input = raw_input
        self.normalized_input = ""
        self.intent = "unknown"
        self.entities: Dict[str, Any] = {}
        self.audit_trail = AuditTrail()

    def to_frontend(self) -> Dict[str, Any]:
        """
        Extremely clean payload for frontend.
        Zero complex parameters. Just the final actionable intent and entities.
        """
        return {
            "intent": self.intent,
            "entities": self.entities
        }

    def to_backend_audit(self) -> Dict[str, Any]:
        """
        Full diagnostic payload for backend logging/analytics.
        """
        return {
            "raw_input": self.raw_input,
            "normalized_input": self.normalized_input,
            "intent": self.intent,
            "entities": self.entities,
            "audit_logs": self.audit_trail.logs
        }

class VoiceIntentParser:
    def __init__(self):
        self.intent_keywords = {
            "review_commission": ["提成", "工资", "奖金", "绩效", "核算"],
            "schedule_meeting": ["开会", "会议", "碰头", "对齐"],
            "submit_report": ["日报", "周报", "月报", "总结"]
        }

    def parse(self, text: Any, user_context: Optional[Dict[str, Any]] = None) -> IntentExtractionResult:
        result = IntentExtractionResult(raw_input=text)

        # 1. Fault Tolerance: Dirty Data / Null Handling
        if text is None:
            result.audit_trail.record("input_repair", "None", "", "Null input replaced with empty string")
            text = ""
        elif not isinstance(text, str):
            try:
                # Handle objects that might fail str() ungracefully
                text_str = str(text)
                result.audit_trail.record("input_repair", type(text).__name__, "str", "Non-string input casted to string")
                text = text_str
            except Exception:
                text = ""
                result.audit_trail.record("input_repair", "Uncastable", "", "Failed to cast input, fallback to empty string")

        # Extreme boundary: extremely long text (truncate silently)
        if len(text) > 5000:
            result.audit_trail.record("boundary_truncation", len(text), 5000, "Input exceeds max length, silently truncated")
            text = text[:5000]

        # 2. Normalization: Deduplication & Stop words
        original_text = text
        normalized = text.strip()
        # Remove redundant punctuation
        normalized = re.sub(r'([。，！？,!?])\1+', r'\1', normalized)

        # Remove verbal tics
        tics = ["那个", "就是说", "然后", "呃", "啊", "嗯", "这个"]
        for tic in tics:
            if tic in normalized:
                normalized = normalized.replace(tic, "")
                result.audit_trail.record("denoise", f"Contains {tic}", "Removed", f"Removed verbal filler: {tic}")

        if original_text != normalized:
            result.audit_trail.record("normalization", original_text, normalized, "Cleaned up spaces, repeated punctuation and fillers")

        result.normalized_input = normalized

        if not normalized:
            result.intent = "noop"
            result.audit_trail.record("intent_resolution", "", "noop", "Empty input resolves to no-op")
            return result

        # 3. Intent Resolution
        matched = False
        for intent, keywords in self.intent_keywords.items():
            for kw in keywords:
                if kw in normalized:
                    result.intent = intent
                    result.audit_trail.record("intent_resolution", "unknown", intent, f"Matched keyword: {kw}")
                    matched = True
                    break
            if matched:
                break

        if not matched:
            result.audit_trail.record("intent_resolution", "unknown", "unknown", "No keywords matched")

        # 4. Entity Extraction & Sensible Defaults (Zero Configuration)
        user_context = user_context or {}
        default_user_id = user_context.get("user_id", "current_user")

        if result.intent == "review_commission":
            now = datetime.datetime.now()
            default_year = now.year
            default_month = now.month

            target_year = default_year
            target_month = default_month

            # Cross-year boundary logic
            if "上个月" in normalized or "上月" in normalized:
                target_month -= 1
                if target_month == 0:
                    target_month = 12
                    target_year -= 1
                    result.audit_trail.record("boundary_handling", f"M:{default_month}", f"Y:{target_year}, M:{target_month}", "Cross-year boundary handled for last month")
            elif "去年" in normalized:
                target_year -= 1
                result.audit_trail.record("boundary_handling", f"Y:{default_year}", f"Y:{target_year}", "Handled last year boundary")

            result.entities["year"] = target_year
            result.entities["month"] = target_month
            result.audit_trail.record("entity_fallback", "missing", f"{target_year}-{target_month}", "Time entities inferred with safe defaults")

            result.entities["target"] = default_user_id
            result.audit_trail.record("entity_fallback", "missing", default_user_id, "Target defaulting to implicit current user")

        elif result.intent == "schedule_meeting":
            # Set default duration to 30 mins
            result.entities["duration_minutes"] = 30
            result.audit_trail.record("entity_fallback", "missing", 30, "Meeting duration default to 30 minutes")
            result.entities["participants"] = [default_user_id]
            result.audit_trail.record("entity_fallback", "missing", [default_user_id], "Participants default to initiator")

        elif result.intent == "submit_report":
            # Default to weekly report
            result.entities["report_type"] = "weekly"
            if "日报" in normalized:
                result.entities["report_type"] = "daily"
            elif "月报" in normalized:
                result.entities["report_type"] = "monthly"
            result.audit_trail.record("entity_fallback", "missing", result.entities["report_type"], "Report type defaulting applied")

        return result
