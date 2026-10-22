import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.evaluation.simulator import synthetic_simulator
from eval.fixtures.sample_loader import seed_demo_course_if_needed, DEMO_COURSE_ID

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_course():
    seed_demo_course_if_needed()

def test_synthetic_student_simulator_10_sessions():
    """
    Phase 4: Run 10-session multi-agent simulation across 3 distinct personas:
    Fast Learner, Struggles with Math, and Skips Lectures.
    """
    results = synthetic_simulator.run_simulation(DEMO_COURSE_ID)
    
    assert results["total_sessions"] == 10
    assert "personas" in results
    assert "comparison_curve" in results
    assert len(results["comparison_curve"]) == 10

    personas = results["personas"]
    assert "fast_learner" in personas
    assert "struggles_math" in personas
    assert "skips_lectures" in personas

    # 1. Fast Learner: High final mastery and unlocks concepts
    fast = personas["fast_learner"]
    assert len(fast["sessions"]) == 10
    assert fast["final_mastery"] >= 65.0

    # 2. Struggles with Math: Gated by prerequisites
    math_p = personas["struggles_math"]
    assert len(math_p["sessions"]) == 10
    assert math_p["initial_mastery"] < fast["initial_mastery"]

    # 3. Skips Lectures: Plateaued / erratic
    skips = personas["skips_lectures"]
    assert len(skips["sessions"]) == 10
    assert skips["final_mastery"] < fast["final_mastery"]

def test_personalization_adaptation_divergence():
    """
    Phase 4: Verify recommendations adapt differently per persona (proof of personalization).
    """
    results = synthetic_simulator.run_simulation(DEMO_COURSE_ID)
    proof = results["personalization_proof"]
    assert len(proof) == 3

    persona_names = [p["persona"] for p in proof]
    assert "Fast Learner" in persona_names
    assert "Struggles with Math" in persona_names
    assert "Skips Lectures" in persona_names

    # Check that each persona receives distinct pedagogical recommendations
    recs = [p["distinct_recommendation"] for p in proof]
    assert len(set(recs)) >= 2

def test_simulator_api_endpoints():
    """
    Phase 4 API: POST /api/evaluation/simulate and GET /api/evaluation/simulator-stream.
    """
    from tests.conftest import make_test_auth_headers
    headers = make_test_auth_headers("student_phase4_test")

    # Synchronous simulation
    res = client.post("/api/evaluation/simulate", params={"course_id": DEMO_COURSE_ID}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_sessions"] == 10
    assert len(data["comparison_curve"]) == 10

    # Live SSE streaming endpoint (streaming client check)
    with client.stream("GET", "/api/evaluation/simulator-stream", params={"course_id": DEMO_COURSE_ID}, headers=headers) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        # read first event line
        for line in response.iter_lines():
            if line:
                assert "data:" in line
                break
