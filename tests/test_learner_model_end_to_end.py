import pytest
import uuid
from backend.app.learner.bkt import bkt_engine, BayesianKnowledgeTracer
from backend.app.services.database import db

@pytest.fixture(autouse=True)
def setup_test_data():
    test_course_id = f"test_course_{uuid.uuid4().hex[:8]}"
    db.insert("courses", {
        "id": test_course_id,
        "name": "Adaptive Learning Systems",
        "description": "Test course for BKT learner model validation"
    })
    
    # Create prerequisite concept A
    concept_a_id = f"concept_a_{uuid.uuid4().hex[:8]}"
    db.insert("concepts", {
        "id": concept_a_id,
        "course_id": test_course_id,
        "name": "Foundational Graph Theory",
        "prerequisites": []
    })

    # Create dependent concept B (requires A)
    concept_b_id = f"concept_b_{uuid.uuid4().hex[:8]}"
    db.insert("concepts", {
        "id": concept_b_id,
        "course_id": test_course_id,
        "name": "Dijkstra Shortest Path",
        "prerequisites": [concept_a_id]
    })
    db.insert("concept_prerequisites", {
        "id": f"rel_{uuid.uuid4().hex[:8]}",
        "concept_id": concept_b_id,
        "prerequisite_id": concept_a_id
    })

    return {
        "course_id": test_course_id,
        "concept_a_id": concept_a_id,
        "concept_b_id": concept_b_id
    }


def test_bkt_default_parameters():
    """Confirms P(L0)=0.2, P(T)=0.15, P(G)=0.2, P(S)=0.1 defaults per Hackathon specification."""
    assert bkt_engine.DEFAULT_P_INIT == 0.20, f"Expected P(L0)=0.20, got {bkt_engine.DEFAULT_P_INIT}"
    assert bkt_engine.DEFAULT_P_TRANSIT == 0.15, f"Expected P(T)=0.15, got {bkt_engine.DEFAULT_P_TRANSIT}"
    assert bkt_engine.DEFAULT_P_GUESS == 0.20, f"Expected P(G)=0.20, got {bkt_engine.DEFAULT_P_GUESS}"
    assert bkt_engine.DEFAULT_P_SLIP == 0.10, f"Expected P(S)=0.10, got {bkt_engine.DEFAULT_P_SLIP}"


def test_new_student_gets_priors(setup_test_data):
    """Verifies that a new student without prior interaction receives the default prior P(L0)=0.20."""
    student_id = f"student_{uuid.uuid4().hex[:8]}"
    course_id = setup_test_data["course_id"]
    concept_a = setup_test_data["concept_a_id"]

    record = bkt_engine.get_or_create_mastery(student_id, course_id, concept_a)
    assert record is not None
    assert record["mastery_probability"] == 0.20
    assert record["attempt_count"] == 0
    assert record["correct_count"] == 0
    assert "next_review_date" in record


def test_mastery_rises_on_correct_answers(setup_test_data):
    """Verifies that student mastery increases after correct answers."""
    student_id = f"student_{uuid.uuid4().hex[:8]}"
    course_id = setup_test_data["course_id"]
    concept_a = setup_test_data["concept_a_id"]

    initial = bkt_engine.get_or_create_mastery(student_id, course_id, concept_a)["mastery_probability"]
    assert initial == 0.20

    updated_1 = bkt_engine.update_mastery(
        student_id=student_id,
        course_id=course_id,
        concept_id=concept_a,
        is_correct=True,
        source="quiz"
    )
    p_1 = updated_1["mastery_probability"]
    assert p_1 > initial, f"Expected mastery to rise above {initial}, got {p_1}"

    updated_2 = bkt_engine.update_mastery(
        student_id=student_id,
        course_id=course_id,
        concept_id=concept_a,
        is_correct=True,
        source="quiz"
    )
    p_2 = updated_2["mastery_probability"]
    assert p_2 > p_1, f"Expected mastery to rise further above {p_1}, got {p_2}"


def test_mastery_falls_on_wrong_answers(setup_test_data):
    """Verifies that student mastery decreases after incorrect answers."""
    student_id = f"student_{uuid.uuid4().hex[:8]}"
    course_id = setup_test_data["course_id"]
    concept_a = setup_test_data["concept_a_id"]

    # Initialize to higher mastery first
    rec = bkt_engine.get_or_create_mastery(student_id, course_id, concept_a)
    rec["mastery_probability"] = 0.75
    db.update("learner_mastery", rec["id"], rec)

    updated = bkt_engine.update_mastery(
        student_id=student_id,
        course_id=course_id,
        concept_id=concept_a,
        is_correct=False,
        source="quiz"
    )
    p_after = updated["mastery_probability"]
    assert p_after < 0.75, f"Expected mastery to fall below 0.75 on incorrect answer, got {p_after}"


def test_tutor_turn_updates_with_smaller_weight(setup_test_data):
    """Confirms tutor turns apply a smaller update weight compared to quiz verification answers."""
    course_id = setup_test_data["course_id"]
    concept_a = setup_test_data["concept_a_id"]

    # Student 1 takes a quiz
    student_quiz = f"student_quiz_{uuid.uuid4().hex[:8]}"
    bkt_engine.get_or_create_mastery(student_quiz, course_id, concept_a)
    res_quiz = bkt_engine.update_mastery(
        student_id=student_quiz,
        course_id=course_id,
        concept_id=concept_a,
        is_correct=True,
        source="quiz"
    )
    delta_quiz = res_quiz["mastery_probability"] - 0.20

    # Student 2 engages in a tutor turn
    student_tutor = f"student_tutor_{uuid.uuid4().hex[:8]}"
    bkt_engine.get_or_create_mastery(student_tutor, course_id, concept_a)
    res_tutor = bkt_engine.update_mastery(
        student_id=student_tutor,
        course_id=course_id,
        concept_id=concept_a,
        is_correct=True,
        source="tutor_turn"
    )
    delta_tutor = res_tutor["mastery_probability"] - 0.20

    assert delta_tutor > 0.0, "Tutor turn should still increase mastery"
    assert delta_tutor < delta_quiz, (
        f"Tutor turn delta ({delta_tutor:.4f}) should have smaller weight than quiz delta ({delta_quiz:.4f})"
    )


def test_mastery_decays_over_time(setup_test_data):
    """Verifies Ebbinghaus forgetting curve decay over time when no practice occurs."""
    student_id = f"student_{uuid.uuid4().hex[:8]}"
    course_id = setup_test_data["course_id"]
    concept_a = setup_test_data["concept_a_id"]

    rec = bkt_engine.get_or_create_mastery(student_id, course_id, concept_a)
    rec["mastery_probability"] = 0.85
    db.update("learner_mastery", rec["id"], rec)

    # Simulate 30 days of inactivity
    decayed = bkt_engine.apply_time_decay(student_id, course_id, elapsed_days=30.0, half_life_days=30.0)
    assert len(decayed) > 0
    p_decayed = decayed[0]["mastery_probability"]
    assert p_decayed < 0.85, f"Expected mastery to decay from 0.85 over 30 days, got {p_decayed}"
    # Should decay towards baseline (0.20 + (0.85 - 0.20) * 0.5 = 0.525)
    assert 0.50 <= p_decayed <= 0.55, f"Expected ~0.525 after 1 half-life, got {p_decayed}"


def test_prerequisite_propagation_and_locking(setup_test_data):
    """Verifies that dependent concepts are locked when prerequisites are weak and unlock when prerequisites are mastered."""
    student_id = f"student_{uuid.uuid4().hex[:8]}"
    course_id = setup_test_data["course_id"]
    concept_a = setup_test_data["concept_a_id"]
    concept_b = setup_test_data["concept_b_id"]

    # Initially A has default prior 0.20 < 0.60, so B must be locked
    lock_info = bkt_engine.check_concept_locked(student_id, course_id, concept_b)
    assert lock_info["is_locked"] is True, "Concept B should be locked when prerequisite A is below 0.60"
    assert "blocking_prerequisite" in lock_info

    # Boost A above the unlock threshold (0.60)
    rec_a = bkt_engine.get_or_create_mastery(student_id, course_id, concept_a)
    rec_a["mastery_probability"] = 0.80
    db.update("learner_mastery", rec_a["id"], rec_a)

    # Prerequisite propagation
    prop_res = bkt_engine.propagate_prerequisite_mastery(student_id, course_id, concept_a)
    assert concept_b in prop_res["unlocked_concepts"]

    # Now verify B is unlocked
    lock_info_after = bkt_engine.check_concept_locked(student_id, course_id, concept_b)
    assert lock_info_after["is_locked"] is False, "Concept B should now be unlocked"


def test_calibrate_prior_knowledge_persists_to_mastery_table(setup_test_data):
    """Confirms Calibrate Prior Knowledge writes initial priors to the learner_mastery table."""
    student_id = f"student_{uuid.uuid4().hex[:8]}"
    course_id = setup_test_data["course_id"]
    concept_a = setup_test_data["concept_a_id"]
    concept_b = setup_test_data["concept_b_id"]

    res = bkt_engine.calibrate_from_intake(
        student_id=student_id,
        course_id=course_id,
        familiar_concepts=["Foundational Graph Theory"],
        experience_level="Intermediate",
        diagnostic_score_pct=65.0
    )
    assert res["status"] == "calibrated"
    assert res["concepts_calibrated"] >= 2

    # Verify directly from learner_mastery records in database
    rec_a = db.list_all("learner_mastery", lambda m: m.get("student_id") == student_id and m.get("concept_id") == concept_a)[0]
    rec_b = db.list_all("learner_mastery", lambda m: m.get("student_id") == student_id and m.get("concept_id") == concept_b)[0]

    # Familiar concept gets higher prior
    assert rec_a["mastery_probability"] == 0.72
    # Non-familiar concept gets calibrated base prior from diagnostic/intermediate
    assert 0.40 <= rec_b["mastery_probability"] <= 0.60
    assert "next_review_date" in rec_a
    assert "next_review_date" in rec_b
