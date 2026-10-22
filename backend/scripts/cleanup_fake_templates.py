import os
import sys
import json
import re
import argparse

# Path to database JSON
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "storage")
DB_PATH = os.path.join(STORAGE_DIR, "studymind_db.json")

CONCEPT_PATTERN = re.compile(r'(Principle \d+[A-Z]|Mechanism \d+[A-Z]|Application \d+[A-Z]|Foundations & Core Principles)', re.IGNORECASE)
DOC_PATTERN = re.compile(r'(Syllabus & Course Notes|Module Notes: Unit \d+: Dsa)', re.IGNORECASE)
UNIT_PATTERN = re.compile(r'(Unit \d+:.*(Foundations & Core Principles|Theoretical Frameworks & Modeling|Applied Methodologies|Advanced Synthesis))', re.IGNORECASE)

def find_fake_records(data):
    fake_concepts = []
    fake_docs = []
    fake_units = []
    fake_chunks = []
    fake_courses = []

    # 1. Fake Concepts
    concepts = data.get("concepts", {})
    for cid, c in concepts.items():
        name = c.get("name", "")
        if CONCEPT_PATTERN.search(name):
            fake_concepts.append((cid, name, c.get("course_id")))

    fake_concept_ids = {fc[0] for fc in fake_concepts}

    # 2. Fake Documents
    docs = data.get("documents", {})
    for did, d in docs.items():
        filename = d.get("filename", "")
        if DOC_PATTERN.search(filename):
            fake_docs.append((did, filename, d.get("course_id")))

    fake_doc_ids = {fd[0] for fd in fake_docs}

    # 3. Fake Chunks belonging to fake docs or fake concepts
    chunks = data.get("knowledge_chunks", {})
    for chkid, chk in chunks.items():
        if chk.get("document_id") in fake_doc_ids:
            fake_chunks.append(chkid)
        elif any(cid in fake_concept_ids for cid in chk.get("concept_ids", [])):
            fake_chunks.append(chkid)

    # 4. Fake Course Units
    units = data.get("course_units", {})
    for uid, u in units.items():
        title = u.get("title", "")
        if UNIT_PATTERN.search(title):
            fake_units.append((uid, title, u.get("course_id")))

    # 5. Courses with only fake units/docs
    courses = data.get("courses", {})
    for cid, c in courses.items():
        c_docs = [d for d in docs.values() if d.get("course_id") == cid]
        real_docs = [d for d in c_docs if d["id"] not in fake_doc_ids]
        if c_docs and not real_docs:
            fake_courses.append((cid, c.get("name", "")))

    return {
        "concepts": fake_concepts,
        "documents": fake_docs,
        "units": fake_units,
        "chunks": fake_chunks,
        "courses": fake_courses
    }

def main():
    parser = argparse.ArgumentParser(description="Find and optionally clean fake syllabus template artifacts.")
    parser.add_argument("--execute", action="store_true", help="Actually delete the records (requires prior confirmation).")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"Database file not found at: {DB_PATH}")
        sys.exit(1)

    with open(DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = find_fake_records(data)

    print("=" * 60)
    print("StudyMind AI - Template Cleanup Scan Results")
    print("=" * 60)
    print(f"Fake Concepts found:     {len(records['concepts'])}")
    print(f"Fake Documents found:    {len(records['documents'])}")
    print(f"Fake Units found:        {len(records['units'])}")
    print(f"Fake Chunks found:       {len(records['chunks'])}")
    print(f"Template-only Courses:   {len(records['courses'])}")
    print("-" * 60)

    if records["courses"]:
        print("\nTemplate-only Courses listed for deletion:")
        for cid, cname in records["courses"]:
            print(f"  • [{cid[:8]}] {cname}")

    if records["documents"]:
        print("\nSample Fake Documents listed for deletion (first 10):")
        for did, dname, cid in records["documents"][:10]:
            print(f"  • [{did[:8]}] {dname} (Course: {cid[:8] if cid else 'N/A'})")

    if records["concepts"]:
        print("\nSample Fake Concepts listed for deletion (first 10):")
        for cid, cname, course_id in records["concepts"][:10]:
            print(f"  • [{cid[:8]}] {cname}")

    print("\n" + "=" * 60)

    if not args.execute:
        print("DRY-RUN COMPLETE. No data was deleted.")
        print("To execute deletion, run with: python backend/scripts/cleanup_fake_templates.py --execute")
        return

    # Execution path
    print("Executing deletion of identified template artifacts...")
    fake_concept_ids = {fc[0] for fc in records["concepts"]}
    fake_doc_ids = {fd[0] for fd in records["documents"]}
    fake_unit_ids = {fu[0] for fu in records["units"]}
    fake_chunk_ids = set(records["chunks"])
    fake_course_ids = {fc[0] for fc in records["courses"]}

    for cid in fake_concept_ids:
        data["concepts"].pop(cid, None)
    for did in fake_doc_ids:
        data["documents"].pop(did, None)
    for uid in fake_unit_ids:
        data["course_units"].pop(uid, None)
    for chkid in fake_chunk_ids:
        data["knowledge_chunks"].pop(chkid, None)
    for cid in fake_course_ids:
        data["courses"].pop(cid, None)

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("Cleanup completed successfully and state persisted.")

if __name__ == "__main__":
    main()
