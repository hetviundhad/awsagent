"""
Cleanup Script for Fake Template Artifacts.

Finds courses, concepts, and documents matching template patterns:
- Concepts: "Principle \\dA", "Mechanism \\dB", "Application \\dC"
- Documents: "Syllabus & Course Notes"
- Units: "Unit \\d+: .* - (Foundations & Core Principles|Theoretical Frameworks|Applied Methodologies)"
- Courses containing exclusively template concepts and fake syllabus documents.

Usage:
    python backend/app/scripts/cleanup_fake_templates.py            # Lists items for deletion (Dry-Run)
    python backend/app/scripts/cleanup_fake_templates.py --delete   # Deletes items (ask user first)
"""

import os
import sys
import re
import argparse

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from typing import List, Dict, Any, Set
from backend.app.services.database import db

CONCEPT_PATTERNS = [
    re.compile(r"Principle\s+\d+A", re.IGNORECASE),
    re.compile(r"Mechanism\s+\d+B", re.IGNORECASE),
    re.compile(r"Application\s+\d+C", re.IGNORECASE),
]

DOC_PATTERN = re.compile(r"Syllabus\s+&\s+Course\s+Notes", re.IGNORECASE)

def find_fake_template_artifacts():
    all_concepts = db.list_all("concepts")
    all_documents = db.list_all("documents")
    all_courses = db.list_all("courses")
    all_units = db.list_all("course_units")

    matched_concepts: List[Dict[str, Any]] = []
    for c in all_concepts:
        name = c.get("name", "")
        if any(p.search(name) for p in CONCEPT_PATTERNS):
            matched_concepts.append(c)

    matched_docs: List[Dict[str, Any]] = []
    for d in all_documents:
        fname = d.get("filename", "")
        if DOC_PATTERN.search(fname):
            matched_docs.append(d)

    # Check for courses that were generated purely via the fake template generator
    course_fake_concepts: Dict[str, int] = {}
    course_total_concepts: Dict[str, int] = {}
    for c in all_concepts:
        cid = c.get("course_id", "")
        course_total_concepts[cid] = course_total_concepts.get(cid, 0) + 1

    for c in matched_concepts:
        cid = c.get("course_id", "")
        course_fake_concepts[cid] = course_fake_concepts.get(cid, 0) + 1

    matched_courses: List[Dict[str, Any]] = []
    for crs in all_courses:
        cid = crs["id"]
        # Skip demo courses
        if cid.startswith("demo-"):
            continue
        fake_cnt = course_fake_concepts.get(cid, 0)
        tot_cnt = course_total_concepts.get(cid, 0)
        # If all or majority of concepts are fake template patterns, or title has ': Theory & Applications' with fake docs
        has_fake_doc = any(d.get("course_id") == cid for d in matched_docs)
        if (fake_cnt > 0 and fake_cnt == tot_cnt) or (has_fake_doc and fake_cnt >= 3):
            matched_courses.append({
                "course": crs,
                "fake_concepts_count": fake_cnt,
                "total_concepts_count": tot_cnt,
                "has_fake_doc": has_fake_doc
            })

    return {
        "concepts": matched_concepts,
        "documents": matched_docs,
        "courses": matched_courses
    }

def main():
    parser = argparse.ArgumentParser(description="Find or clean up fake template syllabus items.")
    parser.add_argument("--delete", action="store_true", help="Execute deletion (destructive)")
    args = parser.parse_args()

    artifacts = find_fake_template_artifacts()
    concepts = artifacts["concepts"]
    documents = artifacts["documents"]
    courses = artifacts["courses"]

    print("=" * 70)
    print("FAKE TEMPLATE ARTIFACTS AUDIT REPORT")
    print("=" * 70)
    print(f"Total Template Concepts Found:  {len(concepts)}")
    print(f"Total Fake Syllabus Docs Found: {len(documents)}")
    print(f"Total Affected Courses Found:   {len(courses)}")
    print("-" * 70)

    print("\n[MATCHED FAKE DOCUMENTS]:")
    for d in documents:
        print(f"  - Doc ID: {d['id']} | Course ID: {d.get('course_id')} | File: {d.get('filename')}")

    print("\n[MATCHED FAKE CONCEPTS (Sample)]: ")
    for c in concepts[:20]:
        print(f"  - Concept ID: {c['id']} | Course ID: {c.get('course_id')} | Name: '{c.get('name')}'")
    if len(concepts) > 20:
        print(f"    ... and {len(concepts) - 20} more concepts.")

    print("\n[AFFECTED COURSES WITH FAKE TEMPLATES]:")
    for crs_info in courses:
        crs = crs_info["course"]
        print(f"  - Course ID: {crs['id']} | Name: '{crs.get('name')}' | Owner: {crs.get('owner_id')} | Fake Concepts: {crs_info['fake_concepts_count']}/{crs_info['total_concepts_count']}")

    print("=" * 70)

    if not args.delete:
        print("\n[DRY RUN COMPLETE] No items were deleted.")
        print("To delete these items, run with --delete after obtaining user confirmation.")
        return

    print("\n[DELETION STARTED] Cleaning up fake template artifacts...")
    # 1. Delete fake concepts and their mastery/prereqs
    deleted_c_count = 0
    for c in concepts:
        cid = c["id"]
        # Delete prerequisites
        prereqs = db.list_all("concept_prerequisites", lambda p: p.get("concept_id") == cid or p.get("prerequisite_id") == cid)
        for p in prereqs:
            db.delete("concept_prerequisites", p["id"])
        # Delete learner mastery
        masteries = db.list_all("learner_mastery", lambda m: m.get("concept_id") == cid)
        for m in masteries:
            db.delete("learner_mastery", m["id"])
        # Delete concept
        db.delete("concepts", cid)
        deleted_c_count += 1

    # 2. Delete fake documents and their chunks
    deleted_d_count = 0
    for d in documents:
        did = d["id"]
        chunks = db.list_all("knowledge_chunks", lambda chk: chk.get("document_id") == did)
        for chk in chunks:
            db.delete("knowledge_chunks", chk["id"])
        db.delete("documents", did)
        deleted_d_count += 1

    # 3. Update course counts
    for crs_info in courses:
        cid = crs_info["course"]["id"]
        rem_concepts = db.list_all("concepts", lambda c: c.get("course_id") == cid)
        rem_topics = db.list_all("topics", lambda t: t.get("course_id") == cid)
        rem_docs = db.list_all("documents", lambda d: d.get("course_id") == cid)
        db.update("courses", cid, {
            "concept_count": len(rem_concepts),
            "topic_count": len(rem_topics),
            "document_count": len(rem_docs)
        })

    db.save_state()
    print(f"[DELETION COMPLETE] Deleted {deleted_c_count} fake concepts and {deleted_d_count} fake documents.")
    print("=" * 70)

if __name__ == "__main__":
    main()
