import os
import sys
import json
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.app.core.config import settings
from backend.app.services.database import db

# Suppress remote supabase sync for acceptance script
db.supabase_client = None
db._push_to_supabase = lambda *args, **kwargs: None

from backend.app.assessment.generator import assessment_engine
from backend.app.learner.bkt import bkt_engine

TARGET_COURSE_ID = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"

def print_separator(title: str):
    print("\n" + "=" * 80, flush=True)
    print(f" {title}", flush=True)
    print("=" * 80, flush=True)

def main():
    course = db.get_by_id("courses", TARGET_COURSE_ID)
    if not course:
        print(f"ERROR: Course {TARGET_COURSE_ID} not found in database.", flush=True)
        sys.exit(1)

    print("=" * 80, flush=True)
    print("STUDYMIND AI — PHASE 3 ACCEPTANCE REPORT: ADAPTIVE ASSESSMENT", flush=True)
    print(f"Course: {course.get('name')} (ID: {TARGET_COURSE_ID})", flush=True)
    print(f"Critic Model: {settings.LLM_MODEL_CRITIC} | Extractor Model: {settings.LLM_MODEL_EXTRACT}", flush=True)
    print("=" * 80, flush=True)

    # 1. Five-Question Quiz Generation with Grounding & Independent Validation
    print_separator("1. FIVE-QUESTION ADAPTIVE QUIZ GENERATION ON REAL COURSE")
    quiz = assessment_engine.generate_assessment(
        course_id=TARGET_COURSE_ID,
        question_count=5,
        difficulty="Adaptive",
        student_id="student_phase3_acceptance_lead"
    )

    questions = quiz.get("questions", [])
    print(f"Generated {len(questions)} verified questions for assessment ID: {quiz['id']}\n", flush=True)

    for idx, q in enumerate(questions, 1):
        print(f"Q{idx} [{q.get('difficulty', 'Medium')} | {q.get('question_type', 'mcq').upper()}]: {q.get('question_text')}", flush=True)
        options = q.get("options", [])
        for o in options:
            marker = " [CORRECT]" if o.strip().lower() == q.get("correct_answer", "").strip().lower() else ""
            print(f"    - {o}{marker}", flush=True)
        print(f"  Supporting Quote: \"{q.get('supporting_quote', 'N/A')[:100]}...\"", flush=True)
        print(f"  Source Document:  {q.get('source_document', 'N/A')} ({q.get('source_location', 'N/A')})", flush=True)
        print(f"  Concept Tag:      {q.get('concept_id', 'N/A')}", flush=True)
        print(f"  Verified Status:  {q.get('verification_status')} (Verified={q.get('verified', True)})", flush=True)
        print(f"  Verification:     {q.get('verification', q.get('verification_details', {}))}", flush=True)
        print(f"  Distractor Rationale: {q.get('distractor_rationale', {})}", flush=True)
        print("-" * 60, flush=True)

    # 2. Ten Consecutive Quizzes for One Student - Repetition & Novelty Rate
    print_separator("2. TEN CONSECUTIVE QUIZZES FOR 1 STUDENT (DEDUPLICATION & REPETITION)")
    student_id = f"student_ten_quizzes_{uuid.uuid4().hex[:6]}"
    seen_hashes = set()
    total_generated = 0
    duplicate_count = 0

    print("Simulating 10 consecutive quizzes with attempt history tracking...", flush=True)
    all_course_qs = db.list_all("questions", lambda q: q.get("course_id") == TARGET_COURSE_ID)
    
    for q_round in range(1, 11):
        # Student requests quiz, engine filters out attempted_hashes
        assessment = assessment_engine.generate_assessment(
            course_id=TARGET_COURSE_ID,
            question_count=1,
            difficulty="Adaptive",
            student_id=student_id
        )
        round_qs = assessment.get("questions", [])
        for q in round_qs:
            total_generated += 1
            h = q.get("question_hash")
            if h in seen_hashes:
                duplicate_count += 1
            else:
                seen_hashes.add(h)
                
            # Student submits attempt, recording question_hash so engine avoids repeats
            db.insert("attempts", {
                "id": str(uuid.uuid4()),
                "user_id": student_id,
                "assessment_id": assessment["id"],
                "question_id": q["id"],
                "question_hash": h,
                "is_correct": True
            })

        print(f"  Quiz {q_round:2d}: {len(round_qs)} questions selected | Unique hashes seen: {len(seen_hashes)} | Duplicates: {duplicate_count}", flush=True)

    rep_rate = round(duplicate_count / max(total_generated, 1), 4)
    print(f"\nTotal Questions Tested across 10 Quizzes: {total_generated}", flush=True)
    print(f"Duplicate Questions Encountered:        {duplicate_count}", flush=True)
    print(f"Repetition Rate:                        {rep_rate * 100:.2f}% (Target: 0.0%)", flush=True)

    # 3. Assessment Submission with Misconception Detection & Remediation
    print_separator("3. ASSESSMENT SUBMISSION, MISCONCEPTION DETECTION & REMEDIATION")
    if questions:
        # Deliberately submit 1 incorrect answer to test misconception detection
        first_q = questions[0]
        wrong_opt = None
        for opt in first_q.get("options", []):
            if opt.strip().lower() != first_q.get("correct_answer", "").strip().lower():
                wrong_opt = opt
                break
        if not wrong_opt:
            wrong_opt = "Deliberately wrong choice regarding MapReduce partitioning"

        answers = {first_q["id"]: wrong_opt}
        if len(questions) > 1:
            answers[questions[1]["id"]] = questions[1]["correct_answer"]

        submission_result = assessment_engine.evaluate_submission(
            assessment_id=quiz["id"],
            student_answers=answers,
            time_spent_seconds=120,
            student_id=student_id
        )

        print(f"Assessment Submitted: Score = {submission_result.get('score_pct')}% | Passed = {submission_result.get('passed')}", flush=True)
        print(f"Correct Answers:     {submission_result.get('correct_count')} / {submission_result.get('total_questions')}", flush=True)
        print(f"Detected Misconceptions ({len(submission_result.get('detected_misconceptions', []))}):", flush=True)
        for m in submission_result.get("detected_misconceptions", []):
            print(f"  • {m}", flush=True)

        # Check remediation: Flashcards and Audio Brief
        if submission_result.get("detected_misconceptions"):
            sample_misc = submission_result["detected_misconceptions"][0]
            print("\nGenerating Targeted Misconception Remediation:", flush=True)
            brief = assessment_engine.generate_misconception_brief(sample_misc, "Big Data Architecture")
            print(f"  Audio Brief ({brief.get('duration_seconds')}s):", flush=True)
            print(f"  \"{brief.get('script', '')[:200]}...\"", flush=True)

            flashcards = assessment_engine.generate_misconception_flashcards(sample_misc, "Big Data Architecture")
            print(f"\n  Targeted Flashcards ({len(flashcards)} generated):", flush=True)
            for fc in flashcards[:2]:
                print(f"    Front: {fc.get('front')}", flush=True)
                print(f"    Back:  {fc.get('back')}", flush=True)

    # 4. Cross-Model Validation Engine Discard Statistics
    print_separator("4. VALIDATION ENGINE DISCARD METRICS")
    val_stats = assessment_engine.get_validation_metrics()
    print(f"Total Questions Evaluated by Validation Pipeline: {val_stats.get('total_evaluated')}", flush=True)
    print(f"Questions Passed All Verification Stages:         {val_stats.get('validated_passed')}", flush=True)
    print(f"Questions Discarded (Quote, SymPy, Solver, Dedup): {val_stats.get('discarded_count')}", flush=True)
    print(f"Discard Rate:                                     {val_stats.get('discard_rate_percentage')}%", flush=True)

if __name__ == "__main__":
    main()
