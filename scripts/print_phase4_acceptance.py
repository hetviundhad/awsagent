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

from backend.app.evaluation.simulator import synthetic_simulator
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

    concepts = db.list_all("concepts", lambda c: c.get("course_id") == TARGET_COURSE_ID)
    prereqs = db.list_all("concept_prerequisites", lambda p: p.get("course_id") == TARGET_COURSE_ID)

    print("=" * 80, flush=True)
    print("STUDYMIND AI — PHASE 4 ACCEPTANCE REPORT: MULTI-DIMENSIONAL LEARNER MODEL", flush=True)
    print(f"Course: {course.get('name')} (ID: {TARGET_COURSE_ID})", flush=True)
    print(f"Total Real Concepts: {len(concepts)} | Prerequisite Edges: {len(prereqs)}", flush=True)
    print(f"BKT Unlock Threshold: {settings.BKT_UNLOCK_THRESHOLD} | Forgetting Rate: {settings.BKT_FORGETTING_RATE}", flush=True)
    print("=" * 80, flush=True)

    # 1. Ten-Session Multi-Persona Simulation
    print_separator("1. TEN-SESSION SYNTHETIC STUDENT SIMULATION (3 DIVERGENT PERSONAS)")
    print(f"Running 10-session longitudinal simulation across real course concepts...", flush=True)
    sim_results = synthetic_simulator.run_simulation(TARGET_COURSE_ID)

    curve = sim_results.get("comparison_curve", [])
    print("\nTrajectory Comparison Table across 10 Sequential Sessions:")
    print(f"{'Session':<8} | {'Fast Learner':<16} | {'Struggles with Math':<20} | {'Skips Lectures':<16}")
    print("-" * 70)
    for pt in curve:
        s = pt.get("session", "")
        fl = f"{pt.get('fast_learner', 0.0)}%"
        sm = f"{pt.get('struggles_math', 0.0)}%"
        sl = f"{pt.get('skips_lectures', 0.0)}%"
        print(f"{s:<8} | {fl:<16} | {sm:<20} | {sl:<16}")

    # 2. Persona Outcome & Pedagogical Proof
    print_separator("2. DIVERGENT PERSONA OUTCOMES & CONCEPT UNLOCK GATING")
    proofs = sim_results.get("personalization_proof", [])
    for proof in proofs:
        p_name = proof.get("persona")
        init_m = proof.get("initial_mastery")
        fin_m = proof.get("final_mastery")
        unlocked = proof.get("concepts_unlocked")
        rec = proof.get("distinct_recommendation")
        reason = proof.get("pedagogical_reason")
        print(f"Persona: {p_name} ({proof.get('avatar')})")
        print(f"  Mastery Progress:    {init_m} -> {fin_m}")
        print(f"  Concepts Unlocked:   {unlocked}")
        print(f"  Target Recommendation: {rec}")
        print(f"  Pedagogical Rationale: {reason}")
        print("-" * 60)

    # 3. Prerequisite Gating Verification on Real Graph Nodes
    print_separator("3. PREREQUISITE LOCKING & GATING LOGIC VERIFICATION")
    # Test concept locking logic for a brand new student and an advanced student
    test_student_locked = f"test_student_locked_{uuid.uuid4().hex[:6]}"
    test_student_unlocked = f"test_student_unlocked_{uuid.uuid4().hex[:6]}"

    # Find a concept with prerequisites
    target_edge = prereqs[0] if prereqs else None
    if target_edge:
        dependent_id = target_edge.get("concept_id")
        prereq_id = target_edge.get("prerequisite_id")
        dependent_concept = db.get_by_id("concepts", dependent_id) or {"name": "Dependent Concept"}
        prereq_concept = db.get_by_id("concepts", prereq_id) or {"name": "Prerequisite Concept"}

        print(f"Inspecting Dependency Edge:")
        print(f"  Prerequisite: '{prereq_concept.get('name')}' (ID: {prereq_id})")
        print(f"  Dependent:    '{dependent_concept.get('name')}' (ID: {dependent_id})")

        # Simulate student who failed prerequisite multiple times (< 0.70 threshold)
        p_rec = bkt_engine.get_or_create_mastery(test_student_locked, TARGET_COURSE_ID, prereq_id)
        p_rec["mastery_probability"] = 0.35
        p_rec["attempt_count"] = 4
        db.update("learner_mastery", p_rec["id"], p_rec, save_disk=False)

        lock_status = bkt_engine.check_concept_locked(test_student_locked, TARGET_COURSE_ID, dependent_id)
        print(f"\nStudent A (Failed prerequisite, mastery=35%, attempts=4):")
        print(f"  Concept Locked:     {lock_status.get('is_locked')}")
        print(f"  Lock Reason:        {lock_status.get('lock_reason')}")
        print(f"  Missing Prereqs:    {len(lock_status.get('missing_prerequisites', []))}")

        # Simulate student who mastered prerequisite (>= 0.70 threshold)
        p_rec_unlocked = bkt_engine.get_or_create_mastery(test_student_unlocked, TARGET_COURSE_ID, prereq_id)
        p_rec_unlocked["mastery_probability"] = 0.88
        p_rec_unlocked["attempt_count"] = 5
        db.update("learner_mastery", p_rec_unlocked["id"], p_rec_unlocked, save_disk=False)

        unlock_status = bkt_engine.check_concept_locked(test_student_unlocked, TARGET_COURSE_ID, dependent_id)
        print(f"\nStudent B (Mastered prerequisite, mastery=88%, attempts=5):")
        print(f"  Concept Locked:     {unlock_status.get('is_locked')}")
        print(f"  Lock Reason:        {unlock_status.get('lock_reason')}")

    # 4. Ebbinghaus Forgetting Curve / BKT Time Decay Demonstration
    print_separator("4. EBBINGHAUS FORGETTING CURVE / BKT TIME DECAY")
    decay_student = f"test_decay_student_{uuid.uuid4().hex[:6]}"
    sample_concept = concepts[0]
    
    # Create baseline mastery of 0.85
    m_baseline = bkt_engine.get_or_create_mastery(decay_student, TARGET_COURSE_ID, sample_concept["id"])
    m_baseline["mastery_probability"] = 0.85
    db.update("learner_mastery", m_baseline["id"], m_baseline, save_disk=False)

    print(f"Baseline Concept: '{sample_concept.get('name')}'")
    print(f"Initial Mastery: 0.85 (85.0%)\n")
    print(f"{'Elapsed Time':<15} | {'Mastery Prob':<15} | {'Decay Amount':<15} | {'Next Review Date':<25}")
    print("-" * 75)

    for elapsed_days in [1.0, 3.0, 7.0, 14.0, 30.0]:
        # Reset to 0.85 to measure exact decay at each horizon
        m_baseline["mastery_probability"] = 0.85
        db.update("learner_mastery", m_baseline["id"], m_baseline, save_disk=False)
        
        decayed = bkt_engine.apply_time_decay(decay_student, TARGET_COURSE_ID, elapsed_days=elapsed_days)
        if decayed:
            p_decayed = decayed[0]["mastery_probability"]
            drop = round(0.85 - p_decayed, 4)
            n_rev = str(decayed[0].get("next_review_date", ""))[:19]
            print(f"{f'{elapsed_days} days':<15} | {p_decayed:<15.4f} | {f'-{drop:.4f}':<15} | {n_rev:<25}")

    # 5. Question Repetition Guarantee
    print_separator("5. QUESTION REPETITION RATE")
    print(f"Longitudinal repetition rate: {sim_results.get('question_repetition_rate_pct', '0.0%')}")
    print(f"Proof: {sim_results.get('question_repetition_explanation')}")

if __name__ == "__main__":
    main()
