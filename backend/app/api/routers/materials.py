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

# --- Multimodal Upload & Ingestion ---
@router.post("/courses/{course_id}/upload")
async def upload_course_material(
    course_id: str,
    request: Request,
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    task_id: Optional[str] = Form(None)
):
    owner_id = get_owner_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, owner_id)

    uploaded_files: List[UploadFile] = []
    seen_names = set()
    if files:
        for f in files:
            if f and f.filename and f.filename not in seen_names:
                uploaded_files.append(f)
                seen_names.add(f.filename)
    if file and file.filename and file.filename not in seen_names:
        uploaded_files.append(file)
        seen_names.add(file.filename)

    if not uploaded_files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    files_data = []
    active_task_id = task_id or str(uuid.uuid4())
    for f in uploaded_files:
        content_bytes = await f.read()
        file_hash = hashlib.sha256(content_bytes).hexdigest()
        saved_path = storage.save_file(f.filename, content_bytes)
        files_data.append({
            "filename": f.filename,
            "file_path": saved_path,
            "file_hash": file_hash,
            "bytes": content_bytes
        })

    pipeline_res = ingestion_pipeline.process_course_documents(
        course_id=course_id,
        files_data=files_data,
        task_id=active_task_id,
        owner_id=owner_id
    )

    return {
        "message": f"Successfully processed {len(files_data)} file(s)",
        "task_id": active_task_id,
        "course_id": course_id,
        "stage_a_ready": pipeline_res.get("stage_a_ready", True),
        "chunks_count": pipeline_res.get("chunks_count", 0),
        "pipeline_result": pipeline_res
    }

@router.post("/courses/{course_id}/youtube")
def ingest_course_youtube(
    course_id: str,
    payload: YouTubeIngestRequest,
    request: Request
):
    owner_id = get_owner_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, owner_id)

    active_task_id = payload.task_id or str(uuid.uuid4())
    result = ingestion_pipeline.ingest_youtube_url(
        course_id=course_id,
        url=payload.url,
        task_id=active_task_id,
        owner_id=owner_id
    )
    return {
        "message": result.get("message", "Successfully processed YouTube video"),
        "task_id": active_task_id,
        "document_id": result.get("document_id"),
        "pipeline_result": result
    }

@router.get("/ingestion/progress/{task_id}")
def get_ingestion_progress(task_id: str):
    from backend.app.services.ingestion_tracker import ingestion_tracker
    progress = ingestion_tracker.get_progress(task_id)
    if not progress:
        return {
            "task_id": task_id,
            "status": "completed",
            "progress_pct": 100,
            "current_stage": "Complete"
        }
    return progress

@router.get("/ingestion/stream/{task_id}")
async def stream_ingestion_progress(task_id: str):
    """Server-Sent Events (SSE) stream for real-time ingestion stage tracking"""
    from fastapi.responses import StreamingResponse
    import asyncio
    import json
    from backend.app.services.ingestion_tracker import ingestion_tracker

    async def event_generator():
        last_pct = -1
        for _ in range(120): # up to 60s
            prog = ingestion_tracker.get_progress(task_id)
            if prog:
                yield f"data: {json.dumps(prog)}\n\n"
                if prog.get("status") in ["completed", "error"]:
                    break
            else:
                yield f"data: {json.dumps({'task_id': task_id, 'progress_pct': 100, 'status': 'completed'})}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/documents/{document_id}/status")
def get_document_status(document_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    doc = db.get_by_id("documents", document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_course_access(db.get_by_id("courses", doc.get("course_id")), student_id)
    chunks = db.list_all("knowledge_chunks", lambda c: c.get("document_id") == document_id)
    return {
        "document": doc,
        "chunks_count": len(chunks)
    }

@router.post("/documents/{document_id}/reanalyze")
def reanalyze_document(document_id: str, request: Request):
    """Re-runs extraction pipeline for a single document with progress reporting."""
    student_id = get_student_id_from_request(request)
    doc = db.get_by_id("documents", document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    course_id = doc.get("course_id")
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, student_id)

    task_id = str(uuid.uuid4())
    file_path = doc.get("storage_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Document storage file not found on disk")

    # Clear existing chunks for this document
    old_chunks = db.list_all("knowledge_chunks", lambda c: c.get("document_id") == document_id)
    for c in old_chunks:
        db.delete("knowledge_chunks", c["id"])

    res = ingestion_pipeline.process_file(
        course_id=course_id,
        file_path=file_path,
        original_filename=doc.get("filename"),
        task_id=task_id,
        owner_id=student_id,
        file_hash=doc.get("file_hash")
    )
    return {"status": "success", "task_id": task_id, "result": res}

@router.post("/courses/{course_id}/reanalyze")
def reanalyze_course(course_id: str, request: Request):
    """Re-runs extraction pipeline across all documents in a course."""
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, student_id)

    docs = db.list_all("documents", lambda d: d.get("course_id") == course_id)
    results = []
    for doc in docs:
        file_path = doc.get("storage_path")
        if file_path and os.path.exists(file_path):
            old_chunks = db.list_all("knowledge_chunks", lambda c: c.get("document_id") == doc["id"])
            for c in old_chunks:
                db.delete("knowledge_chunks", c["id"])
            task_id = str(uuid.uuid4())
            try:
                res = ingestion_pipeline.process_file(
                    course_id=course_id,
                    file_path=file_path,
                    original_filename=doc.get("filename"),
                    task_id=task_id,
                    owner_id=student_id,
                    file_hash=doc.get("file_hash")
                )
                results.append(res)
            except Exception as e:
                results.append({"document_id": doc["id"], "status": "needs analysis", "error": str(e)})

    return {"status": "success", "course_id": course_id, "processed_count": len(results), "results": results}



# --- User Documents Endpoint ---
@router.get("/user/documents")
def get_user_documents(request: Request, course_id: Optional[str] = None):
    student_id = get_student_id_from_request(request)
    if course_id and course_id != "all":
        docs = db.list_all("documents", lambda d: d.get("course_id") == course_id)
    else:
        docs = db.list_all("documents")
    
    formatted = []
    for d in docs:
        sz = d.get("file_size", 0)
        size_str = f"{sz / 1024:.1f} KB" if sz < 1024 * 1024 else f"{sz / (1024 * 1024):.1f} MB"
        created = d.get("created_at", "")[:10]
        c_id = d.get("course_id")
        course_name = ""
        if c_id:
            c_obj = db.get_by_id("courses", c_id)
            if c_obj:
                course_name = c_obj.get("name") or c_obj.get("title", "")
        
        doc_chunks = db.list_all("knowledge_chunks", lambda c: c.get("document_id") == d["id"])
        doc_cids = set()
        for chk in doc_chunks:
            doc_cids.update(chk.get("concept_ids", []))

        doc_concept_names = []
        for cid in doc_cids:
            c_obj = db.get_by_id("concepts", cid)
            if c_obj and c_obj.get("name"):
                doc_concept_names.append(c_obj.get("name"))
            if len(doc_concept_names) >= 4:
                break
        if not doc_concept_names:
            first_chk = doc_chunks[0] if doc_chunks else None
            if first_chk:
                doc_concept_names = [w.strip() for w in first_chk.get("content", "").split(".") if len(w.strip()) > 5][:2]

        formatted.append({
            "id": d["id"],
            "name": d.get("filename", "Untitled Document"),
            "size": size_str,
            "date": created,
            "type": d.get("file_type", "pdf"),
            "course_id": c_id,
            "course_name": course_name,
            "page_count": d.get("page_count", 1),
            "slide_count": d.get("slide_count", 0),
            "chunk_count": len(doc_chunks),
            "concept_count": len(doc_cids),
            "status": d.get("status", "processed"),
            "last_error": d.get("error_message"),
            "topics": doc_concept_names
        })
    return formatted


@router.get("/user/documents/{document_id}/download")
def download_user_document(document_id: str, request: Request):
    from fastapi.responses import FileResponse
    student_id = get_student_id_from_request(request)
    doc = db.get_by_id("documents", document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    c_id = doc.get("course_id")
    if c_id:
        course = db.get_by_id("courses", c_id)
        ensure_course_access(course, student_id)
    elif str(doc.get("owner_id") or "") != str(student_id):
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = doc.get("storage_path") or doc.get("file_path")
    if file_path and os.path.exists(file_path):
        filename = doc.get("filename", "downloaded_document")
        return FileResponse(path=file_path, filename=filename, media_type="application/octet-stream")
    
    # Fallback to demo file on disk if exists
    filename = doc.get("filename", "")
    demo_path = os.path.join(settings.STORAGE_DIR, "uploads", filename)
    if os.path.exists(demo_path):
        return FileResponse(path=demo_path, filename=filename, media_type="application/octet-stream")

    raise HTTPException(status_code=404, detail="File content not found on server disk")


@router.delete("/user/documents/{document_id}")
def delete_user_document(document_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    doc = db.get_by_id("documents", document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    c_id = doc.get("course_id")
    if c_id:
        course = db.get_by_id("courses", c_id)
        ensure_course_access(course, student_id)
    elif str(doc.get("owner_id") or "") != str(student_id):
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Try removing physical file if exists
    storage_path = doc.get("storage_path") or doc.get("file_path")
    if storage_path and os.path.exists(storage_path):
        try:
            os.remove(storage_path)
        except Exception:
            pass

    # Remove associated chunks
    chunks = db.list_all("knowledge_chunks", lambda ch: ch.get("document_id") == document_id)
    for ch in chunks:
        db.delete("knowledge_chunks", ch["id"])
    
    db.delete("documents", document_id)
    return {"status": "success", "deleted_id": document_id}


# --- Part 6: Lecture-to-Slide Alignment Endpoints ---
from backend.app.services.slide_alignment import slide_alignment_service

@router.get("/courses/{course_id}/slide-alignments")
def get_slide_alignments(course_id: str, request: Request):
    """Returns sequential alignment pairs between lecture video transcripts and course slides."""
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, student_id)

    alignments = db.list_all("slide_alignments", lambda a: a.get("course_id") == course_id)
    if not alignments:
        alignments = slide_alignment_service.align_course_lectures_to_slides(course_id)

    return {
        "course_id": course_id,
        "alignment_count": len(alignments),
        "alignments": alignments
    }

@router.get("/courses/{course_id}/slide-for-moment")
def get_slide_for_moment(course_id: str, timestamp: float, request: Request):
    """Given a timestamp in seconds in a video lecture, returns the corresponding aligned slide."""
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, student_id)

    match = slide_alignment_service.get_slide_for_timestamp(course_id, timestamp)
    if not match:
        raise HTTPException(status_code=404, detail="No aligned slide found for this moment")
    return match

@router.get("/courses/{course_id}/moments-for-slide")
def get_moments_for_slide(course_id: str, document: str, slide: int, request: Request):
    """Given a presentation slide, returns moments in video lectures discussing it."""
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", course_id)
    ensure_course_access(course, student_id)

    moments = slide_alignment_service.get_moments_for_slide(course_id, document, slide)
    return {
        "course_id": course_id,
        "slide_document": document,
        "slide_number": slide,
        "moments_count": len(moments),
        "moments": moments
    }




