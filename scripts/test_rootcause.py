import sys
import os

sys.path.insert(0, os.path.abspath("."))
from backend.app.learner.rootcause import root_cause_tracer

cid = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"
res = root_cause_tracer.diagnose_stuck("default_student", cid, target_concept_id="con_5bde266f")

print("=" * 70)
print("REAL ROOT-CAUSE DIAGNOSIS ACCEPTANCE ITEM")
print("=" * 70)
print(f"Target Concept: {res['target_concept_name']} (ID: {res['target_concept_id']})")
print(f"Root Cause Candidates: {len(res['root_causes'])}")
for rc in res["root_causes"]:
    print(f"  * {rc['concept_name']} | Depth: {rc['depth']} | p_known: {rc['p_known']} | Stuck Score: {rc['stuck_score']}")

print(f"\nEvidence List: {len(res['evidence'])} verified entries")
for ev in res["evidence"][:2]:
    print(f"  * Prereq: {ev['concept_name']} | Incorrect: {ev['incorrect_attempts']} | Score: {ev['stuck_score']}")
    print(f"    Source: {ev['source_document']} (Page/Slide {ev['source_page']})")
    print(f"    Snippet: \"{ev['source_snippet']}...\"")

print(f"\nRepair Path Plan: {len(res['repair_path'])} sequential remediation steps")
for step in res["repair_path"]:
    print(f"  Step {step['step']}: {step['concept_name']}")
    print(f"    Action: {step['action']}")
    print(f"    Micro-diagnostic Questions: {len(step['micro_diagnostic_questions'])} items")
    for q in step["micro_diagnostic_questions"][:1]:
        print(f"      Q: {q['question_text']}")
        print(f"      Correct Answer: {q['correct_answer']}")
print("=" * 70)
