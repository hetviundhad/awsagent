import os
import re
import json
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Response, Request, Depends, status
from fastapi.responses import StreamingResponse

from backend.app.models.schemas import (
    Course, CourseCreate, TutorQueryRequest, TutorQueryResponse,
    AssessmentGenerateRequest, AssessmentSubmitRequest, EvaluationRunRequest,
    ExplainUrlRequest, AddNoteRequest, YouTubeIngestRequest
)
from backend.app.services.database import db
from backend.app.services.storage import storage
from backend.app.services.web_extractor import web_extractor
from backend.app.providers.llm_provider import get_llm_provider
from backend.app.providers.vision_provider import get_vision_provider
from backend.app.ingestion.pipeline import ingestion_pipeline
from backend.app.rag.engine import rag_engine
from backend.app.assessment.generator import assessment_engine
from backend.app.learner.bkt import bkt_engine
from backend.app.evaluation.ragas_eval import evaluation_suite
from backend.app.services.sample_course import load_sample_course_for_user
from backend.app.core.config import settings, is_test_environment
from backend.app.core.errors import AIServiceUnavailableError
from backend.app.evaluation.simulator import synthetic_simulator
from backend.app.api.dependencies import (
    get_student_id_from_request,
    get_owner_id_from_request,
    ensure_course_access,
    DEMO_STUDENT_IDS
)

router = APIRouter()

# --- Courses ---
@router.get("/courses")
def get_courses(request: Request):
    try:
        student_id = get_student_id_from_request(request)
    except Exception:
        student_id = "default_student"
    user_courses = db.list_all(
        "courses",
        lambda c: (
            not c.get("id", "").startswith("test_")
            and not c.get("id", "").startswith("test-")
            and not c.get("id", "").startswith("crs_isolated_")
            and (
                c.get("owner_id") == student_id
                or student_id in DEMO_STUDENT_IDS
                or c.get("owner_id") in DEMO_STUDENT_IDS
                or c.get("owner_id") in ("default_student", "demo", "demo_student", None, "")
                or (c.get("is_public") is True and not str(student_id).startswith("user_isolation_"))
            )
        )
    )
    enriched = []
    for c in user_courses:
        c_id = c["id"]
        c_dict = dict(c)
        c_docs = db.list_all("documents", lambda d: d.get("course_id") == c_id)
        c_chunks = db.list_all("knowledge_chunks", lambda ch: ch.get("course_id") == c_id)
        c_concepts = db.list_all("concepts", lambda co: co.get("course_id") == c_id)
        c_topics = db.list_all("topics", lambda t: t.get("course_id") == c_id)
        c_dict["document_count"] = len(c_docs)
        c_dict["chunk_count"] = len(c_chunks)
        c_dict["concept_count"] = len(c_concepts)
        c_dict["topic_count"] = len(c_topics)
        enriched.append(c_dict)

    # Deduplicate courses with identical names by keeping the one with richest concepts/documents
    deduped = {}
    for c in enriched:
        name_key = c.get("name", "").strip().lower()
        if name_key not in deduped:
            deduped[name_key] = c
        else:
            prev = deduped[name_key]
            if (c.get("concept_count", 0), c.get("document_count", 0)) > (prev.get("concept_count", 0), prev.get("document_count", 0)):
                deduped[name_key] = c
    return list(deduped.values())

def generate_course_curriculum(course_id: str, course_name: str, subject: str):
    # Synthesizes academic syllabus topics and concepts for course and subject
    groq_key = settings.GROQ_API_KEY
    topics_list = []
    if groq_key and groq_key.strip():
        import httpx
        prompt = (
            f"You are a university academic dean. Generate 4 core syllabus topics with 2-3 essential concepts each "
            f"for a course titled '{course_name}' in the subject/discipline '{subject}'.\n"
            "Return strictly valid JSON array of objects: "
            "[{\"topic_name\": \"...\", \"description\": \"...\", \"concepts\": [\"Concept 1\", \"Concept 2\"]}]"
        )
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                        "max_tokens": 1000
                    }
                )
                if res.status_code == 200:
                    raw = res.json()["choices"][0]["message"].get("content", "")
                    m = re.search(r'\[[\s\S]*\]', raw)
                    if m:
                        topics_list = json.loads(m.group(0))
        except Exception as e:
            print(f"[CurriculumGen] AI synthesis note: {e}")

    # No silent fake template fallback: fail if AI service did not produce curriculum
    if not topics_list:
        raise AIServiceUnavailableError(f"AI curriculum synthesis failed for course '{course_name}'. AI service is unavailable or returned an invalid structure.")

    created_topics = []
    total_concepts = 0
    for idx, t in enumerate(topics_list, start=1):
        t_id = f"top_{course_id}_{idx}"
        topic_obj = {
            "id": t_id,
            "course_id": course_id,
            "name": t.get("topic_name", f"Topic {idx}"),
            "description": t.get("description", ""),
            "created_at": datetime.utcnow().isoformat(),
            "concepts": []
        }
        db.insert("topics", {k: v for k, v in topic_obj.items() if k != "concepts"})

        for c_name in t.get("concepts", []):
            c_id = f"con_{uuid.uuid4().hex[:8]}"
            concept_obj = {
                "id": c_id,
                "course_id": course_id,
                "topic_id": t_id,
                "name": c_name,
                "description": f"Key concept covering {c_name} in {t.get('topic_name')}",
                "created_at": datetime.utcnow().isoformat()
            }
            db.insert("concepts", concept_obj)
            topic_obj["concepts"].append(concept_obj)
            total_concepts += 1

        created_topics.append(topic_obj)

    db.update("courses", course_id, {
        "topic_count": len(created_topics),
        "concept_count": total_concepts
    })
    return created_topics

@router.post("/courses")
def create_course(payload: CourseCreate, request: Request):
    owner_id = get_owner_id_from_request(request)
    course_id = str(uuid.uuid4())
    course = {
        "id": course_id,
        "owner_id": owner_id,
        "name": payload.name,
        "description": payload.description or f"Course knowledge base covering {payload.name}.",
        "subject": payload.subject or "General Subject",
        "semester": payload.semester,
        "exam_date": payload.exam_date or None,
        "created_at": datetime.utcnow().isoformat(),
        "units": [],
        "document_count": 0,
        "topic_count": 0,
        "concept_count": 0,
        "overall_mastery": 0.0
    }
    db.insert("courses", course)
    return course

@router.post("/courses/{course_id}/generate-curriculum")
def generate_curriculum_endpoint(course_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, student_id)
    topics = generate_course_curriculum(course_id, course.get("name", "Course"), course.get("subject", "General Subject"))
    return {"message": "Curriculum generated successfully", "topics": topics}

@router.get("/courses/{course_id}/concepts")
def get_course_concepts(course_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, student_id)
    concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
    return concepts

@router.delete("/courses/{course_id}")
def delete_course(course_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    tables_to_clean = [
        "course_units", "documents", "topics", "concepts",
        "concept_prerequisites", "visual_elements", "knowledge_chunks",
        "learner_mastery", "study_plans", "revision_materials", "assessments",
        "questions"
    ]
    for tbl in tables_to_clean:
        records = db.list_all(tbl, lambda r: r.get("course_id") == course_id)
        for r in records:
            db.delete(tbl, r["id"])

    db.delete("courses", course_id)
    return {"message": "Course deleted successfully", "course_id": course_id}

@router.get("/courses/{course_id}")
def get_course_detail(course_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, student_id)
    
    docs = db.list_all("documents", lambda d: d.get("course_id") == course_id)
    topics = db.list_all("topics", lambda t: t.get("course_id") == course_id)
    concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
    units = db.list_all("course_units", lambda u: u.get("course_id") == course_id)
    if not units and docs:
        for idx, doc in enumerate(docs, start=1):
            clean_title = os.path.splitext(doc.get("filename", f"Unit {idx}"))[0].replace("_", " ").title()
            db.insert("course_units", {
                "id": str(uuid.uuid4()),
                "course_id": course_id,
                "unit_number": idx,
                "title": clean_title,
                "description": f"Curriculum module extracted from {doc.get('filename')}"
            })
        units = db.list_all("course_units", lambda u: u.get("course_id") == course_id)
    visuals = db.list_all("visual_elements", lambda v: v.get("course_id") == course_id)

    # Calculate overall mastery
    mastery_profile = bkt_engine.get_learner_profile(student_id, course_id)

    course_chunks = db.list_all("knowledge_chunks", lambda c: c.get("course_id") == course_id)
    enriched_docs = []
    for d in docs:
        d_chunks = [c for c in course_chunks if c.get("document_id") == d["id"]]
        d_cids = set()
        for chk in d_chunks:
            d_cids.update(chk.get("concept_ids", []))
        d_dict = dict(d)
        d_dict["chunk_count"] = len(d_chunks)
        d_dict["concept_count"] = len(d_cids)
        d_dict["status"] = d.get("status", "processed")
        d_dict["last_error"] = d.get("error_message")
        enriched_docs.append(d_dict)

    return {
        "course": course,
        "units": units,
        "documents": enriched_docs,
        "topics": topics,
        "concepts": concepts,
        "visual_elements_count": len(visuals),
        "overall_mastery": mastery_profile["overall_mastery_pct"]
    }

@router.get("/courses/{course_id}/suggested-questions")
def get_course_suggested_questions(course_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, student_id)

    concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
    c_name = course.get("name", "this course")
    
    if not concepts:
        return {
            "course_id": course_id,
            "course_name": c_name,
            "questions": [
                f"What are the foundational principles in {c_name}?",
                f"Can you explain the syllabus structure of {c_name}?",
                f"Give me a high-level overview of the uploaded materials.",
                f"What should I study first in {c_name}?"
            ]
        }
    
    # Generate 3-4 questions dynamically from real concepts in the database
    c_names = [c.get("name") for c in concepts if c.get("name")]
    questions = []
    if len(c_names) >= 1:
        questions.append(f"Can you explain {c_names[0]} in simple terms with an example?")
    if len(c_names) >= 2:
        questions.append(f"How does {c_names[1]} work in practice?")
    if len(c_names) >= 3:
        questions.append(f"What is the key difference between {c_names[0]} and {c_names[2]}?")
    if len(c_names) >= 4:
        questions.append(f"Quiz me on {c_names[3]} from our lecture notes.")
    elif len(c_names) >= 1:
        questions.append(f"Quiz me on {c_names[0]} with a practical problem.")
        
    return {
        "course_id": course_id,
        "course_name": c_name,
        "questions": questions[:4],
        "suggested_questions": questions[:4]
    }

@router.get("/courses/{course_id}/debug")
def get_course_debug(course_id: str, request: Request):
    """
    Debug inspection endpoint: documents, chunk count, concept count, embedding dim,
    sample chunks, and last ingestion error.
    """
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, student_id)
    
    docs = db.list_all("documents", lambda d: d.get("course_id") == course_id)
    chunks = db.list_all("knowledge_chunks", lambda c: c.get("course_id") == course_id)
    concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
    
    embedding_dim = 0
    sample_chunks = []
    for chk in chunks[:5]:
        emb = chk.get("embedding") or []
        if emb and not embedding_dim:
            embedding_dim = len(emb)
        sample_chunks.append({
            "id": chk.get("id"),
            "document_name": chk.get("document_name"),
            "page_number": chk.get("page_number"),
            "slide_number": chk.get("slide_number"),
            "content_preview": (chk.get("content") or "")[:200],
            "concept_ids": chk.get("concept_ids", []),
            "has_embedding": bool(emb)
        })
    if not embedding_dim and chunks:
        first_emb = chunks[0].get("embedding") or []
        embedding_dim = len(first_emb) if first_emb else settings.EMBEDDING_DIMENSION
        
    last_ingestion_error = None
    failed_docs = [d for d in docs if d.get("status") == "error" or d.get("error")]
    if failed_docs:
        last_ingestion_error = failed_docs[-1].get("error") or "Document ingestion failed"

    timing_metrics = (course.get("timing_metrics") if course else None) or (
        getattr(ingestion_pipeline, "timer", None).to_dict() if getattr(ingestion_pipeline, "timer", None) else None
    )

    return {
        "course_id": course_id,
        "course_name": course.get("name") if course else None,
        "documents": [
            {
                "id": d.get("id"),
                "filename": d.get("filename"),
                "status": d.get("status"),
                "file_type": d.get("file_type"),
                "file_size": d.get("file_size"),
                "file_hash": d.get("file_hash"),
                "created_at": d.get("created_at")
            }
            for d in docs
        ],
        "chunk_count": len(chunks),
        "concept_count": len(concepts),
        "embedding_dim": embedding_dim,
        "sample_chunks": sample_chunks,
        "last_ingestion_error": last_ingestion_error,
        "timing_metrics": timing_metrics
    }



# --- Concept Map (Dependency Graph) ---
@router.get("/course/{course_id}/concept-map")
@router.get("/courses/{course_id}/concept-map")
def get_course_concept_map(course_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    ensure_course_access(db.get_by_id("courses", course_id), student_id)
    concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
    prereqs = db.list_all("concept_prerequisites")
    prereqs_map: Dict[str, List[str]] = {}
    for p in prereqs:
        cid = p.get("concept_id")
        pid = p.get("prerequisite_id")
        if cid and pid:
            prereqs_map.setdefault(cid, []).append(pid)
    
    # Calculate mastery colors for nodes and evaluate locked states
    mastery_records = db.list_all("learner_mastery", lambda m: m.get("course_id") == course_id and m.get("student_id") == student_id)
    m_map = {m["concept_id"]: m for m in mastery_records}

    chunks_in_course = db.list_all("knowledge_chunks", lambda k: k.get("course_id") == course_id)
    chunks_by_cid: Dict[str, List[Any]] = {}
    for chk in chunks_in_course:
        for cid in chk.get("concept_ids", []):
            chunks_by_cid.setdefault(cid, []).append(chk)
        c_direct = chk.get("concept_id")
        if c_direct:
            chunks_by_cid.setdefault(c_direct, []).append(chk)

    nodes = []
    for c in concepts:
        m_rec = m_map.get(c["id"]) or {}
        p_val = m_rec.get("mastery_probability", 0.20) if isinstance(m_rec, dict) else 0.20
        attempts = m_rec.get("attempt_count", 0) if isinstance(m_rec, dict) else 0
        lock_info = bkt_engine.check_concept_locked(student_id, course_id, c["id"], mastery_map=m_map, prereqs_map=prereqs_map)
        is_locked = lock_info["is_locked"]

        if is_locked:
            status = "Locked"
        elif p_val >= 0.75:
            status = "Mastered"
        elif p_val >= 0.45:
            status = "Developing"
        elif attempts == 0:
            status = "Not started"
        else:
            status = "Needs Attention"

        # Find matching source units for this concept efficiently
        source_units = []
        matching_chunks = chunks_by_cid.get(c["id"], [])
        if not matching_chunks:
            c_name_lower = c["name"].lower()
            matching_chunks = [chk for chk in chunks_in_course[:20] if c_name_lower in chk.get("content", "").lower()]

        for s_idx, chk in enumerate(matching_chunks[:6]):
            source_units.append({
                "citation_index": s_idx + 1,
                "chunk_id": chk.get("id"),
                "document_name": chk.get("document_name", "Course Document"),
                "source_type": chk.get("source_type", "document"),
                "page_number": chk.get("page_number"),
                "slide_number": chk.get("slide_number"),
                "timestamp_start": chk.get("timestamp_start"),
                "timestamp_end": chk.get("timestamp_end"),
                "snippet": chk.get("content_summary") or (chk.get("content", "")[:140] + "..."),
                "keyframe_path": chk.get("keyframe_path"),
                "bbox": chk.get("bbox")
            })

        # Gather rich prerequisite details
        prereq_details = []
        for p_id in c.get("prerequisites", []):
            pr_c = db.get_by_id("concepts", p_id)
            if pr_c:
                p_m = m_map.get(p_id) or {}
                p_prob = p_m.get("mastery_probability", 0.20) if isinstance(p_m, dict) else 0.20
                prereq_details.append({
                    "id": p_id,
                    "name": pr_c.get("name"),
                    "mastery": round(p_prob * 100, 1),
                    "is_met": p_prob >= 0.60
                })

        nodes.append({
            "id": c["id"],
            "name": c["name"],
            "topic_id": c.get("topic_id"),
            "difficulty": c.get("difficulty", "Medium"),
            "mastery": round(p_val * 100, 1),
            "status": status,
            "is_locked": is_locked,
            "locked_reason": lock_info["reason"],
            "blocking_prerequisite": lock_info["blocking_prerequisite"],
            "prerequisites": c.get("prerequisites", []),
            "prerequisite_details": prereq_details,
            "source_units": source_units
        })

    edges = []
    concept_ids = {c["id"] for c in concepts}
    for p in prereqs:
        if p.get("concept_id") in concept_ids and p.get("prerequisite_id") in concept_ids:
            edges.append({
                "source": p["prerequisite_id"],
                "target": p["concept_id"],
                "strength": p.get("relationship_strength", 1.0)
            })

    return {
        "nodes": nodes,
        "edges": edges
    }

from backend.app.services.conflicts import source_conflict_detector

@router.get("/courses/{course_id}/conflicts")
def get_course_conflicts(course_id: str, request: Request):
    """
    Part 2 Unique Feature: Source Conflict Detector.
    Scans cross-document claims to detect disagreements and surfaces active/resolved conflicts.
    """
    student_id = get_student_id_from_request(request)
    ensure_course_access(db.get_by_id("courses", course_id), student_id)
    conflicts = source_conflict_detector.detect_conflicts_for_course(course_id)
    return {
        "course_id": course_id,
        "conflict_count": len(conflicts),
        "conflicts": conflicts
    }

@router.post("/courses/{course_id}/conflicts/{conflict_id}/resolve")
def resolve_course_conflict(course_id: str, conflict_id: str, payload: Dict[str, Any], request: Request):
    """
    Allows the student to resolve a conflict by marking which source document to trust.
    """
    student_id = get_student_id_from_request(request)
    ensure_course_access(db.get_by_id("courses", course_id), student_id)
    trusted_doc = payload.get("trusted_document")
    if not trusted_doc:
        raise HTTPException(status_code=400, detail="trusted_document is required")
    res = source_conflict_detector.resolve_conflict(conflict_id, trusted_doc, student_id)
    return res

from backend.app.services.syllabus import syllabus_auditor

@router.get("/courses/{course_id}/syllabus-coverage")
def get_syllabus_coverage(course_id: str, request: Request):
    """
    Part 4 Unique Feature: Syllabus Coverage Audit.
    Maps syllabus topics against uploaded course documents and concepts (covered / thin / missing).
    """
    student_id = get_student_id_from_request(request)
    ensure_course_access(db.get_by_id("courses", course_id), student_id)
    report = syllabus_auditor.audit_coverage(course_id)
    return report

@router.post("/courses/{course_id}/documents/{document_id}/tag-syllabus")
def tag_document_as_syllabus(course_id: str, document_id: str, payload: Dict[str, Any], request: Request):
    """
    Allows user to tag/untag a document as syllabus.
    """
    student_id = get_student_id_from_request(request)
    ensure_course_access(db.get_by_id("courses", course_id), student_id)
    doc = db.get_by_id("documents", document_id)
    if not doc or doc.get("course_id") != course_id:
        raise HTTPException(status_code=404, detail="Document not found")
    is_syl = bool(payload.get("is_syllabus", True))
    doc["is_syllabus"] = is_syl
    db.update("documents", document_id, doc)
    return {"status": "success", "document_id": document_id, "is_syllabus": is_syl}




