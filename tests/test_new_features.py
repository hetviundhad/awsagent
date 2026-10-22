import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from eval.fixtures.sample_loader import DEMO_COURSE_ID
from tests.conftest import make_test_auth_headers

client = TestClient(app)
AUTH_HEADERS = make_test_auth_headers("student_test_new_features")

def test_explain_study_material_url():
    """Verify live study material URL explanation and AI extraction."""
    response = client.post("/api/tutor/explain-url", json={
        "url": "https://www.geeksforgeeks.org/dynamic-programming/",
        "course_id": DEMO_COURSE_ID,
        "save_to_knowledge_base": True
    }, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "explanation" in data
    assert "summary" in data
    assert "geeksforgeeks.org" in data["domain"]

def test_add_course_note():
    """Verify student notes can be saved and indexed in the course knowledge base."""
    response = client.post(f"/api/courses/{DEMO_COURSE_ID}/add-note", json={
        "course_id": DEMO_COURSE_ID,
        "title": "CPU Scheduling Notes",
        "content": "Round Robin scheduling uses time quantums to prevent starvation. Context switching involves saving and restoring process state from PCB."
    }, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert data["result"]["chunks_count"] >= 1

def test_chat_quiz_generation():
    """Verify dynamic quiz generated from chat and student knowledge."""
    response = client.post("/api/assessments/chat-quiz", json={
        "course_id": DEMO_COURSE_ID,
        "question_count": 2
    }, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert len(data["questions"]) >= 1
    assert "options" in data["questions"][0]

def test_safe_mode_auto_submit():
    """Verify Safe Mode auto-submit with tab-switch detection records violation."""
    # 1. Generate an assessment
    gen_res = client.post("/api/assessments/generate", json={
        "course_id": DEMO_COURSE_ID,
        "question_count": 2,
        "difficulty": "Adaptive"
    }, headers=AUTH_HEADERS)
    assert gen_res.status_code == 200
    assessment = gen_res.json()
    assessment_id = assessment["id"]

    # 2. Submit with tab switch violation (auto-submitted)
    sub_res = client.post(f"/api/assessments/{assessment_id}/submit", json={
        "student_answers": {},
        "time_spent_seconds": 45,
        "auto_submitted": True,
        "safe_mode_violation": "Tab switch or window blur detected"
    }, headers=AUTH_HEADERS)
    assert sub_res.status_code == 200
    report = sub_res.json()
    assert report["auto_submitted"] is True
    assert "Tab switch" in report["safe_mode_violation"]

    # 3. Retrieve report
    rep_res = client.get(f"/api/assessments/{assessment_id}/report", headers=AUTH_HEADERS)
    assert rep_res.status_code == 200
    saved_rep = rep_res.json()
    assert saved_rep["auto_submitted"] is True
    assert "Tab switch" in saved_rep["safe_mode_violation"]

def test_llm_connection_test():
    """Verify testing the LLM connection returns live status."""
    res = client.post("/api/settings/test-llm", json={
        "llm_provider": "mock"
    }, headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "response" in data
