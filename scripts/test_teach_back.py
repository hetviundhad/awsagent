import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.database import db
from backend.app.services.teach_back import teach_back_evaluator

def main():
    course_id = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"
    student_id = "demo_student"
    
    # Pick a real concept from course
    concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
    target_concept = None
    for c in concepts:
        if "locality" in c.get("name", "").lower() or "parallel" in c.get("name", "").lower():
            target_concept = c
            break
    if not target_concept and concepts:
        target_concept = concepts[0]
        
    print(f"=== PART 3: TEACH-BACK MODE ACCEPTANCE TEST ===")
    print(f"Course: {course_id}")
    print(f"Target Concept: {target_concept['name']} (ID: {target_concept['id']})")
    
    # 1. Good Explanation matching course document
    good_explanation = (
        f"Partition placement is the strategy for deciding which physical nodes store each data partition and its replicas. "
        f"In distributed storage systems, HDFS Rack Awareness is the algorithmic policy used to intelligently distribute data blocks across physical server racks. "
        f"This balances the conflicting priorities of data reliability against hardware failures with network performance for write speeds."
    )

    print("\n" + "="*50)
    print("1. RUNNING HIGH-QUALITY STUDENT EXPLANATION:")
    print("Explanation:", good_explanation)
    res_good = teach_back_evaluator.evaluate_teach_back(
        student_id=student_id,
        course_id=course_id,
        concept_id=target_concept["id"],
        explanation_text=good_explanation
    )
    print(f"Overall Score: {res_good['overall_score']}% (Passed: {res_good['is_passed']})")
    print(f"Correct Claims ({len(res_good['correct_claims'])}):")
    for cc in res_good['correct_claims']:
        print(f"  [+] {cc['claim']} (Verified from {cc['supporting_doc']} p.{cc['page_number']})")
    print(f"Flawed/Unsupported Claims ({len(res_good['wrong_claims'])}):")
    for wc in res_good['wrong_claims']:
        print(f"  [-] {wc['claim']} -> Citation: {wc['correcting_citation']}")
    print(f"Missing Key Points: {res_good['missing_key_points']}")
    print(f"BKT Change: P(L) {res_good['bkt_update']['before_probability']} -> {res_good['bkt_update']['after_probability']} (Gain: {res_good['bkt_update']['mastery_gain']:+0.3f})")
    print(f"Feedback: {res_good['feedback']}")

    # 2. Flawed Explanation
    flawed_explanation = (
        f"Data locality requires all distributed datasets to be sent over the switch to the client browser before computing. "
        f"It completely ignores node architecture and transfers 100 gigabytes over network routers for every single map task."
    )
    print("\n" + "="*50)
    print("2. RUNNING FLAWED STUDENT EXPLANATION (MISCONCEPTIONS):")
    print("Explanation:", flawed_explanation)
    res_bad = teach_back_evaluator.evaluate_teach_back(
        student_id=student_id,
        course_id=course_id,
        concept_id=target_concept["id"],
        explanation_text=flawed_explanation
    )
    print(f"Overall Score: {res_bad['overall_score']}% (Passed: {res_bad['is_passed']})")
    print(f"Correct Claims ({len(res_bad['correct_claims'])}):")
    for cc in res_bad['correct_claims']:
        print(f"  [+] {cc['claim']} (Verified from {cc['supporting_doc']} p.{cc['page_number']})")
    print(f"Flawed/Unsupported Claims ({len(res_bad['wrong_claims'])}):")
    for wc in res_bad['wrong_claims']:
        print(f"  [-] {wc['claim']}")
        print(f"      Correction: {wc['correcting_citation']['corrective_fact']} (Source: {wc['correcting_citation']['document_name']} p.{wc['correcting_citation']['page_number']})")
    print(f"Missing Key Points: {res_bad['missing_key_points']}")
    print(f"BKT Change: P(L) {res_bad['bkt_update']['before_probability']} -> {res_bad['bkt_update']['after_probability']} (Gain: {res_bad['bkt_update']['mastery_gain']:+0.3f})")
    print(f"Feedback: {res_bad['feedback']}")
    print("="*50)

if __name__ == "__main__":
    main()
