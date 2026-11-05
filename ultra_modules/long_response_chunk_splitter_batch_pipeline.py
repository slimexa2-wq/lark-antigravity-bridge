import concurrent.futures
import threading
import uuid
from typing import List, Dict, Any

class ProgressSnapshot:
    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.failed = 0
        self.results = []
        self._lock = threading.Lock()

    def add_result(self, result: Any, is_success: bool = True):
        with self._lock:
            if is_success:
                self.completed += 1
            else:
                self.failed += 1
            self.results.append(result)

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            total_processed = self.completed + self.failed
            return {
                "total": self.total,
                "completed": self.completed,
                "failed": self.failed,
                "progress_percent": round((total_processed) / self.total * 100, 2) if self.total > 0 else 100.0,
                "is_done": total_processed >= self.total,
                "results_count": len(self.results)
            }

    def get_all_results(self) -> List[Any]:
        with self._lock:
            return list(self.results)

class LongResponseChunkSplitterBatchPipeline:
    def __init__(self, max_chunk_size: int = 1500, max_workers: int = 10):
        # Default fallback for parameters
        self.max_chunk_size = max(100, max_chunk_size) if isinstance(max_chunk_size, int) else 1500
        self.max_workers = max(1, max_workers) if isinstance(max_workers, int) else 10

    def split_text(self, text: Any) -> List[str]:
        # Dirty data self-healing
        if text is None:
            return []
        if not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            return []

        chunks = []
        # Split by chapter semantic boundary, e.g., double newline
        paragraphs = text.split('\n\n')
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If a single paragraph is too long, we need to split it
            if len(para) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                # Split the long paragraph by single newlines first, then brute-force if still too long
                sub_lines = para.split('\n')
                for line in sub_lines:
                    line = line.strip()
                    if not line:
                        continue
                    if len(line) > self.max_chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = ""
                        # Brute-force split
                        for i in range(0, len(line), self.max_chunk_size):
                            chunks.append(line[i:i+self.max_chunk_size])
                    else:
                        if len(current_chunk) + len(line) + 1 > self.max_chunk_size:
                            chunks.append(current_chunk.strip())
                            current_chunk = line
                        else:
                            current_chunk = current_chunk + "\n" + line if current_chunk else line
            else:
                if len(current_chunk) + len(para) + 2 > self.max_chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = para
                else:
                    current_chunk = current_chunk + "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def process_record(self, record: Any) -> Dict[str, Any]:
        """
        Processes a single record.
        Record could be a dict with a 'text' field, or just a string.
        """
        record_id = None
        try:
            text = ""
            if isinstance(record, dict):
                record_id = record.get("id", str(uuid.uuid4()))
                text = record.get("text", "")
            else:
                record_id = str(uuid.uuid4())
                text = record

            chunks = self.split_text(text)
            return {
                "id": record_id,
                "status": "success",
                "chunks": chunks,
                "chunk_count": len(chunks)
            }
        except Exception as e:
            return {
                "id": record_id if record_id else str(uuid.uuid4()),
                "status": "error",
                "error": str(e),
                "chunks": [],
                "chunk_count": 0
            }

    def process_batch(self, records: List[Any]) -> ProgressSnapshot:
        """
        Process a batch of 10~1000 records asynchronously.
        Returns a ProgressSnapshot object that can be queried without blocking.
        """
        # Dirty data self-healing: fallback for non-list input
        if not isinstance(records, list):
            records = [records] if records is not None else []

        snapshot = ProgressSnapshot(total=len(records))

        if not records:
            return snapshot

        # Using ThreadPoolExecutor for high throughput batch pipeline
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)

        def task_wrapper(record):
            res = self.process_record(record)
            snapshot.add_result(res, is_success=(res["status"] == "success"))

        for record in records:
            executor.submit(task_wrapper, record)

        # Non-blocking return: zero-block result aggregation
        executor.shutdown(wait=False)
        return snapshot
