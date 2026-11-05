import concurrent.futures
import threading
import uuid
import time
from typing import List, Dict, Any, Optional, Tuple

class ErrorPlainChineseTranslatorBatchPipeline:
    """
    后台堆栈报错自动翻译为大白话原因说明与一键自愈建议卡片生成器
    高吞吐批量流水线与并发加速封装
    """
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        self._progress_snapshots: Dict[str, Dict[str, Any]] = {}
        self._results: Dict[str, List[Any]] = {}
        self._lock = threading.Lock()

    def process_batch(self, error_records: List[Dict[str, Any]], batch_id: Optional[str] = None) -> str:
        """
        批量流式处理报错记录。
        支持单次拖入 10~1000 条记录。
        缺参自动设合理默认值（error_records 缺省默认转为空列表）。
        """
        if not batch_id:
            batch_id = str(uuid.uuid4())

        if error_records is None or not isinstance(error_records, list):
            error_records = []

        total = len(error_records)

        with self._lock:
            self._progress_snapshots[batch_id] = {
                'total': total,
                'completed': 0,
                'failed': 0,
                'status': 'processing'
            }
            self._results[batch_id] = [None] * total

        # Submit all tasks
        futures_to_index = {
            self._executor.submit(self._translate_single, record): i
            for i, record in enumerate(error_records)
        }

        # Handle futures as they complete in a background thread to keep it non-blocking
        def _monitor_progress():
            for future in concurrent.futures.as_completed(futures_to_index):
                index = futures_to_index[future]
                try:
                    result = future.result()
                    with self._lock:
                        self._results[batch_id][index] = result
                        self._progress_snapshots[batch_id]['completed'] += 1
                except Exception as e:
                    # Exception handling - create a default fallback result
                    with self._lock:
                        self._results[batch_id][index] = {
                            "original_error": None,
                            "plain_chinese_explanation": "未知系统异常，请联系管理员。",
                            "auto_healing_suggestion": "重试操作或检查网络连接。",
                            "is_healed": False
                        }
                        self._progress_snapshots[batch_id]['failed'] += 1

            with self._lock:
                self._progress_snapshots[batch_id]['status'] = 'completed'

        # Start the monitoring thread
        monitor_thread = threading.Thread(target=_monitor_progress)
        monitor_thread.daemon = True
        monitor_thread.start()

        return batch_id

    def _translate_single(self, record: Any) -> Dict[str, Any]:
        """
        核心单条处理逻辑
        包含脏数据自愈、缺参默认兜底
        """
        # 脏数据自愈和缺参兜底
        if not isinstance(record, dict):
            record = {'raw_error': str(record) if record else 'Unknown Error'}

        raw_error = record.get('raw_error') or record.get('stack_trace') or record.get('message') or '未提供错误信息'
        error_code = record.get('code', 'UNKNOWN_CODE')

        # 极端边界：大文本截断
        if isinstance(raw_error, str) and len(raw_error) > 5000:
            raw_error = raw_error[:5000] + '...[截断]'

        raw_error_str = str(raw_error).lower()

        # 模拟大白话翻译逻辑和自愈建议
        explanation = "系统内部发生未知错误。"
        suggestion = "建议刷新页面重试。"
        is_healed = False

        if 'timeout' in raw_error_str or '连接超时' in raw_error_str:
            explanation = "网络请求超时了，服务器没来得及响应。"
            suggestion = "请检查网络连接是否正常，或者稍后再试。"
            is_healed = True
        elif 'null pointer' in raw_error_str or 'nonetype' in raw_error_str:
            explanation = "程序在处理数据时遇到了空值，像是在找一个不存在的东西。"
            suggestion = "系统正在自动补充缺失的数据默认值，请重试。"
            is_healed = True
        elif 'permission denied' in raw_error_str or '403' in str(error_code):
            explanation = "您当前没有权限执行此操作。"
            suggestion = "请联系管理员为您开通相应的访问权限。"
        elif 'database' in raw_error_str or 'sql' in raw_error_str:
            explanation = "数据库在存取数据时卡住了。"
            suggestion = "可能是短时间内访问人数过多，请稍等片刻。"

        # 构造卡片结果
        return {
            "original_error": raw_error,
            "error_code": error_code,
            "plain_chinese_explanation": explanation,
            "auto_healing_suggestion": suggestion,
            "is_healed": is_healed
        }

    def get_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        获取进度快照
        """
        with self._lock:
            if batch_id not in self._progress_snapshots:
                return None
            return dict(self._progress_snapshots[batch_id])

    def get_results(self, batch_id: str) -> Optional[List[Any]]:
        """
        获取结果，如果尚未完成，返回部分结果
        """
        with self._lock:
            if batch_id not in self._results:
                return None
            return list(self._results[batch_id])

    def shutdown(self):
        self._executor.shutdown(wait=True)
