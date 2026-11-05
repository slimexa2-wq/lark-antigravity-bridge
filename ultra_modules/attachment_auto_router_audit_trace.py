import re
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

class DifferenceHighlighter:
    """Helper to generate a diff of repaired strings."""
    @staticmethod
    def highlight(original: str, repaired: str) -> str:
        if original == repaired:
            return "No changes"
        return f"- {original}\n+ {repaired}"

class AuditLogger:
    """Silent record keeping for routing, deduplication, and healing processes."""
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def log(self, action: str, details: Dict[str, Any]):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": details
        }
        self.logs.append(entry)

    def get_logs(self) -> List[Dict[str, Any]]:
        return self.logs

class AttachmentAutoRouterAuditTrace:
    def __init__(self):
        self.audit_logger = AuditLogger()
        self.seen_files = set()

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize invalid characters in filenames."""
        if not filename:
            return ""
        # Remove any character that is not alphanumeric, dot, underscore, or dash
        # We also want to keep Chinese characters for Feishu context, so \w covers it
        # Actually, let's just strip control chars, and weird symbols.
        # A simple regex for safe chars: letters, numbers, dot, dash, underscore, space, chinese chars
        # For dirty data self-healing, let's remove any non-printable or suspicious characters.
        repaired = re.sub(r'[^\w\.\-\s]', '', filename).strip()

        # Replace multiple spaces with single space
        repaired = re.sub(r'\s+', ' ', repaired)

        if filename != repaired:
            diff = DifferenceHighlighter.highlight(filename, repaired)
            self.audit_logger.log("sanitize", {"original": filename, "repaired": repaired, "diff": diff})

        return repaired

    def route(self, filename: Optional[str] = None, file_content: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Main entry point for routing files.
        Returns a clean dictionary intended for the frontend.
        """
        self.audit_logger.log("route_request", {"filename": filename, "has_content": bool(file_content)})

        # Handle missing parameter fallback
        if not filename:
            filename = "default_attachment.txt"
            self.audit_logger.log("missing_parameter_fallback", {"assigned_filename": filename})

        original_filename = filename
        repaired_filename = self._sanitize_filename(original_filename)

        # Boundary case: empty filename after sanitization
        if not repaired_filename:
            repaired_filename = "unnamed_file.txt"
            self.audit_logger.log("empty_data_boundary", {"assigned_filename": repaired_filename})

        # Deduplication
        file_id = f"{repaired_filename}_{hash(file_content) if file_content else 'nocontent'}"
        if file_id in self.seen_files:
            self.audit_logger.log("deduplication", {"file_id": file_id, "action": "ignored"})
            return {
                "status": "ignored",
                "reason": "duplicate",
                "filename": repaired_filename,
                "engine": None
            }

        self.seen_files.add(file_id)

        # Routing logic based on file extension and naming patterns
        lower_name = repaired_filename.lower()

        engine = "unknown"

        if lower_name.endswith(('.xlsx', '.xls', '.csv')):
            if '提成' in lower_name or 'commission' in lower_name:
                engine = "commission_engine"
            elif '周报' in lower_name or 'weekly' in lower_name:
                engine = "weekly_report_engine"
            else:
                engine = "commission_engine" # Default for excel
        elif lower_name.endswith(('.docx', '.doc')):
            if '标书' in lower_name or 'bid' in lower_name:
                engine = "bid_document_engine"
            else:
                engine = "bid_document_engine" # Default for word
        elif lower_name.endswith('.txt'):
            if '漫剧' in lower_name or 'comic' in lower_name:
                engine = "comic_drama_engine"
            else:
                engine = "comic_drama_engine" # Default for txt

        self.audit_logger.log("routing_decision", {"filename": repaired_filename, "engine": engine})

        # Return clean result for frontend
        return {
            "status": "success",
            "filename": repaired_filename,
            "engine": engine
        }
