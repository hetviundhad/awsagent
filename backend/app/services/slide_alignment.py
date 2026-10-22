import os
import uuid
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from backend.app.services.database import db
from backend.app.providers.embedding_provider import get_embedding_provider
from backend.app.core.config import settings

class SlideAlignmentService:
    def __init__(self):
        self.embedding_provider = get_embedding_provider(settings.EMBEDDING_PROVIDER, settings.OPENAI_API_KEY)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        va = np.array(a, dtype=np.float32)
        vb = np.array(b, dtype=np.float32)
        norm_a = np.linalg.norm(va)
        norm_b = np.linalg.norm(vb)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(va, vb) / (norm_a * norm_b))

    def align_course_lectures_to_slides(
        self,
        course_id: str,
        ordering_penalty: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Aligns video transcript chunks to presentation slide chunks using embedding similarity
        constrained by sequential lecture progression (Dynamic Programming with forward bias).
        """
        all_chunks = db.list_all("knowledge_chunks", lambda c: c.get("course_id") == course_id)

        # 1. Collect video transcript chunks
        video_chunks = [
            c for c in all_chunks 
            if c.get("timestamp_start") is not None or c.get("source_type") == "video"
        ]
        video_chunks.sort(key=lambda c: float(c.get("timestamp_start", 0) or 0))

        # 2. Collect slide chunks
        slide_chunks = [
            c for c in all_chunks
            if c.get("slide_number") is not None or "pptx" in str(c.get("document_name", "")).lower()
        ]
        slide_chunks.sort(key=lambda c: (str(c.get("document_name")), int(c.get("slide_number", 0) or 0)))

        if not video_chunks or not slide_chunks:
            return []

        # 3. Compute embeddings if not cached
        video_embs = []
        for vc in video_chunks:
            emb = vc.get("embedding")
            if not emb or len(emb) == 0:
                emb = self.embedding_provider.embed_text(vc.get("content", ""))
                vc["embedding"] = emb
            video_embs.append(emb)

        slide_embs = []
        for sc in slide_chunks:
            emb = sc.get("embedding")
            if not emb or len(emb) == 0:
                emb = self.embedding_provider.embed_text(sc.get("content", ""))
                sc["embedding"] = emb
            slide_embs.append(emb)

        n_v = len(video_chunks)
        n_s = len(slide_chunks)

        # 4. Construct Cost/Similarity Matrix S[i, j]
        sim_matrix = np.zeros((n_v, n_s), dtype=np.float32)
        for i in range(n_v):
            for j in range(n_s):
                sim_matrix[i, j] = self._cosine_similarity(video_embs[i], slide_embs[j])

        # 5. Dynamic Programming with Monotonic Progression Bias
        # DP[i, j]: maximum alignment score aligning first i video windows to end at slide j
        dp = np.full((n_v, n_s), -1e9, dtype=np.float32)
        parent = np.zeros((n_v, n_s), dtype=np.int32)

        for j in range(n_s):
            dp[0, j] = sim_matrix[0, j]
            parent[0, j] = -1

        for i in range(1, n_v):
            for j in range(n_s):
                best_score = -1e9
                best_k = 0
                for k in range(n_s):
                    # Penalty for backward jump in slides
                    trans_penalty = 0.0
                    if j < k:
                        trans_penalty = ordering_penalty * (k - j) # Backward penalty
                    elif j > k + 2:
                        trans_penalty = 0.05 * (j - k) # Skipping slides forward slightly penalized
                    
                    score = dp[i - 1, k] + sim_matrix[i, j] - trans_penalty
                    if score > best_score:
                        best_score = score
                        best_k = k
                dp[i, j] = best_score
                parent[i, j] = best_k

        # 6. Backtrack optimal alignment path
        aligned_pairs = []
        curr_slide_idx = int(np.argmax(dp[n_v - 1]))
        
        path = [(n_v - 1, curr_slide_idx)]
        for i in range(n_v - 1, 0, -1):
            curr_slide_idx = parent[i, curr_slide_idx]
            path.append((i - 1, curr_slide_idx))
        path.reverse()

        alignments = []
        for v_idx, s_idx in path:
            vc = video_chunks[v_idx]
            sc = slide_chunks[s_idx]
            raw_sim = float(sim_matrix[v_idx, s_idx])

            record = {
                "id": f"align_{uuid.uuid4().hex[:10]}",
                "course_id": course_id,
                "video_chunk_id": vc["id"],
                "slide_chunk_id": sc["id"],
                "video_title": vc.get("document_name") or "Lecture Video",
                "timestamp_start": vc.get("timestamp_start", 0),
                "timestamp_end": vc.get("timestamp_end", 0),
                "timestamp_label": self._format_timestamp(vc.get("timestamp_start", 0)),
                "slide_document": sc.get("document_name") or "Presentation",
                "slide_number": sc.get("slide_number", 1),
                "similarity_score": round(raw_sim, 4),
                "transcript_snippet": vc.get("content", "")[:120].strip(),
                "slide_snippet": sc.get("content", "")[:120].strip(),
                "created_at": datetime.utcnow().isoformat()
            }
            alignments.append(record)
            db.insert("slide_alignments", record, save_disk=False)

        db.flush()
        return alignments

    def _format_timestamp(self, sec: Any) -> str:
        try:
            s = int(float(sec))
            m = s // 60
            rem_s = s % 60
            return f"{m:02d}:{rem_s:02d}"
        except Exception:
            return "00:00"

    def get_slide_for_timestamp(self, course_id: str, timestamp_sec: float) -> Optional[Dict[str, Any]]:
        alignments = db.list_all("slide_alignments", lambda a: a.get("course_id") == course_id)
        if not alignments:
            alignments = self.align_course_lectures_to_slides(course_id)
        if not alignments:
            return None

        # Find closest timestamp window
        best = None
        min_diff = 1e9
        for a in alignments:
            t_start = float(a.get("timestamp_start", 0) or 0)
            t_end = float(a.get("timestamp_end", t_start + 30) or t_start + 30)
            if t_start <= timestamp_sec <= t_end:
                return a
            diff = abs(t_start - timestamp_sec)
            if diff < min_diff:
                min_diff = diff
                best = a
        return best

    def get_moments_for_slide(self, course_id: str, slide_doc: str, slide_num: int) -> List[Dict[str, Any]]:
        alignments = db.list_all("slide_alignments", lambda a: a.get("course_id") == course_id)
        if not alignments:
            alignments = self.align_course_lectures_to_slides(course_id)
        matched = [
            a for a in alignments 
            if a.get("slide_document") == slide_doc and int(a.get("slide_number", 0)) == int(slide_num)
        ]
        return matched

    def evaluate_alignment_accuracy(self, labeled_pairs: List[Tuple[float, str, int]]) -> Dict[str, Any]:
        """
        Calculates Top-1 and within-1-slide tolerance accuracy against ground-truth pairs.
        labeled_pairs: [(timestamp_sec, expected_slide_doc, expected_slide_num)]
        """
        if not labeled_pairs:
            return {"total_evaluated": 0, "exact_accuracy": 0.0, "tolerance_accuracy": 0.0}

        exact_correct = 0
        tolerance_correct = 0

        for t_sec, exp_doc, exp_num in labeled_pairs:
            pred = self.get_slide_for_timestamp("a091a4aa-a333-4a0c-85ec-9af9ad8505bd", t_sec)
            if not pred:
                continue
            pred_doc = pred.get("slide_document", "")
            pred_num = int(pred.get("slide_number", 0) or 0)

            same_doc = (exp_doc.lower() in pred_doc.lower() or pred_doc.lower() in exp_doc.lower())
            if same_doc and pred_num == exp_num:
                exact_correct += 1
                tolerance_correct += 1
            elif same_doc and abs(pred_num - exp_num) <= 1:
                tolerance_correct += 1

        n = len(labeled_pairs)
        return {
            "total_evaluated": n,
            "exact_accuracy": round(exact_correct / n, 4),
            "tolerance_accuracy": round(tolerance_correct / n, 4),
            "exact_percentage": f"{round(exact_correct / n * 100, 1)}%",
            "tolerance_percentage": f"{round(tolerance_correct / n * 100, 1)}%"
        }

slide_alignment_service = SlideAlignmentService()
