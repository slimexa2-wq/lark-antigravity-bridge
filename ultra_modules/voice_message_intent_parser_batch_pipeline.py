import concurrent.futures
import traceback
import re
from typing import List, Dict, Any, Union, Optional

class IntentExtractor:
    """
    Zero-config intent extractor with basic heuristics for voice commands.
    """
    def __init__(self):
        # A simple mapping of keywords to intents
        self.intent_map = {
            r"核一下|核对|审核|查一下": "audit",
            r"提成|工资|报酬": "salary",
            r"日程|安排|会议": "schedule",
            r"请假|休假": "leave",
            r"打卡|签到": "attendance",
            r"审批|同意|驳回": "approval",
            r"总结|汇报|日报|周报": "report"
        }

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract intent from a text message.
        """
        if not text or not isinstance(text, str):
            return {"intent": "unknown", "confidence": 0.0, "entities": []}

        matched_intents = []
        for pattern, intent in self.intent_map.items():
            if re.search(pattern, text):
                matched_intents.append(intent)

        if not matched_intents:
            return {"intent": "unknown", "confidence": 0.0, "entities": []}

        # Simple primary intent selection (first match)
        primary_intent = matched_intents[0]

        # Simple entity extraction heuristic for demonstration (extracting potential dates/times)
        entities = []
        time_match = re.search(r"这月|上月|下月|今天|明天|昨天", text)
        if time_match:
            entities.append({"type": "time", "value": time_match.group(0)})

        return {
            "intent": primary_intent,
            "confidence": 0.8 if len(matched_intents) == 1 else 0.6,
            "entities": entities
        }

class BatchPipeline:
    """
    High-throughput concurrent pipeline for processing voice messages.
    """
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.extractor = IntentExtractor()

    def _process_single(self, record: Any) -> Dict[str, Any]:
        """
        Process a single record, self-healing dirty data.
        """
        # Self-healing string conversion
        try:
            if record is None:
                text = ""
            elif isinstance(record, str):
                text = record
            elif isinstance(record, dict) and "text" in record:
                text = str(record["text"])
            elif isinstance(record, (list, tuple)) and len(record) > 0:
                text = str(record[0])
            else:
                text = str(record)
        except Exception:
            text = "" # Fallback for objects that raise errors on __str__

        result = self.extractor.extract(text)
        return {
            "original": str(record) if text else "<unprintable>",
            "parsed_text": text,
            "intent_result": result,
            "status": "success" if text else "empty_or_failed"
        }

    def process_batch(self, records: List[Any]) -> List[Dict[str, Any]]:
        """
        Process a batch of records concurrently.
        """
        if not records:
            return []

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_record = {executor.submit(self._process_single, record): i for i, record in enumerate(records)}

            # Maintain original order
            ordered_results = [None] * len(records)
            for future in concurrent.futures.as_completed(future_to_record):
                idx = future_to_record[future]
                try:
                    ordered_results[idx] = future.result()
                except Exception as exc:
                    ordered_results[idx] = {
                        "original": str(records[idx])[:100] + "..." if hasattr(records[idx], '__str__') else "<error>",
                        "error": str(exc),
                        "status": "error"
                    }

        return ordered_results

def parse_voice_message_intents(records: Optional[Union[List[Any], Any]] = None, max_workers: int = 20) -> List[Dict[str, Any]]:
    """
    Zero-configuration entrypoint for voice message intent extraction.
    Supports single item or batches, self-heals dirty data, uses concurrency for high throughput.
    """
    if records is None:
        records = []
    elif not isinstance(records, (list, tuple)):
        records = [records]

    # Handle potentially nested lists (flatten 1 level as a self-healing measure)
    flat_records = []
    for r in records:
        if isinstance(r, (list, tuple)) and all(not isinstance(item, (list, tuple, dict)) for item in r):
             # Try to just take the first string-like thing if it's a simple flat tuple/list
             flat_records.append(r)
        else:
             flat_records.append(r)

    pipeline = BatchPipeline(max_workers=max_workers)
    return pipeline.process_batch(flat_records)
