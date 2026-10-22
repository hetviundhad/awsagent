"""
backend/app/services/teach_back.py
Teach-Back Mode Engine: Student Explains Concept in Their Own Words.
Splits explanation into atomic claims, verifies each claim against source document chunks (entailment),
identifies missing essential concept keypoints, generates corrective citations,
records detected misconceptions, and updates BKT parameters.
"""

import os
import re
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from backend.app.services.database import db
from backend.app.rag.self_rag import self_rag_guardrail
from backend.app.learner.bkt import bkt_engine
from backend.app.providers.llm_provider import get_llm_provider
from backend.app.core.config import settings

class TeachBackEvaluator:
    def __init__(self):
        self.llm = get_llm_provider(settings.LLM_PROVIDER, settings.OPENAI_API_KEY)

    def evaluate_teach_back(
        self,
        student_id: str,
        course_id: str,
        concept_id: str,
        explanation_text: str
    ) -> Dict[str, Any]:
        """
        Evaluates a student's teach-back explanation against course ground truth.
        """
        concept = db.get_by_id("concepts", concept_id)
        if not concept:
            # Fallback lookup
            concepts = db.list_all("concepts", lambda c: c.get("id") == concept_id)
            concept = concepts[0] if concepts else {"id": concept_id, "name": "Course Concept"}

        concept_name = concept.get("name", "Course Concept")

        # 1. Fetch supporting knowledge chunks from course documents
        chunks = []
        if concept.get("supporting_chunk_ids"):
            chunks = [db.get_by_id("knowledge_chunks", cid) for cid in concept.get("supporting_chunk_ids") if db.get_by_id("knowledge_chunks", cid)]
            
        if len(chunks) < 2:
            name_words = [w.lower() for w in concept_name.split() if len(w) > 4]
            extra = db.list_all(
                "knowledge_chunks",
                lambda ch: ch.get("course_id") == course_id and (
                    concept_id in str(ch.get("concept_ids", "")) or 
                    concept_name.lower() in ch.get("content", "").lower() or
                    any(w in ch.get("content", "").lower() for w in name_words)
                )
            )
            chunks.extend(extra[:4])

        if not chunks:
            chunks = db.list_all("knowledge_chunks", lambda ch: ch.get("course_id") == course_id)[:4]

        contexts = [ch.get("content", "") for ch in chunks]
        primary_chunk = chunks[0] if chunks else {}
        doc_name = primary_chunk.get("document_name", "Course Material")
        page_num = primary_chunk.get("page_number") or primary_chunk.get("slide_number") or 1

        # 2. Extract Key Points of the concept from chunks
        chunk_text_joined = "\n".join(contexts[:3])
        extract_prompt = f"""Extract 3-4 essential key factual points defining the concept '{concept_name}' based strictly on this text:
{chunk_text_joined[:1500]}

Return JSON list of short strings: ["keypoint 1", "keypoint 2", "keypoint 3"].
"""
        key_points = []
        try:
            res_kp = self.llm.generate_completion([{"role": "user", "content": extract_prompt}], max_tokens=200).get("content", "")
            json_m = re.search(r'\[.*\]', res_kp, re.DOTALL)
            if json_m:
                key_points = json.loads(json_m.group(0))
        except Exception:
            key_points = [
                f"Core definition and operational principle of {concept_name}",
                f"How {concept_name} optimizes distributed performance or fault tolerance",
                f"Interaction of {concept_name} with cluster master and worker nodes"
            ]

        # 3. Split student explanation into sentences/claims
        raw_sentences = [s.strip() for s in re.split(r'[.!?\n]+', explanation_text) if len(s.strip()) > 8]
        if not raw_sentences:
            raw_sentences = [explanation_text.strip()]

        # 4. Verify each claim with Self-RAG entailment check
        correct_claims = []
        wrong_claims = []
        retrieved_eval_chunks = [{"content": ch.get("content", ""), "document_name": ch.get("document_name", doc_name), "page_number": ch.get("page_number") or ch.get("slide_number") or 1} for ch in chunks]

        for sent in raw_sentences:
            prompt = f"""You are an expert academic evaluator. Assess this student statement about '{concept_name}' against the course excerpt.
Course Excerpt:
{chunk_text_joined[:1200]}

Student Claim: "{sent}"

Respond in valid JSON format:
{{
  "is_entailed": true/false,
  "status": "correct" or "unsupported_or_flawed",
  "correcting_fact": "Specific factual correction if flawed, or brief confirmation",
  "feedback": "Why it is correct or what error/misconception it contains"
}}"""
            eval_data = {}
            try:
                res_obj = self.llm.generate_completion([{"role": "user", "content": prompt}], max_tokens=220)
                res_text = res_obj.get("content", "")
                json_m = re.search(r'\{[\s\S]*\}', res_text)
                if json_m:
                    eval_data = json.loads(json_m.group(0))
            except Exception:
                pass


            if not eval_data:
                verifs, _ = self_rag_guardrail.verify_claims(sent, retrieved_eval_chunks)
                supported = any(v.supported for v in verifs)
                eval_data = {
                    "is_entailed": supported,
                    "status": "correct" if supported else "unsupported_or_flawed",
                    "correcting_fact": contexts[0][:140].replace("\n", " ").strip() if contexts else f"Refer to {doc_name}.",
                    "feedback": "Claim verified from context" if supported else f"Contradicts {doc_name}."
                }

            if eval_data.get("is_entailed") is True or eval_data.get("status") == "correct":
                correct_claims.append({
                    "claim": sent,
                    "status": "correct",
                    "verification_confidence": 0.95,
                    "supporting_doc": doc_name,
                    "page_number": page_num
                })
            else:
                wrong_claims.append({
                    "claim": sent,
                    "status": "unsupported_or_flawed",
                    "correcting_citation": {
                        "document_name": doc_name,
                        "page_number": page_num,
                        "corrective_fact": eval_data.get("correcting_fact") or (contexts[0][:140].replace("\n", " ").strip() if contexts else f"Refer to {doc_name}.")
                    },
                    "feedback": eval_data.get("feedback") or f"This claim contradicts or lacks support in {doc_name} (Page/Slide {page_num})."
                })


        # 5. Check missing key points
        missing_key_points = []
        expl_lower = explanation_text.lower()
        for kp in key_points:
            kp_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', kp.lower()))
            overlap = sum(1 for w in kp_words if w in expl_lower)
            if overlap < max(1, len(kp_words) * 0.35):
                missing_key_points.append(kp)

        # 6. Compute Teach-Back Score (0 to 100)
        total_claims = max(len(raw_sentences), 1)
        claim_accuracy = len(correct_claims) / total_claims
        coverage = (len(key_points) - len(missing_key_points)) / max(len(key_points), 1)
        score_pct = round((0.60 * claim_accuracy + 0.40 * coverage) * 100)
        is_passed = score_pct >= 60

        # 7. Update BKT parameters
        m_before = bkt_engine.get_or_create_mastery(student_id, course_id, concept_id)
        p_before = float(m_before.get("mastery_probability", 0.25))

        bkt_res = bkt_engine.update_mastery(
            student_id=student_id,
            course_id=course_id,
            concept_id=concept_id,
            is_correct=is_passed,
            difficulty="Medium",
            source="teach_back"
        )
        p_after = float(bkt_res.get("mastery_probability", bkt_res.get("new_mastery_probability", p_before)))

        # Store misconceptions for student if flawed claims exist
        if wrong_claims:
            for wc in wrong_claims:
                db.insert("misconceptions", {
                    "id": f"misc_{uuid.uuid4().hex[:10]}",
                    "student_id": student_id,
                    "course_id": course_id,
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "flawed_claim": wc["claim"],
                    "correcting_source": doc_name,
                    "page_number": page_num,
                    "created_at": datetime.utcnow().isoformat()
                }, save_disk=True)

        # 8. Feedback Summary
        if is_passed:
            feedback = f"Great explanation! You accurately articulated {len(correct_claims)} core claims of {concept_name} grounded in {doc_name}."
        else:
            feedback = f"You captured some aspects of {concept_name}, but your explanation contains {len(wrong_claims)} unsupported claims and omits key mechanisms. Review {doc_name} (Page {page_num}) and try again."


        return {
            "concept_id": concept_id,
            "concept_name": concept_name,
            "overall_score": score_pct,
            "is_passed": is_passed,
            "correct_claims": correct_claims,
            "wrong_claims": wrong_claims,
            "missing_key_points": missing_key_points,
            "feedback": feedback,
            "bkt_update": {
                "before_probability": round(p_before, 3),
                "after_probability": round(p_after, 3),
                "mastery_gain": round(p_after - p_before, 3)
            }
        }

teach_back_evaluator = TeachBackEvaluator()
