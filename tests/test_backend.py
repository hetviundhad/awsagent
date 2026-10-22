import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.rag.engine import rag_engine
from backend.app.assessment.generator import assessment_engine
from backend.app.learner.bkt import bkt_engine
from backend.app.evaluation.ragas_eval import evaluation_suite
from eval.fixtures.sample_loader import DEMO_COURSE_ID
from tests.conftest import make_test_auth_headers

client = TestClient(app)
AUTH_HEADERS = make_test_auth_headers("student_test_backend")

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "StudyMind AI"

def test_courses_endpoint():
    default_headers = make_test_auth_headers("default_student")
    response = client.get("/api/courses", headers=default_headers)
    assert response.status_code == 200
    courses = response.json()
    assert len(courses) >= 1
    algo_course = next((c for c in courses if c["id"] == DEMO_COURSE_ID), None)
    assert algo_course is not None
    assert "Algorithms" in algo_course["name"]

def test_course_detail():
    response = client.get(f"/api/courses/{DEMO_COURSE_ID}", headers=AUTH_HEADERS)
    assert response.status_code == 200
    detail = response.json()
    assert len(detail["units"]) >= 3
    assert len(detail["documents"]) >= 2
    assert len(detail["topics"]) >= 3

def test_grounded_tutor_query():
    # Ask grounded question
    res = client.post("/api/tutor/query", json={
        "course_id": DEMO_COURSE_ID,
        "query": "What is optimal substructure in dynamic programming?",
        "mode": "Quick Explanation"
    }, headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert len(data["citations"]) >= 1
    # Verify citation preserves exact metadata
    first_citation = data["citations"][0]
    assert "document_name" in first_citation
    assert ("page_number" in first_citation or "slide_number" in first_citation or "timestamp_start" in first_citation)

def test_unsupported_query_detection():
    # Ask question not in course material
    res = client.post("/api/tutor/query", json={
        "course_id": DEMO_COURSE_ID,
        "query": "How do I bake a chocolate cake with sourdough starter?",
        "allow_outside_knowledge": False
    }, headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is False
    assert "couldn't find sufficient evidence" in data["answer"].lower() or data.get("refused") is True or "not covered" in data["answer"].lower()
    assert len(data["citations"]) == 0

def test_outside_knowledge_mode():
    # When student explicitly asks using outside knowledge
    res = client.post("/api/tutor/query", json={
        "course_id": DEMO_COURSE_ID,
        "query": "What is quantum computing qubits?",
        "allow_outside_knowledge": True
    }, headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["is_outside_knowledge"] is True
    assert "outside knowledge" in data["answer"].lower()

def test_assessment_generation_and_verification():
    res = client.post("/api/assessments/generate", json={
        "course_id": DEMO_COURSE_ID,
        "question_count": 3,
        "difficulty": "Adaptive"
    }, headers=AUTH_HEADERS)
    assert res.status_code == 200
    assessment = res.json()
    assert len(assessment["questions"]) == 3
    for q in assessment["questions"]:
        assert q["verification_status"] == "verified"
        assert len(q["options"]) >= 2
        assert "question_hash" in q

def test_bkt_mastery_update():
    student_id = "student_test_backend"
    headers = make_test_auth_headers(student_id)
    initial_profile = client.get(f"/api/learner/{student_id}/mastery", headers=headers).json()
    assert "overall_mastery" in initial_profile

    # Submit correct answer on concept
    concept_id = "con_dp_1"
    updated = bkt_engine.update_mastery(
        student_id=student_id,
        course_id=DEMO_COURSE_ID,
        concept_id=concept_id,
        is_correct=True,
        difficulty="Medium"
    )
    assert updated["correct_count"] >= 1
    assert updated["mastery_probability"] > 0.0

def test_evaluation_suite():
    res = client.post("/api/evaluation/run", json={"course_id": DEMO_COURSE_ID}, headers=AUTH_HEADERS)
    assert res.status_code == 200
    eval_data = res.json()
    assert eval_data["faithfulness"] > 0.8
    assert eval_data["unsupported_rate"] >= 0.8
    assert len(eval_data["simulation_results"]) == 3 # Student A, B, C
