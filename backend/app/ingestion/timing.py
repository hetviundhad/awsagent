import time
from typing import Dict, Any, List, Optional
from threading import Lock

class IngestionTimer:
    """
    Precision timing instrumentation for IngestionPipeline.
    Tracks time per stage and per document, LLM call counts, chunk counts, model load time,
    and save_state time.
    """
    def __init__(self):
        self._lock = Lock()
        self.stage_timings: Dict[str, float] = {
            "save_upload": 0.0,
            "text_extraction": 0.0,
            "figure_extraction": 0.0,
            "chunking": 0.0,
            "embedding": 0.0,
            "db_writes": 0.0,
            "curriculum_llm": 0.0,
            "concept_merge_llm": 0.0,
            "chunk_tagging": 0.0,
            "prerequisite_llm": 0.0,
            "course_stats": 0.0,
            "supabase_sync": 0.0,
        }
        self.doc_timings: Dict[str, Dict[str, float]] = {}
        self.llm_calls: Dict[str, int] = {
            "curriculum": 0,
            "concept_merge": 0,
            "chunk_tagging": 0,
            "prerequisite": 0,
            "total": 0,
        }
        self.model_load_time: float = 0.0
        self.save_state_time: float = 0.0
        self.save_state_count: int = 0
        self.chunks_count: int = 0
        self.start_time: float = 0.0
        self.total_time: float = 0.0

    def start(self):
        self.start_time = time.perf_counter()

    def record_stage(self, stage: str, duration: float, doc_name: Optional[str] = None):
        with self._lock:
            self.stage_timings[stage] = self.stage_timings.get(stage, 0.0) + duration
            if doc_name:
                if doc_name not in self.doc_timings:
                    self.doc_timings[doc_name] = {}
                self.doc_timings[doc_name][stage] = self.doc_timings[doc_name].get(stage, 0.0) + duration

    def record_llm_call(self, category: str, duration: float = 0.0):
        with self._lock:
            self.llm_calls[category] = self.llm_calls.get(category, 0) + 1
            self.llm_calls["total"] = self.llm_calls.get("total", 0) + 1
            if duration > 0:
                stage_name = f"{category}_llm"
                if stage_name in self.stage_timings:
                    self.stage_timings[stage_name] += duration

    def finish(self, chunks_count: int = 0):
        with self._lock:
            self.chunks_count = chunks_count
            if self.start_time > 0:
                self.total_time = time.perf_counter() - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_time_seconds": round(self.total_time, 2),
                "model_load_time_seconds": round(self.model_load_time, 3),
                "save_state_time_seconds": round(self.save_state_time, 3),
                "save_state_count": self.save_state_count,
                "chunks_count": self.chunks_count,
                "stage_timings_seconds": {k: round(v, 2) for k, v in self.stage_timings.items()},
                "llm_calls_per_stage": dict(self.llm_calls),
                "document_timings_seconds": {
                    d: {k: round(v, 2) for k, v in stages.items()}
                    for d, stages in self.doc_timings.items()
                }
            }

    def format_table(self) -> str:
        with self._lock:
            lines = []
            lines.append("=" * 80)
            lines.append(f"{'STAGE':<32} | {'TIME (s)':<12} | {'SHARE':<10} | {'LLM CALLS':<10}")
            lines.append("-" * 80)
            total = max(self.total_time, sum(self.stage_timings.values()), 0.001)
            for stage, t in sorted(self.stage_timings.items(), key=lambda x: x[1], reverse=True):
                share = (t / total) * 100
                calls = "-"
                if "curriculum" in stage:
                    calls = str(self.llm_calls.get("curriculum", 0))
                elif "merge" in stage:
                    calls = str(self.llm_calls.get("concept_merge", 0))
                elif "tagging" in stage:
                    calls = str(self.llm_calls.get("chunk_tagging", 0))
                elif "prerequisite" in stage:
                    calls = str(self.llm_calls.get("prerequisite", 0))
                lines.append(f"{stage:<32} | {t:<12.2f} | {share:<9.1f}% | {calls:<10}")
            lines.append("-" * 80)
            lines.append(f"{'TOTAL MEASURED TIME':<32} | {self.total_time:<12.2f} | 100.0%     | {self.llm_calls.get('total', 0)}")
            lines.append(f"Model Load Time: {self.model_load_time:.2f}s | save_state() Time: {self.save_state_time:.2f}s ({self.save_state_count} calls) | Total Chunks: {self.chunks_count}")
            lines.append("=" * 80)
            return "\n".join(lines)
