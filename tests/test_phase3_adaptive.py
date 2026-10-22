import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.learner.bkt import bkt_engine
from backend.app.assessment.generator import assessment_engine
from backend.app.services.database import db
from eval.fixtures.sample_loader import seed_demo_course_if_needed, DEMO_COURSE_ID
from tests.conftest import make_test_auth_headers

client = TestClient(app)
AUTH_HEADERS = make_test_auth_headers("student_phase3_test")

@pytest.fixture(autouse=True)
def setup_course():
    seed_demo_course_if_needed()

def test_cross_model_question_validation_and_discard_rate():
    """
    Phase 3: Cross-model question validation (generator -> independent blind solver)
    tracks discard rates and logs validation metrics.
    """
    metrics_before = assessment_engine.get_validation_metrics()
    assert "discard_rate" in metrics_before
    assert "total_evaluated" in metrics_before

    import uuid
    test_c_id = f"test_adaptive_{uuid.uuid4().hex[:6]}"
    chunk = {
        "id": f"chk_test_{uuid.uuid4().hex[:6]}",
        "course_id": test_c_id,
        "content": "A problem has optimal substructure if an optimal solution contains within it optimal solutions to subproblems.",
        "document_name": "Algorithms.pdf",
        "page_number": 42
    }
    existing_hashes = set()
    q = assessment_engine._synthesize_and_verify_question(test_c_id, chunk, existing_hashes, "Adaptive")
    assert q is not None
    assert q["verification_status"] == "verified"
    assert q.get("concept_id") is not None # Tagged with knowledge-graph node!

    metrics_after = assessment_engine.get_validation_metrics()
    assert metrics_after["total_evaluated"] >= metrics_before["total_evaluated"] + 1
    assert metrics_after["validated_passed"] >= 1

    # Verify endpoint works
    res = client.get("/api/assessment/validation-metrics", headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert "discard_rate" in data
    assert "total_evaluated" in data

def test_knowledge_graph_node_tagging_and_bkt_propagation():
    """
    Phase 3 & Step 1 Rule 5: Every question has concept_id. Answering updates BKT for that node,
    and weak prerequisites (attempted >= 3 times with P(L) < 0.60) lock dependent concepts.
    """
    student_id = "test_phase3_student"
    
    # Locate a real concept with a prerequisite in the ingested demo course
    prereqs = db.list_all("concept_prerequisites", lambda p: (
        db.get_by_id("concepts", p.get("concept_id")) is not None and
        db.get_by_id("concepts", p.get("concept_id")).get("course_id") == DEMO_COURSE_ID
    ))
    if not prereqs:
        # Create a prerequisite relationship between demo concepts if not present
        concepts = db.list_all("concepts", lambda c: c.get("course_id") == DEMO_COURSE_ID)
        assert len(concepts) >= 2
        target_concept_id = concepts[1]["id"]
        prereq_id = concepts[0]["id"]
        bkt_engine.add_prerequisite_edge(DEMO_COURSE_ID, prereq_id, target_concept_id)
    else:
        rel = prereqs[0]
        target_concept_id = rel["concept_id"]
        prereq_id = rel["prerequisite_id"]

    # Per Step 1 Rule 5: Set prerequisite to low mastery (<0.60) with >= 3 attempts
    prereq_mastery = bkt_engine.get_or_create_mastery(student_id, DEMO_COURSE_ID, prereq_id)
    prereq_mastery["mastery_probability"] = 0.30
    prereq_mastery["attempt_count"] = 3
    db.update("learner_mastery", prereq_mastery["id"], prereq_mastery)

    # Check that dependent concept is now locked
    lock_status = bkt_engine.check_concept_locked(student_id, DEMO_COURSE_ID, target_concept_id)
    assert lock_status["is_locked"] is True
    assert lock_status["blocking_prerequisite"]["id"] == prereq_id

    # When student answers correctly, prerequisite-aware propagation bounds effective learning
    updated = bkt_engine.update_mastery(
        student_id=student_id,
        course_id=DEMO_COURSE_ID,
        concept_id=target_concept_id,
        is_correct=True,
        difficulty="Medium"
    )
    assert updated["concept_id"] == target_concept_id
    assert updated["attempt_count"] >= 1

def test_locked_node_concept_map_endpoint():
    """
    Phase 3 & Step 1: /course/{course_id}/concept-map returns locked states, locking prerequisites,
    and locked reasons. Under Rule 5, new students with 0 attempts see 'Not started', not 'Locked'.
    """
    res = client.get(f"/api/course/{DEMO_COURSE_ID}/concept-map", headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data

    nodes = data["nodes"]
    assert len(nodes) > 0

    # Verify locked node properties exist on nodes
    has_lock_prop = any("is_locked" in n for n in nodes)
    assert has_lock_prop is True

    # Check node status consistency
    for n in nodes:
        if n.get("is_locked"):
            assert "locked_reason" in n
            assert n["status"] == "Locked"
        else:
            assert n["status"] in ["Not started", "In progress", "Mastered", "Developing", "Needs Attention"]

def test_misconception_remediation_flashcards_and_audio_brief():
    """
    Phase 3: Post-assessment diagnostic report CTAs:
    - Generate flashcards for this misconception
    - Play 2-minute audio brief
    """
    misconception_text = "Confusing greedy-choice property with optimal substructure in dynamic programming."

    # 1. Test audio brief generation
    brief_res = client.post("/api/assessment/misconception-brief", json={
        "misconception": misconception_text,
        "concept_name": "Dynamic Programming"
    }, headers=AUTH_HEADERS)
    assert brief_res.status_code == 200
    brief_data = brief_res.json()
    assert "script" in brief_data
    assert len(brief_data["script"]) > 50
    assert brief_data["duration_seconds"] == 120

    # 2. Test targeted flashcards generation
    fc_res = client.post("/api/assessment/misconception-flashcards", json={
        "misconception": misconception_text,
        "concept_name": "Dynamic Programming"
    }, headers=AUTH_HEADERS)
    assert fc_res.status_code == 200
    fc_data = fc_res.json()
    assert isinstance(fc_data, list)
    assert len(fc_data) >= 3
    assert "front" in fc_data[0]
    assert "back" in fc_data[0]
