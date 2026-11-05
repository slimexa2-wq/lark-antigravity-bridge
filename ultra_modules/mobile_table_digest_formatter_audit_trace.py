import logging
from typing import List, Dict, Any, Tuple, Optional

class AuditTraceLogger:
    def __init__(self) -> None:
        self.traces: List[Dict[str, Any]] = []

    def log(self, step: str, details: Any) -> None:
        self.traces.append({"step": step, "details": details})

def format_mobile_table_digest(raw_data: Optional[Any] = None, attachment_url: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format wide table into 3 lines of core digest, highlight abnormal items, and append an attachment card.
    Silently records audit traces for every transformation step.

    Args:
        raw_data: The wide table data to process (expected list of dicts).
        attachment_url: The URL for downloading the full table.

    Returns:
        tuple: (clean_frontend_string, audit_traces_list)
    """
    audit = AuditTraceLogger()

    # 1. Fallback for missing parameters and dirty data
    if raw_data is None:
        raw_data = []
        audit.log("FALLBACK", "Missing raw_data, defaulted to empty list")

    if attachment_url is None or not isinstance(attachment_url, str) or not attachment_url.strip():
        attachment_url = "https://feishu.cn/default_attachment_download"
        audit.log("FALLBACK", "Missing or invalid attachment_url, used default fallback")

    if not isinstance(raw_data, list):
        audit.log("SELF_HEAL", f"Input data is not a list (type: {type(raw_data).__name__}), wrapping in list or defaulting")
        if isinstance(raw_data, dict):
            raw_data = [raw_data]
        else:
            raw_data = []

    audit.log("START", {"raw_data_length": len(raw_data), "attachment_url": attachment_url})

    # 2. Deduplication and Normalization
    seen_ids = set()
    deduped_data = []

    for i, row in enumerate(raw_data):
        if not isinstance(row, dict):
            audit.log("SELF_HEAL", f"Row {i} is not a dict (type: {type(row).__name__}), skipping")
            continue

        row_id = str(row.get("id", "")).strip()
        if not row_id:
            row_id = f"auto_gen_id_{i}"
            audit.log("SELF_HEAL", f"Row {i} missing ID, auto-generated: {row_id}")

        if row_id in seen_ids:
            audit.log("DEDUPLICATE", f"Removed duplicate row with ID: {row_id}")
            continue

        seen_ids.add(row_id)

        name = str(row.get("name", "")).strip()
        if not name:
            name = f"Unnamed_Item_{row_id}"
            audit.log("SELF_HEAL", f"Row {row_id} missing name, auto-generated: {name}")

        try:
            expected = float(row.get("expected", 0.0))
        except (ValueError, TypeError):
            expected = 0.0
            audit.log("SELF_HEAL", f"Row {row_id} expected value invalid, defaulted to 0.0")

        try:
            actual = float(row.get("actual", 0.0))
        except (ValueError, TypeError):
            actual = 0.0
            audit.log("SELF_HEAL", f"Row {row_id} actual value invalid, defaulted to 0.0")

        deduped_data.append({
            "id": row_id,
            "name": name,
            "expected": expected,
            "actual": actual
        })

    audit.log("PROCESS", f"Deduplicated data length: {len(deduped_data)}")

    # 3. Analyze differences (Diff Highlighter)
    total_items = len(deduped_data)
    abnormal_items = []

    for row in deduped_data:
        diff = row["actual"] - row["expected"]
        if abs(diff) > 0.0001:
            highlight_str = f"{row['name']}(Δ{diff:+.2f})"
            abnormal_items.append(highlight_str)
            audit.log("DIFF_HIGHLIGHT", f"Anomaly detected for {row['name']}: expected {row['expected']}, actual {row['actual']}, diff {diff:+.2f}")

    # 4. Format 3 lines
    line1 = f"📊 核心摘要: 共处理 {total_items} 条数据，发现 {len(abnormal_items)} 项异常。"

    if abnormal_items:
        display_abnormal = abnormal_items[:3]
        suffix = "..." if len(abnormal_items) > 3 else ""
        line2 = f"🚨 异常高亮: {', '.join(display_abnormal)}{suffix}"
    else:
        line2 = "✅ 异常高亮: 无异常，系统运行平稳。"

    line3 = f"📎 完整附件: [点击下载完整宽表]({attachment_url})"

    frontend_result = f"{line1}\n{line2}\n{line3}"
    audit.log("FINISH", "Successfully generated 3-line digest")

    return frontend_result, audit.traces
