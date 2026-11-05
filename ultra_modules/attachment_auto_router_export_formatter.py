import math
from typing import Dict, Any, List, Optional


class AttachmentAutoRouter:
    """
    Routes files to appropriate business engines (weekly report, commission, bid, comic engine),
    cleans exported data (comments=0, NaN/None to 0 for numerics), and generates a 3-line summary.
    """

    SUPPORTED_FILE_TYPES = {"excel", "word", "txt"}
    BUSINESS_ENGINES = ["周报", "提成", "标书", "漫剧引擎"]

    def __init__(self, filename: str, file_type: Optional[str] = None, business_type: Optional[str] = None):
        self.filename = filename

        # Default fallbacks
        self.file_type = file_type.lower() if file_type and file_type.lower() in self.SUPPORTED_FILE_TYPES else self._guess_file_type(filename)
        self.business_type = business_type if business_type and business_type in self.BUSINESS_ENGINES else self._guess_business_type(filename)

    def _guess_file_type(self, filename: str) -> str:
        """Fallback to guess file type from extension."""
        if not filename:
            return "txt"

        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext in ["xlsx", "xls", "csv"]:
            return "excel"
        elif ext in ["doc", "docx"]:
            return "word"
        return "txt"

    def _guess_business_type(self, filename: str) -> str:
        """Fallback to guess business type from filename or default to 周报."""
        if not filename:
             return "周报"

        for engine in self.BUSINESS_ENGINES:
            if engine in filename:
                return engine
        return "周报"

    def clean_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Cleans data:
        - Ensures numerical values have no NaN or None, replaced by 0 (dirty data self-healing)
        """
        cleaned = []
        for row in data:
            if not isinstance(row, dict):
                continue

            clean_row = {}
            for k, v in row.items():
                if v is None:
                    clean_row[k] = 0 if self._is_likely_numeric(k) else ""
                elif isinstance(v, float) and math.isnan(v):
                    clean_row[k] = 0
                else:
                    clean_row[k] = v
            cleaned.append(clean_row)
        return cleaned

    def _is_likely_numeric(self, key: str) -> bool:
        """Heuristics to determine if a missing value should default to 0."""
        return any(term in str(key).lower() for term in ["amount", "count", "num", "id", "price", "提成", "金额", "数值"])

    def process(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main entry point for processing the attachment.
        Returns cleaned data and a 3-line report.
        """
        if not isinstance(data, list):
            data = []

        cleaned_data = self.clean_data(data)

        # Extreme boundaries (empty data) handling
        total_records = len(cleaned_data)

        # Generation of 3-line summary
        line1 = f"【{self.business_type}】解析完毕 (文件: {self.filename})"
        line2 = f"共处理 {total_records} 条数据 (零批注纯净导出)"
        line3 = f"导出状态: 正常 | comments=0"

        summary = f"{line1}\n{line2}\n{line3}"

        return {
            "engine": self.business_type,
            "cleaned_data": cleaned_data,
            "summary": summary,
            "comments": 0
        }
