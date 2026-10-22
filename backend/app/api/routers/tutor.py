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
    ExplainUrlRequest, AddNoteRequest, YouTubeIngestRequest, TeachBackRequest
)
from backend.app.services.teach_back import teach_back_evaluator
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

# --- Study Notes & Web URL Ingestion ---
@router.post("/courses/{course_id}/add-note")
def add_course_note(course_id: str, payload: AddNoteRequest, request: Request):
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, student_id)
    
    active_task_id = payload.task_id or str(uuid.uuid4())
    result = ingestion_pipeline.ingest_raw_text(
        course_id=course_id,
        title=payload.title,
        text=payload.content,
        source_type="notes",
        owner_id=student_id,
        task_id=active_task_id
    )
    return {
        "message": f"Successfully ingested note '{payload.title}' into course database",
        "task_id": active_task_id,
        "result": result
    }

@router.post("/tutor/explain-url")
def explain_study_material_url(payload: ExplainUrlRequest, request: Request):
    student_id = get_student_id_from_request(request)
    c_id = payload.course_id
    if payload.save_to_knowledge_base:
        if not c_id:
            raise HTTPException(status_code=400, detail="Choose a course before saving this material")
        ensure_course_access(db.get_by_id("courses", c_id), student_id)
    scrape_res = web_extractor.fetch_and_clean_url(payload.url)
    if not scrape_res.get("success"):
        raise HTTPException(
            status_code=400,
            detail=f"Unable to access study link: {scrape_res.get('error', 'Connection error')}"
        )

    llm = get_llm_provider(settings.LLM_PROVIDER)
    explanation_res = llm.explain_study_material_url(
        url=payload.url,
        title=scrape_res.get("title", "Study Material"),
        text_content=scrape_res.get("text", "")
    )

    # Ingest into course database if requested (Step 1 Requirement 3: store as type 'web' or 'video' with its URL)
    if payload.save_to_knowledge_base:
        try:
            yt_id = storage.extract_youtube_video_id(payload.url)
            if yt_id:
                ingestion_pipeline.ingest_youtube_url(
                    course_id=c_id,
                    url=payload.url,
                    owner_id=student_id
                )
            else:
                ingestion_pipeline.ingest_raw_text(
                    course_id=c_id,
                    title=f"Web: {scrape_res.get('title', 'Study Material')[:60]}",
                    text=scrape_res.get("text", "")[:16000],
                    source_type="web",
                    url=payload.url,
                    owner_id=student_id
                )
        except Exception as e:
            print(f"[explain_study_material_url] Ingestion failed: {e}")

    return {
        "status": "success",
        "url": payload.url,
        "title": scrape_res.get("title"),
        "domain": scrape_res.get("domain"),
        "explanation": explanation_res.get("explanation"),
        "summary": explanation_res.get("summary"),
        "key_points": explanation_res.get("key_points", []),
        "code_snippet": explanation_res.get("code_snippet"),
        "recommended_next_step": explanation_res.get("recommended_next_step")
    }

# --- Grounded Tutor ---
@router.post("/tutor/query")
def tutor_query(payload: TutorQueryRequest, request: Request):
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", payload.course_id)
    ensure_course_access(course, student_id)

    # Fast-path for quick greetings & chitchat
    q_low = payload.query.lower().strip()
    is_greeting = q_low in ("hi", "hello", "hey", "hola", "greetings", "good morning", "good evening", "good afternoon", "how are you", "who are you")
    is_quiz_style = (payload.style == "Quiz me") or ("quiz me" in q_low) or ("quiz" in q_low and any(w in q_low for w in ["give", "ask", "test", "practice", "question"]))
    
    learning_state = bkt_engine.get_learner_profile(student_id, payload.course_id)
    if is_greeting:
        learner_context = f"Course: {course.get('name', 'Current course')}."
    else:
        weak = [m["concept_name"] for m in learning_state["mastery_by_concept"] if m["mastery_probability"] < 0.45 and not m.get("is_locked")]
        mastered = [m["concept_name"] for m in learning_state["mastery_by_concept"] if m["mastery_probability"] >= 0.75]
        locked = [m["concept_name"] for m in learning_state["mastery_by_concept"] if m.get("is_locked")]
        recent_attempts = sorted(
            db.list_all("attempts", lambda a: a.get("user_id") == student_id and a.get("concept_id") in {m["concept_id"] for m in learning_state["mastery_by_concept"]}),
            key=lambda a: a.get("created_at", ""), reverse=True
        )[:5]
        learner_context = (
            f"Course: {course.get('name', 'Current course')}. "
            f"Subject/Discipline: {course.get('subject', 'General Subject')}. "
            f"Weak concepts to reinforce: {', '.join(weak) or 'none identified'}. "
            f"Mastered concepts: {', '.join(mastered) or 'none yet'}. "
            f"Locked concepts: {', '.join(locked) or 'none'}. "
            f"Recent answer events: {len(recent_attempts)}. "
            "When a requested concept is locked, recommend its weakest prerequisite first. "
            "Ensure explanations are structured with markdown headers, bullet points, and real-world clarity."
        )

    # --- Strands Decider 2B gate: ONE ~100ms round trip decides policy / clarity / model tier / prerequisite gap ---
    gate = None
    short_response = None
    ctx_store: Dict[str, Any] = {}
    try:
        from backend.app.decider.service import decider_service
        from backend.app.decider.context import context_scores_var, route_var
        route_var.set(None)
        context_scores_var.set(ctx_store)
        if not is_greeting:
            gate = decider_service.evaluate(
                message=payload.query, course_id=payload.course_id, student_id=student_id,
                conversation_id=payload.conversation_id, learning_state=learning_state
            )
            short_response = decider_service.short_circuit_response(
                gate, payload.query, payload.course_id, payload.conversation_id
            )
            if gate.learner_hint:
                learner_context = f"{learner_context} {gate.learner_hint}"
            if gate.action == "quiz":
                is_quiz_style = True
            if short_response:
                is_quiz_style = False
    except Exception as e:
        print(f"[DeciderGate] skipped (tutor answers normally): {e}")

    gate_mode = gate.mode_override if gate else None
    response = short_response or rag_engine.answer_query(
        course_id=payload.course_id,
        query=payload.query,
        conversation_id=payload.conversation_id,
        topic_id=payload.topic_id,
        difficulty=payload.difficulty or "Medium",
        mode=gate_mode or payload.style or payload.mode or "Simple",
        style=gate_mode or payload.style,
        language=payload.language or "en",
        allow_outside_knowledge=payload.allow_outside_knowledge,
        learner_context=learner_context,
        owner_id=student_id,
        document_ids=payload.document_ids
    )
    if gate:
        response["decision_trace"] = {**gate.to_public(), "context": ctx_store,
                                      "generated_by": response.get("generated_by")}

    # When Quiz me is requested, generate an interactive quiz question directly
    if is_quiz_style:
        try:
            quiz_result = assessment_engine.generate_chat_quiz(
                course_id=payload.course_id,
                conversation_id=payload.conversation_id,
                student_id=student_id,
                question_count=1
            )
            q_list = quiz_result.get("questions") or []
            if q_list:
                cq = q_list[0]
                q_text = cq.get("question_text") or cq.get("stem") or cq.get("question") or "Diagnostic Question"
                response["interactive_quiz"] = {
                    "question_id": cq.get("id"),
                    "question_text": q_text,
                    "options": cq.get("options") or ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": cq.get("correct_answer", ""),
                    "explanation": cq.get("explanation", "Verified based on course principles."),
                    "concept_name": cq.get("concept_name", "Course Concept")
                }
                response["check_yourself_question"] = q_text
                c_name = cq.get("concept_name", "key concept")
                if is_greeting:
                    response["answer"] = (
                        f"Hello! 👋 Here is your diagnostic quiz on **{c_name}** to test your course mastery:\n\n"
                        f"**{q_text}**\n\n"
                        "Select an option below to test your understanding!"
                    )
                else:
                    response["answer"] = (
                        f"{response.get('answer', '')}\n\n"
                        f"---\n### 🎯 Interactive Checkpoint: **{c_name}**\n"
                        f"**{q_text}**\n\n"
                        "Test yourself with the interactive question below:"
                    )
        except Exception as e:
            print(f"[tutor_query] Chat quiz synthesis note: {e}")

    # Save to message history with valid UUID conversation
    conv_id = payload.conversation_id
    if not conv_id or len(conv_id) < 10:
        conv_id = str(uuid.uuid4())
        db.insert("conversations", {
            "id": conv_id,
            "student_id": student_id,
            "user_id": student_id,
            "course_id": payload.course_id,
            "title": f"Tutoring: {payload.query[:30]}"
        })

    db.insert("messages", {
        "conversation_id": conv_id,
        "role": "user",
        "content": payload.query,
        "mode": payload.mode
    })
    db.insert("messages", {
        "conversation_id": conv_id,
        "role": "assistant",
        "content": response.get("answer"),
        "is_grounded": response.get("grounded"),
        "citations": response.get("citations", []),
        "is_outside_knowledge": response.get("is_outside_knowledge"),
        "interactive_quiz": response.get("interactive_quiz")
    })
    response["conversation_id"] = conv_id

    # Update learner mastery after tutor turn with smaller weight
    try:
        updated_concepts = set()
        for cit in response.get("citations", []):
            cid = cit.get("concept_id")
            if cid and cid not in updated_concepts:
                bkt_engine.update_mastery(
                    student_id=student_id,
                    course_id=payload.course_id,
                    concept_id=cid,
                    is_correct=True,
                    source="tutor_turn"
                )
                updated_concepts.add(cid)
        if not updated_concepts and payload.topic_id:
            top_concepts = [m for m in learning_state.get("mastery_by_concept", []) if m.get("concept_id")]
            if top_concepts:
                bkt_engine.update_mastery(
                    student_id=student_id,
                    course_id=payload.course_id,
                    concept_id=top_concepts[0]["concept_id"],
                    is_correct=True,
                    source="tutor_turn"
                )
    except Exception as e:
        print(f"[TutorTurn] Mastery update note: {e}")

    return response

# --- Conversation History Management (ChatGPT-style multi-session) ---
@router.get("/conversations")
def list_conversations(request: Request, course_id: Optional[str] = None):
    student_id = get_student_id_from_request(request)
    if course_id:
        ensure_course_access(db.get_by_id("courses", course_id), student_id)
        convs = db.list_all(
            "conversations",
            lambda c: c.get("course_id") == course_id and str(c.get("student_id") or c.get("user_id") or "") == str(student_id)
        )
    else:
        convs = db.list_all(
            "conversations",
            lambda c: str(c.get("student_id") or c.get("user_id") or "") == str(student_id)
        )
    return sorted(convs, key=lambda c: c.get("updated_at") or c.get("created_at") or "", reverse=True)

@router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    conv = db.get_by_id("conversations", conversation_id)
    if not conv or str(conv.get("student_id") or conv.get("user_id") or "") != str(student_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = db.list_all("messages", lambda m: m.get("conversation_id") == conversation_id)
    return sorted(msgs, key=lambda m: m.get("created_at", ""))

@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    conv = db.get_by_id("conversations", conversation_id)
    if not conv or str(conv.get("student_id") or conv.get("user_id") or "") != str(student_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = db.list_all("messages", lambda m: m.get("conversation_id") == conversation_id)
    for m in msgs:
        db.delete("messages", m["id"])
    db.delete("conversations", conversation_id)
    return {"status": "success", "deleted_id": conversation_id}

@router.get("/tutor/sources/{chunk_id}")
def get_source_details(chunk_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    chk = db.get_by_id("knowledge_chunks", chunk_id)
    if not chk:
        # Check by visual element
        v = db.get_by_id("visual_elements", chunk_id)
        if v:
            ensure_course_access(db.get_by_id("courses", v.get("course_id")), student_id)
            return {"visual_element": v}
        raise HTTPException(status_code=404, detail="Source chunk not found")
    ensure_course_access(db.get_by_id("courses", chk.get("course_id")), student_id)
    
    # Retrieve linked visual element if any
    v_el = None
    if chk.get("visual_element"):
        v_el = chk.get("visual_element")

    doc = db.get_by_id("documents", chk.get("document_id")) if chk.get("document_id") else None
    file_url = (doc.get("file_url") or doc.get("storage_path") or f"/storage/documents/{doc.get('filename')}") if doc else None
    location = {
        "page_number": chk.get("page_number"),
        "slide_number": chk.get("slide_number"),
        "timestamp_start": chk.get("timestamp_start"),
        "timestamp_end": chk.get("timestamp_end"),
    }

    return {
        "chunk": chk,
        "file_url": file_url,
        "location": location,
        "document": doc,
        "document_name": chk.get("document_name") or (doc.get("filename") if doc else "Course Document"),
        "visual_element": v_el
    }

@router.post("/tutor/teach-back")
def evaluate_teach_back(payload: TeachBackRequest, request: Request):
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", payload.course_id)
    ensure_course_access(course, student_id)
    
    result = teach_back_evaluator.evaluate_teach_back(
        student_id=student_id,
        course_id=payload.course_id,
        concept_id=payload.concept_id,
        explanation_text=payload.explanation
    )
    return result



