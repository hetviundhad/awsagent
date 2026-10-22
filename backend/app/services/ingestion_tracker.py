import time
from typing import Dict, Any, Optional
from threading import Lock

class IngestionProgressTracker:
    def __init__(self):
        self._lock = Lock()
        self._progress: Dict[str, Dict[str, Any]] = {}

    def init_task(self, task_id: str, filename: str, total_stages: int = 9):
        with self._lock:
            now = time.time()
            self._progress[task_id] = {
                "task_id": task_id,
                "filename": filename,
                "stage_index": 0,
                "total_stages": total_stages,
                "current_stage": "Initializing multimodal ingestion pipeline",
                "progress_pct": 5,
                "status": "processing",
                "stage_a_ready": False,
                "error": None,
                "created_at": now,
                "updated_at": now,
                "elapsed_seconds": 0.0,
                "eta_seconds": None,
                "documents": {
                    filename: {"status": "queued", "chunks_count": 0, "error": None}
                },
                "details": {}
            }

    def init_multi_doc_task(self, task_id: str, filenames: list, course_id: str):
        with self._lock:
            now = time.time()
            doc_map = {f: {"status": "queued", "chunks_count": 0, "error": None} for f in filenames}
            self._progress[task_id] = {
                "task_id": task_id,
                "course_id": course_id,
                "filename": f"{len(filenames)} Course Documents",
                "stage_index": 1,
                "total_stages": 4,
                "current_stage": f"Queued {len(filenames)} documents for parallel ingestion",
                "progress_pct": 5,
                "status": "processing",
                "stage_a_ready": False,
                "error": None,
                "created_at": now,
                "updated_at": now,
                "elapsed_seconds": 0.0,
                "eta_seconds": 55.0,
                "documents": doc_map,
                "details": {"total_files": len(filenames)}
            }

    def update_doc_status(self, task_id: str, filename: str, status: str, chunks_count: int = 0, error: Optional[str] = None):
        with self._lock:
            if task_id in self._progress:
                now = time.time()
                self._progress[task_id]["updated_at"] = now
                self._progress[task_id]["elapsed_seconds"] = round(now - self._progress[task_id].get("created_at", now), 1)
                docs = self._progress[task_id].setdefault("documents", {})
                if filename not in docs:
                    docs[filename] = {}
                docs[filename]["status"] = status
                if chunks_count > 0:
                    docs[filename]["chunks_count"] = chunks_count
                if error:
                    docs[filename]["error"] = error

    def update_stage(self, task_id: str, stage_index: int, stage_name: str, progress_pct: int, details: Optional[Dict[str, Any]] = None):
        with self._lock:
            if task_id in self._progress:
                now = time.time()
                self._progress[task_id]["stage_index"] = stage_index
                self._progress[task_id]["current_stage"] = stage_name
                self._progress[task_id]["progress_pct"] = progress_pct
                self._progress[task_id]["updated_at"] = now
                self._progress[task_id]["elapsed_seconds"] = round(now - self._progress[task_id].get("created_at", now), 1)
                if details:
                    self._progress[task_id]["details"].update(details)

    def mark_stage_a_ready(self, task_id: str, course_id: str, chunks_count: int, elapsed_seconds: float):
        with self._lock:
            if task_id in self._progress:
                now = time.time()
                self._progress[task_id]["stage_a_ready"] = True
                self._progress[task_id]["status"] = "ready_for_study"
                self._progress[task_id]["current_stage"] = "Stage A Ready: Course is ready to study! Building concept graph in background..."
                self._progress[task_id]["progress_pct"] = 80
                self._progress[task_id]["updated_at"] = now
                self._progress[task_id]["elapsed_seconds"] = round(elapsed_seconds, 1)
                self._progress[task_id]["eta_seconds"] = 15.0
                self._progress[task_id]["details"]["stage_a_chunks"] = chunks_count

    def complete_task(self, task_id: str, result_summary: Dict[str, Any]):
        with self._lock:
            if task_id in self._progress:
                now = time.time()
                self._progress[task_id]["stage_index"] = self._progress[task_id]["total_stages"]
                self._progress[task_id]["current_stage"] = "Ingestion Complete: Full Concept Graph & BKT Ready"
                self._progress[task_id]["progress_pct"] = 100
                self._progress[task_id]["status"] = "completed"
                self._progress[task_id]["stage_a_ready"] = True
                self._progress[task_id]["updated_at"] = now
                self._progress[task_id]["elapsed_seconds"] = round(now - self._progress[task_id].get("created_at", now), 1)
                self._progress[task_id]["eta_seconds"] = 0.0
                self._progress[task_id]["result"] = result_summary

    def fail_task(self, task_id: str, error_message: str):
        with self._lock:
            if task_id in self._progress:
                now = time.time()
                self._progress[task_id]["status"] = "error"
                self._progress[task_id]["error"] = error_message
                self._progress[task_id]["updated_at"] = now
                self._progress[task_id]["elapsed_seconds"] = round(now - self._progress[task_id].get("created_at", now), 1)

    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._progress.get(task_id)
            if not record:
                return None
            out = dict(record)
            now = time.time()
            out["elapsed_seconds"] = round(now - record.get("created_at", now), 1)
            return out

ingestion_tracker = IngestionProgressTracker()
