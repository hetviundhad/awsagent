import pytest
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.database import db
from backend.app.services.conflicts import source_conflict_detector
from backend.app.services.teach_back import teach_back_evaluator
from backend.app.services.syllabus import syllabus_auditor
from backend.app.services.slide_alignment import slide_alignment_service
from backend.app.learner.rootcause import root_cause_tracer
from backend.app.learner.bkt import bkt_engine
from eval.fixtures.sample_loader import DEMO_COURSE_ID
from tests.conftest import make_test_auth_headers

client = TestClient(app)
AUTH_HEADERS = make_test_auth_headers("student_test_unique_features")

def test_rootcause_tracing():
    """Part 1: Verify 'Why Am I Stuck?' Root-Cause Prerequisite Tracing."""
    concepts = db.list_all("concepts", lambda c: c.get("course_id") == DEMO_COURSE_ID)
    assert len(concepts) > 0, "Demo course concepts required"
    target_c = concepts[0]["id"]

    diagnosis = root_cause_tracer.diagnose_stuck(
        student_id="test_stuck_student",
        course_id=DEMO_COURSE_ID,
        target_concept_id=target_c
    )
    assert "root_causes" in diagnosis
    assert "repair_path" in diagnosis
    assert "evidence" in diagnosis
    assert "target_concept_name" in diagnosis

def test_conflicts_with_injected_data():
    """Part 2: Verify Source Conflict Detector on known injected conflicting claims."""
    # Create two conflicting chunks about the same attribute in different documents
    chunk_a = {
        "id": f"chk_test_a_{uuid.uuid4().hex[:6]}",
        "course_id": "test_conflict_course",
        "concept_id": "concept_demo_1",
        "document_name": "Official_Architecture_Manual.pdf",
        "page_number": 12,
        "content": "The HDFS default block size is 128 MB across production clusters.",
        "created_at": "2026-10-14T00:00:00Z"
    }
    chunk_b = {
        "id": f"chk_test_b_{uuid.uuid4().hex[:6]}",
        "course_id": "test_conflict_course",
        "concept_id": "concept_demo_1",
        "document_name": "Storage_Optimization_Whitepaper.pdf",
        "page_number": 45,
        "content": "The HDFS default block size is 256 MB across production clusters for large files.",
        "created_at": "2026-10-14T00:00:00Z"
    }
    db.insert("knowledge_chunks", chunk_a)
    db.insert("knowledge_chunks", chunk_b)

    conflicts = source_conflict_detector.detect_conflicts_for_course("test_conflict_course")
    assert len(conflicts) >= 1, "Detector should capture numerical disagreement between documents"
    first = conflicts[0]
    assert first["claim_a"]["document_name"] != first["claim_b"]["document_name"]
    assert first["status"] == "active"

def test_teach_back_mode():
    """Part 3: Verify Teach-Back explanation evaluation and BKT updates."""
    concepts = db.list_all("concepts", lambda c: c.get("course_id") == DEMO_COURSE_ID)
    assert len(concepts) > 0, "Demo course concepts required"
    c_id = concepts[0]["id"]

    explanation = "In dynamic programming, optimal substructure means that optimal solutions to subproblems combine into optimal solutions to the overall problem."
    result = teach_back_evaluator.evaluate_teach_back(
        student_id="test_teach_back_student",
        course_id=DEMO_COURSE_ID,
        concept_id=c_id,
        explanation_text=explanation
    )
    assert "is_passed" in result
    assert "overall_score" in result
    assert "correct_claims" in result
    assert "bkt_update" in result
    assert "mastery_gain" in result["bkt_update"]

def test_syllabus_coverage_audit():
    """Part 4: Verify Syllabus Coverage Auditor."""
    # Seed a sample syllabus document in demo course
    db.insert("documents", {
        "id": "doc_syllabus_test",
        "course_id": DEMO_COURSE_ID,
        "filename": "Course_Syllabus_2026.pdf",
        "file_type": "pdf",
        "status": "processed",
        "page_count": 3
    })
    report = syllabus_auditor.audit_coverage(DEMO_COURSE_ID)
    assert "has_syllabus" in report
    assert "overall_coverage_pct" in report
    assert "counts" in report
    assert "units" in report
    assert "items" in report
    assert report["overall_coverage_pct"] >= 0.0

def test_confidence_calibrated_bkt():
    """Part 5: Verify Metacognitive Confidence-Calibrated BKT & Misconceptions."""
    m_init = bkt_engine.get_or_create_mastery("test_calib_student", DEMO_COURSE_ID, "con_test_calib")
    p_init = m_init.get("mastery_probability", 0.20)

    # 1. Confident Wrong answer should heavily penalize mastery
    m_wrong = bkt_engine.update_mastery(
        student_id="test_calib_student",
        course_id=DEMO_COURSE_ID,
        concept_id="con_test_calib",
        is_correct=False,
        difficulty="Medium",
        source="quiz",
        student_confidence="Sure"
    )
    assert m_wrong["mastery_probability"] < p_init, "Confident wrong answer must reduce mastery"
    assert m_wrong.get("confident_wrong_count", 0) >= 1

    # 2. Correct Guess should have discounted mastery increase
    m_guess = bkt_engine.update_mastery(
        student_id="test_calib_student",
        course_id=DEMO_COURSE_ID,
        concept_id="con_test_calib_2",
        is_correct=True,
        difficulty="Medium",
        source="quiz",
        student_confidence="Guess"
    )
    m_sure = bkt_engine.update_mastery(
        student_id="test_calib_student",
        course_id=DEMO_COURSE_ID,
        concept_id="con_test_calib_3",
        is_correct=True,
        difficulty="Medium",
        source="quiz",
        student_confidence="Sure"
    )
    gain_guess = m_guess["mastery_probability"] - 0.20
    gain_sure = m_sure["mastery_probability"] - 0.20
    assert gain_sure > gain_guess, f"Confident correct ({gain_sure}) must exceed guess correct ({gain_guess})"

def test_slide_alignment():
    """Part 6: Verify Lecture-to-Slide Multimodal Alignment."""
    # Seed a video chunk and slide chunk in DEMO_COURSE_ID
    db.insert("knowledge_chunks", {
        "id": "chk_video_demo_1",
        "course_id": DEMO_COURSE_ID,
        "document_name": "Lecture 1: Intro to Dynamic Programming",
        "source_type": "video",
        "timestamp_start": 30.0,
        "timestamp_end": 60.0,
        "content": "In this lecture, we introduce dynamic programming and memoization tables for caching subproblems."
    })
    db.insert("knowledge_chunks", {
        "id": "chk_slide_demo_1",
        "course_id": DEMO_COURSE_ID,
        "document_name": "Lecture1_Slides.pptx",
        "source_type": "slide",
        "slide_number": 2,
        "content": "Dynamic Programming: Principle of Optimality and Memoization Tables."
    })

    alignments = slide_alignment_service.align_course_lectures_to_slides(DEMO_COURSE_ID)
    assert len(alignments) > 0, "Should generate lecture-to-slide alignments"
    first = alignments[0]
    assert "timestamp_start" in first
    assert "slide_number" in first
    assert "slide_document" in first
    assert "similarity_score" in first

    # Test timestamp moment lookup
    moment = slide_alignment_service.get_slide_for_timestamp(DEMO_COURSE_ID, float(first["timestamp_start"]))
    assert moment is not None
    assert moment["slide_number"] == first["slide_number"]
