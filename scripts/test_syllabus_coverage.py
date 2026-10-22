import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')


from backend.app.services.database import db
from backend.app.services.syllabus import syllabus_auditor

def main():
    course_id = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"
    print("=== PART 4: SYLLABUS COVERAGE AUDIT ACCEPTANCE TEST ===")
    print(f"Course: {course_id}")
    
    report = syllabus_auditor.audit_coverage(course_id)
    
    print(f"\nSyllabus Document Detected: {report['syllabus_document']['name']}")
    print(f"Overall Course Coverage: {report['overall_coverage_pct']}%")
    print(f"Counts: {report['counts']['covered']} Covered, {report['counts']['thin']} Thin, {report['counts']['missing']} Missing (Total {report['counts']['total_items']} syllabus topics)")
    print(f"\n{'Unit':<8} | {'Topic Name':<42} | {'Status':<10} | {'Sources':<8} | {'Recommendation'}")
    print("-" * 110)
    for it in report['items']:
        u_str = f"Unit {it['unit_number']}"
        t_name = it['topic_name'][:40]
        status = it['status'].upper()
        sources = f"{it['supporting_chunk_count']} chunks"
        rec = it['recommendation'][:45]
        print(f"{u_str:<8} | {t_name:<42} | {status:<10} | {sources:<8} | {rec}")
        
    print("-" * 110)
    print(f"\nMissing Topics Requiring Uploads ({len(report['missing_topics'])}):")
    for mt in report['missing_topics']:
        print(f"  [MISSING] {mt}")
    print(f"\nThin Topics ({len(report['thin_topics'])}):")
    for tt in report['thin_topics']:
        print(f"  [THIN] {tt}")

if __name__ == "__main__":
    main()
