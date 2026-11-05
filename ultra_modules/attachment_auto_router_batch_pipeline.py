import concurrent.futures
from typing import List, Dict, Any, Optional
import time
import logging

class AttachmentAutoRouterBatchPipeline:
    def __init__(self, max_workers: int = 20):
        self.max_workers = max_workers
        self.progress = {
            "total": 0,
            "processed": 0,
            "success": 0,
            "failed": 0,
            "in_progress": False
        }
        # In a real system, you might not use a class-level variable for progress if
        # multiple batches run concurrently on the same instance, but for this simplified
        # pipeline it allows a simple progress snapshot.

    def _determine_engine(self, file_data: Dict[str, Any]) -> str:
        """
        Determine which engine the file should be routed to based on its contents or metadata.
        Support routing to: 'weekly_report', 'commission', 'tender_document', 'comic_drama', or 'unknown'.
        """
        filename = (file_data.get('filename') or '').lower()
        content = (file_data.get('content') or '').lower()
        file_type = (file_data.get('file_type') or '').lower()

        # Self-healing / default handling
        if not filename and not content and not file_type:
             return 'unknown'

        text_to_search = f"{filename} {content} {file_type}"

        if any(keyword in text_to_search for keyword in ['周报', 'weekly']):
            return 'weekly_report'
        elif any(keyword in text_to_search for keyword in ['提成', 'commission']):
            return 'commission'
        elif any(keyword in text_to_search for keyword in ['标书', 'tender']):
            return 'tender_document'
        elif any(keyword in text_to_search for keyword in ['漫剧', 'comic', 'drama']):
            return 'comic_drama'

        return 'unknown'

    def _process_single_file(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single file and route it.
        """
        try:
            # Handle missing params with defaults
            if not isinstance(file_data, dict):
                file_data = {}

            file_id = file_data.get('id', 'unknown_id')

            engine = self._determine_engine(file_data)

            # Simulate some processing time
            # time.sleep(0.01)

            return {
                "id": file_id,
                "status": "success",
                "routed_to": engine,
                "original_data": file_data
            }
        except Exception as e:
            return {
                "id": file_data.get('id', 'unknown_id') if isinstance(file_data, dict) else 'unknown_id',
                "status": "failed",
                "error": str(e)
            }

    def route_batch(self, files: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process a batch of files and route them to different engines.
        """
        if files is None:
            files = []

        self.progress["total"] = len(files)
        self.progress["processed"] = 0
        self.progress["success"] = 0
        self.progress["failed"] = 0
        self.progress["in_progress"] = True

        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {executor.submit(self._process_single_file, f): f for f in files}
            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    result = future.result()
                    results.append(result)
                    self.progress["processed"] += 1
                    if result["status"] == "success":
                        self.progress["success"] += 1
                    else:
                        self.progress["failed"] += 1
                except Exception as exc:
                    self.progress["processed"] += 1
                    self.progress["failed"] += 1
                    results.append({
                        "status": "failed",
                        "error": str(exc)
                    })

        self.progress["in_progress"] = False

        return {
            "summary": {
                "total": self.progress["total"],
                "success": self.progress["success"],
                "failed": self.progress["failed"]
            },
            "results": results
        }

    def get_progress(self) -> Dict[str, Any]:
        """
        Get the current progress snapshot of the pipeline.
        """
        return dict(self.progress)
