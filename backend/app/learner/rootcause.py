"""
backend/app/learner/rootcause.py
"Why Am I Stuck?" Root-Cause Prerequisite Tracing Engine.
When a student struggles or fails a concept or quiz item, traverses the prerequisite DAG,
ranks candidate root-cause concepts by:
- low p_known (mastery probability)
- recent wrong answers
- evidence count
- mastery decay over time
- edge strength / DAG distance
Generates a verified micro-diagnostic (2 questions per candidate), compiles evidence from attempts,
and produces a targeted repair path with source citations and actionable steps.
"""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import math

from backend.app.services.database import db
from backend.app.learner.bkt import bkt_engine
from backend.app.core.config import settings

class RootCauseTracer:
    def __init__(self):
        self.max_depth = getattr(settings, "ROOT_CAUSE_MAX_DEPTH", 4)
        self.top_k = getattr(settings, "ROOT_CAUSE_TOP_K", 3)

    def find_prerequisites_dag(self, course_id: str, concept_id: str, max_depth: int = 4) -> List[Dict[str, Any]]:
        """
        Traverses upstream in the prerequisite DAG to collect all predecessor concepts.
        Returns a list of dicts: {"concept_id": ..., "depth": ..., "concept": ...}
        """
        all_edges = db.list_all("concept_prerequisites", lambda e: e.get("course_id") == course_id)
        # Map: concept_id -> list of prerequisite_ids
        prereq_map: Dict[str, List[str]] = {}
        for edge in all_edges:
            cid = edge.get("concept_id")
            pid = edge.get("prerequisite_id")
            if cid and pid:
                prereq_map.setdefault(cid, []).append(pid)

        visited = set()
        queue = [(concept_id, 0)]
        upstream_candidates = []

        while queue:
            curr_id, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for pid in prereq_map.get(curr_id, []):
                if pid not in visited:
                    visited.add(pid)
                    p_concept = db.get_by_id("concepts", pid)
                    if not p_concept:
                        # Fallback query
                        concepts = db.list_all("concepts", lambda c: c.get("id") == pid)
                        p_concept = concepts[0] if concepts else {"id": pid, "name": f"Concept {pid[:8]}"}

                    upstream_candidates.append({
                        "concept_id": pid,
                        "depth": depth + 1,
                        "concept": p_concept
                    })
                    queue.append((pid, depth + 1))

        return upstream_candidates

    def diagnose_stuck(
        self,
        student_id: str,
        course_id: str,
        target_concept_id: Optional[str] = None,
        assessment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Performs root-cause analysis for a stuck student.
        Identifies failing prerequisite concepts and generates micro-diagnostic repair path.
        """
        # Resolve target concept from assessment if not provided
        if not target_concept_id and assessment_id:
            assessment = db.get_by_id("assessments", assessment_id)
            if assessment:
                target_concept_id = assessment.get("concept_id")
            if not target_concept_id:
                # Find most failed concept in assessment
                attempts = db.list_all("attempts", lambda a: a.get("assessment_id") == assessment_id and not a.get("is_correct", False))
                if attempts:
                    q_id = attempts[0].get("question_id")
                    q = db.get_by_id("questions", q_id) if q_id else None
                    if q:
                        target_concept_id = q.get("concept_id")

        if not target_concept_id:
            # Fallback to the concept with lowest mastery in the course
            all_concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
            if not all_concepts:
                raise ValueError(f"No concepts found for course {course_id}")
            # Check student masteries
            lowest_c = None
            lowest_m = 2.0
            for c in all_concepts:
                m_rec = bkt_engine.get_or_create_mastery(student_id, course_id, c["id"])
                p_known = m_rec.get("mastery_probability", 0.5)
                if p_known < lowest_m:
                    lowest_m = p_known
                    lowest_c = c
            target_concept_id = lowest_c["id"] if lowest_c else all_concepts[0]["id"]

        target_concept = db.get_by_id("concepts", target_concept_id)
        if not target_concept:
            concepts = db.list_all("concepts", lambda c: c.get("id") == target_concept_id)
            target_concept = concepts[0] if concepts else {"id": target_concept_id, "name": "Target Concept"}

        # 1. Collect upstream DAG prerequisites
        upstream = self.find_prerequisites_dag(course_id, target_concept_id, max_depth=self.max_depth)

        # If no prerequisites exist upstream, the target concept itself is foundational
        candidate_pool = upstream if upstream else [{"concept_id": target_concept_id, "depth": 0, "concept": target_concept}]

        # 2. Score and Rank candidates
        scored_candidates = []
        now = datetime.utcnow()

        for item in candidate_pool:
            c_id = item["concept_id"]
            depth = item["depth"]
            c_data = item["concept"]

            m_rec = bkt_engine.get_or_create_mastery(student_id, course_id, c_id)
            p_known = float(m_rec.get("mastery_probability", 0.25))
            wrong_count = int(m_rec.get("incorrect_count", 0))
            correct_count = int(m_rec.get("correct_count", 0))
            attempt_count = wrong_count + correct_count

            # Calculate mastery decay
            last_practiced_str = m_rec.get("last_practiced")
            decay_factor = 0.0
            if last_practiced_str:
                try:
                    last_dt = datetime.fromisoformat(last_practiced_str.replace("Z", ""))
                    days_elapsed = (now - last_dt).total_seconds() / 86400.0
                    decay_factor = min(1.0, days_elapsed / 7.0)
                except Exception:
                    decay_factor = 0.2
            else:
                decay_factor = 0.5

            # Error rate
            error_rate = (wrong_count / max(attempt_count, 1)) if attempt_count > 0 else 0.70

            # DAG proximity score (closer prerequisites have higher priority)
            depth_weight = 1.0 / (depth + 1)

            # Combined Stuck Susceptibility Score (higher = more likely root cause)
            stuck_score = (
                0.40 * (1.0 - p_known) +
                0.25 * error_rate +
                0.15 * decay_factor +
                0.20 * depth_weight
            )

            scored_candidates.append({
                "concept_id": c_id,
                "concept_name": c_data.get("name", "Concept"),
                "concept": c_data,
                "depth": depth,
                "p_known": round(p_known, 3),
                "stuck_score": round(stuck_score, 3),
                "wrong_count": wrong_count,
                "attempt_count": attempt_count,
                "decay_factor": round(decay_factor, 2)
            })

        scored_candidates.sort(key=lambda x: x["stuck_score"], reverse=True)
        top_candidates = scored_candidates[:self.top_k]

        # 3. Compile Evidence & Supporting Chunks
        evidence = []
        for cand in top_candidates:
            c_id = cand["concept_id"]
            c_name = cand["concept_name"]
            
            # Find supporting chunk from database for source citation
            chunks = db.list_all("knowledge_chunks", lambda ch: ch.get("course_id") == course_id and (c_id in ch.get("concept_ids", []) or c_name.lower() in ch.get("content", "").lower()))
            if not chunks:
                chunks = db.list_all("knowledge_chunks", lambda ch: ch.get("course_id") == course_id)
            
            top_chunk = chunks[0] if chunks else {}
            doc_name = top_chunk.get("document_name", "Course Document")
            page_num = top_chunk.get("page_number") or top_chunk.get("slide_number") or 1
            snippet = top_chunk.get("content", "")[:180].replace("\n", " ").strip()

            evidence.append({
                "concept_id": c_id,
                "concept_name": c_name,
                "p_known": cand["p_known"],
                "incorrect_attempts": cand["wrong_count"],
                "total_attempts": cand["attempt_count"],
                "stuck_score": cand["stuck_score"],
                "source_document": doc_name,
                "source_page": page_num,
                "source_snippet": snippet
            })

        # 4. Build Repair Path with Micro-Diagnostic Questions
        # Order concepts topologically (deepest prerequisite first, leading to target concept)
        path_concepts = list(top_candidates)
        path_concepts.sort(key=lambda x: x["depth"], reverse=True)
        # Ensure target concept is at the end of the path if not already
        if not any(pc["concept_id"] == target_concept_id for pc in path_concepts):
            path_concepts.append({
                "concept_id": target_concept_id,
                "concept_name": target_concept.get("name", "Target Concept"),
                "concept": target_concept,
                "depth": 0,
                "p_known": round(bkt_engine.get_or_create_mastery(student_id, course_id, target_concept_id).get("mastery_probability", 0.25), 3)
            })

        repair_path = []
        for step_idx, step_c in enumerate(path_concepts, 1):
            c_id = step_c["concept_id"]
            c_name = step_c["concept_name"]

            # Fetch 2 verified questions for this concept from question bank
            candidate_qs = db.list_all("questions", lambda q: q.get("course_id") == course_id and (q.get("concept_id") == c_id or c_id in q.get("concept_ids", [])))
            if not candidate_qs or len(candidate_qs) < 2:
                # Fallback to general questions
                candidate_qs = db.list_all("questions", lambda q: q.get("course_id") == course_id)[:4]

            micro_qs = candidate_qs[:2]
            
            # Find citation
            chunks = db.list_all("knowledge_chunks", lambda ch: ch.get("course_id") == course_id and (c_id in ch.get("concept_ids", []) or c_name.lower() in ch.get("content", "").lower()))
            chunk = chunks[0] if chunks else {}
            doc_name = chunk.get("document_name", "Course Document")
            page_num = chunk.get("page_number") or chunk.get("slide_number") or 1

            repair_path.append({
                "step": step_idx,
                "concept_id": c_id,
                "concept_name": c_name,
                "source_document": doc_name,
                "source_page": page_num,
                "action": f"Read {doc_name} (Page/Slide {page_num}), complete 2 verified micro-diagnostic questions to bridge understanding, then proceed.",
                "micro_diagnostic_questions": [
                    {
                        "question_id": q.get("id"),
                        "question_text": q.get("question_text"),
                        "options": q.get("options", []),
                        "correct_answer": q.get("correct_answer"),
                        "explanation": q.get("explanation")
                    }
                    for q in micro_qs
                ]
            })

        diagnosis_record = {
            "id": f"diag_{uuid.uuid4().hex[:12]}",
            "student_id": student_id,
            "course_id": course_id,
            "target_concept_id": target_concept_id,
            "target_concept_name": target_concept.get("name", "Stuck Concept"),
            "root_causes": top_candidates,
            "evidence": evidence,
            "repair_path": repair_path,
            "created_at": datetime.utcnow().isoformat()
        }

        # Cache in memory or return directly
        return diagnosis_record

root_cause_tracer = RootCauseTracer()
