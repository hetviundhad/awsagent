import os
import sys
import uuid
import numpy as np

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.services.database import db
from backend.app.assessment.generator import assessment_engine
from backend.app.learner.bkt import bkt_engine
from backend.app.core.config import settings

def run_part5_evaluation():
    print("=" * 70)
    print("PART 5 ACCEPTANCE TEST: CONFIDENCE-CALIBRATED BKT & MISCONCEPTIONS")
    print("=" * 70)

    course_id = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"
    course = db.get_by_id("courses", course_id)
    if not course:
        print("Course not found!")
        return

    student_id = f"test_calib_student_{uuid.uuid4().hex[:6]}"

    # Step 1: Generate or pick 3 real questions on real course concepts
    concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)[:3]
    if not concepts:
        print("No concepts found in course!")
        return

    print(f"Selected Course: '{course.get('name')}' ({course_id})")
    print(f"Target Concepts: {[c.get('name') for c in concepts]}")

    # Synthesize 3 verified assessment questions
    questions = []
    chunks = db.list_all("knowledge_chunks", lambda chk: chk.get("course_id") == course_id)

    for i, c in enumerate(concepts):
        # find matching chunk
        c_chunks = [chk for chk in chunks if chk.get("concept_id") == c["id"]]
        chunk = c_chunks[0] if c_chunks else (chunks[i % len(chunks)] if chunks else {"content": c.get("description", c["name"]), "document_name": "Course Material", "concept_id": c["id"]})
        q = assessment_engine._synthesize_and_verify_question(
            course_id=course_id,
            chunk=chunk,
            existing_hashes=set(),
            difficulty="Medium",
            target_concept_id=c["id"],
            question_type="mcq"
        )
        if q:
            questions.append(q)
        else:
            # fallback synthesize
            sub_q = assessment_engine._synthesize_subject_questions(
                course_id=course_id,
                question_count=1,
                difficulty="Medium",
                concept_name=c["name"],
                concept_id=c["id"]
            )
            if sub_q:
                questions.append(sub_q[0])

    if len(questions) < 3:
        print(f"Need 3 questions, got {len(questions)}")
        return

    assessment_id = f"asst_calib_{uuid.uuid4().hex[:8]}"
    assessment_record = {
        "id": assessment_id,
        "course_id": course_id,
        "title": "Calibrated BKT Acceptance Test Quiz",
        "total_questions": len(questions),
        "difficulty": "Medium",
        "time_limit_minutes": 10,
        "status": "pending",
        "score": 0.0,
        "questions": questions,
        "created_at": "2026-10-14T15:00:00Z"
    }
    db.insert("assessments", assessment_record, save_disk=True)

    # Step 2: Formulate student answers with mixed confidence:
    # Q1: Correct with "Sure" (high confidence)
    # Q2: Incorrect with "Sure" (CONFIDENT WRONG -> Misconception penalty!)
    # Q3: Correct with "Guess" (GUESS -> discounted mastery increase)
    q1 = questions[0]
    q2 = questions[1]
    q3 = questions[2]

    # Pick wrong option for q2
    wrong_opt_q2 = [opt for opt in q2["options"] if opt.lower() != q2["correct_answer"].lower()][0]

    answers = {
        q1["id"]: q1["correct_answer"],
        q2["id"]: wrong_opt_q2,
        q3["id"]: q3["correct_answer"]
    }
    confidences = {
        q1["id"]: "Sure",
        q2["id"]: "Sure",       # Confident Error
        q3["id"]: "Guess"      # Correct Guess
    }

    print("\n--- Submitting Quiz with Confidence Ratings ---")
    for idx, q in enumerate([q1, q2, q3], 1):
        ans = answers[q["id"]]
        conf = confidences[q["id"]]
        is_corr = ans.lower() == q["correct_answer"].lower()
        print(f" Question {idx}: '{q['question_text'][:60]}...'")
        print(f"   Answer: '{ans[:40]}' (Correct: {is_corr}) | Confidence: '{conf}'")

    report = assessment_engine.evaluate_submission(
        assessment_id=assessment_id,
        student_answers=answers,
        time_spent_seconds=120,
        student_id=student_id,
        student_confidences=confidences
    )

    print("\n" + "=" * 50)
    print("SUBMISSION RESULTS:")
    print("=" * 50)
    print(f"Score: {report['score_pct']}% ({report['correct_count']}/{report['total_questions']})")
    print(f"Calibration Summary: {report['calibration']}")
    print(f"Confident Wrong Count: {report['calibration']['confident_wrong_count']}")

    print("\nMastery Shifts by Concept:")
    for c_name, shifts in report['mastery_changes'].items():
        diff = round(shifts['after'] - shifts['before'], 4)
        direction = f"+{diff}" if diff >= 0 else f"{diff}"
        print(f" - {c_name}: {shifts['before']} -> {shifts['after']} ({direction})")

    print("\nDiagnosed Misconceptions Profile:")
    for m in report['misconception_profile']:
        print(f" - Concept: {m.get('concept_name')}")
        print(f"   Misconception: {m.get('misconception')}")
        print(f"   Confident Wrong: {m.get('is_confident_wrong')}")
        print(f"   Correction Quote: \"{m.get('corrective_quote')}\"")
        if m.get('source_document'):
            print(f"   Source Citation: {m.get('source_document')}")

    # Step 3: Simulation benchmark (RMSE of Mastery estimation: Plain BKT vs Calibrated BKT)
    print("\n" + "=" * 50)
    print("SIMULATION: MASTERY ESTIMATION RMSE (PLAIN vs CALIBRATED BKT)")
    print("=" * 50)
    
    np.random.seed(42)
    n_students = 120
    n_trials = 12

    # True latent mastery distributed in [0.05, 0.95]
    true_mastery = np.random.uniform(0.1, 0.9, size=n_students)

    plain_errors = []
    calibrated_errors = []

    for s_idx in range(n_students):
        m_true = true_mastery[s_idx]
        
        p_plain = settings.BKT_P_INIT
        p_calib = settings.BKT_P_INIT

        slip = 0.10
        guess = 0.20
        p_t = settings.BKT_P_TRANSIT

        for t in range(n_trials):
            # Probability of correct answer depends on latent mastery
            p_corr_real = m_true * (1 - slip) + (1 - m_true) * guess
            is_correct = bool(np.random.rand() < p_corr_real)

            # Realistic metacognitive reporting:
            # High mastery students mostly say "Sure"
            # Low mastery students say "Guess" when guessing, but ~20% of the time hold a misconception ("Sure")
            r = np.random.rand()
            if m_true > 0.60:
                conf = "Sure" if r < 0.80 else ("Not sure" if r < 0.95 else "Guess")
            elif m_true < 0.40:
                if is_correct:
                    # Likely a lucky guess
                    conf = "Guess" if r < 0.75 else "Not sure"
                else:
                    # Incorrect: could be misconception (Sure) or knowing they don't know (Not sure / Guess)
                    conf = "Sure" if r < 0.35 else ("Not sure" if r < 0.70 else "Guess")
            else:
                conf = "Not sure" if r < 0.60 else ("Sure" if r < 0.85 else "Guess")

            # 1. Plain BKT (no confidence awareness)
            if is_correct:
                num = p_plain * (1 - slip)
                den = num + (1 - p_plain) * guess
            else:
                num = p_plain * slip
                den = num + (1 - p_plain) * (1 - guess)
            p_obs = num / den if den > 0 else p_plain
            p_plain = p_obs + (1.0 - p_obs) * p_t
            p_plain = max(0.01, min(0.99, p_plain))

            # 2. Calibrated BKT (uses metacognitive confidence)
            if is_correct:
                num_c = p_calib * (1 - slip)
                den_c = num_c + (1 - p_calib) * guess
            else:
                num_c = p_calib * slip
                den_c = num_c + (1 - p_calib) * (1 - guess)
            p_obs_c = num_c / den_c if den_c > 0 else p_calib

            p_t_eff = p_t
            if is_correct and conf == "Guess":
                # Discount lucky guess
                p_obs_c = p_calib + (p_obs_c - p_calib) * settings.BKT_CONFIDENCE_GUESS_DISCOUNT
            elif (not is_correct) and conf == "Sure":
                # Confident wrong -> misconception penalty
                p_obs_c = max(0.01, p_obs_c / settings.BKT_CONFIDENCE_WRONG_PENALTY)
                p_t_eff = p_t * 0.50

            p_calib = p_obs_c + (1.0 - p_obs_c) * p_t_eff
            p_calib = max(0.01, min(0.99, p_calib))

        plain_errors.append((p_plain - m_true) ** 2)
        calibrated_errors.append((p_calib - m_true) ** 2)

    rmse_plain = np.sqrt(np.mean(plain_errors))
    rmse_calib = np.sqrt(np.mean(calibrated_errors))
    improvement = ((rmse_plain - rmse_calib) / rmse_plain) * 100

    print(f"Plain BKT RMSE:      {round(rmse_plain, 4)}")
    print(f"Calibrated BKT RMSE: {round(rmse_calib, 4)}")
    print(f"RMSE Reduction:      {round(improvement, 2)}% ({'Calibrated BKT Wins' if rmse_calib < rmse_plain else 'Plain Wins'})")
    print("=" * 70)

if __name__ == "__main__":
    run_part5_evaluation()
