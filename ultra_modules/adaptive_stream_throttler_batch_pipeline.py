import time
import threading
import uuid
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

class AdaptiveStreamThrottler:
    """
    自适应节流器
    """
    def __init__(self, min_window_ms: int = 150, max_window_ms: int = 500):
        self.min_window_ms = min_window_ms
        self.max_window_ms = max_window_ms
        self.current_window_ms = min_window_ms

        self.last_flush_time = time.time() # 初始化为当前时间，而不是0.0
        self.sequence_num = 0
        self.buffer = ""
        self.lock = threading.Lock()

    def push_token(self, token: str) -> None:
        with self.lock:
            self.buffer += token

    def try_flush(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            now = time.time()
            elapsed_ms = (now - self.last_flush_time) * 1000

            if elapsed_ms >= self.current_window_ms and self.buffer:
                self.sequence_num += 1
                result = {
                    "sequence": self.sequence_num,
                    "content": self.buffer,
                    "timestamp": now
                }
                self.buffer = ""
                self.last_flush_time = now

                # 自适应调整窗口
                self.current_window_ms = min(self.max_window_ms, self.current_window_ms + 10)

                return result
            return None

    def force_flush(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            if self.buffer:
                now = time.time()
                self.sequence_num += 1
                result = {
                    "sequence": self.sequence_num,
                    "content": self.buffer,
                    "timestamp": now
                }
                self.buffer = ""
                self.last_flush_time = now
                return result
            return None

    def report_429(self):
        """
        接收到429错误时，增加窗口时间
        """
        with self.lock:
            self.current_window_ms = min(self.max_window_ms, self.current_window_ms * 2)

    def report_success(self):
        """
        发送成功时，稍微减小窗口时间
        """
        with self.lock:
            self.current_window_ms = max(self.min_window_ms, self.current_window_ms - 5)

class BatchPipeline:
    """
    高吞吐批量流水线与并发加速封装
    """
    def __init__(self, max_workers: int = 10):
        self.records: List[Dict[str, Any]] = []
        self.processed: List[Dict[str, Any]] = []
        self.max_workers = max_workers

    def ingest(self, records: List[Dict[str, Any]]) -> None:
        """
        单次拖入10~1000条记录
        """
        if not records:
            return

        # 脏数据自愈：填充默认值，确保必填字段存在
        for r in records:
            cleaned = self._clean_record(r)
            self.records.append(cleaned)

    def _clean_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        缺参默认兜底与脏数据自愈
        """
        if not isinstance(record, dict):
            record = {"_raw": record}

        cleaned = dict(record)

        if "id" not in cleaned:
            cleaned["id"] = "auto_" + uuid.uuid4().hex

        if "status" not in cleaned:
            cleaned["status"] = "pending"

        if "value" in cleaned:
            try:
                cleaned["value"] = float(cleaned["value"])
            except (ValueError, TypeError):
                cleaned["value"] = 0.0

        return cleaned

    def process_all(self, processor_func=None) -> Dict[str, Any]:
        """
        批量流式处理与零阻塞结果汇总 (带并发加速)
        """
        results = []
        errors = 0
        successes = 0

        def _worker(record: Dict[str, Any]) -> Dict[str, Any]:
            try:
                if processor_func:
                    res = processor_func(record)
                else:
                    res = dict(record)
                    res["status"] = "processed"
                return {"status": "success", "result": res}
            except Exception as e:
                res = dict(record)
                res["status"] = "error"
                res["error_msg"] = str(e)
                return {"status": "error", "result": res}

        # 保证结果的顺序与输入一致
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_worker, record): i for i, record in enumerate(self.records)}

            # 使用一个按照原顺序初始化的列表存放结果
            ordered_results = [None] * len(self.records)

            for future in as_completed(futures):
                idx = futures[future]
                res_data = future.result()

                if res_data["status"] == "success":
                    successes += 1
                else:
                    errors += 1

                ordered_results[idx] = res_data["result"]

        results = ordered_results

        self.processed.extend(results)
        self.records = []

        return {
            "total": successes + errors,
            "success": successes,
            "error": errors,
            "snapshot": results
        }
