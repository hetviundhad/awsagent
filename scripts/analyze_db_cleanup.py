import json
import os
import glob
from collections import Counter

DB_PATH = "backend/data/storage/studymind_db.json"
STORAGE_DIR = "backend/data/storage"

TEST_COURSE_NAMES = {
    "Adaptive Learning Systems",
    "Marine Biology & Coral Ecology",
    "Cellular Biology 101",
    "General Biology",
    "Modern European History",
    "YouTube Test Course"
}

def analyze():
    if not os.path.exists(DB_PATH):
        print("DB file not found!")
        return

    with open(DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    courses = data.get("courses", {})
    documents = data.get("documents", {})
    units = data.get("course_units", {})
    topics = data.get("topics", {})
    concepts = data.get("concepts", {})
    chunks = data.get("knowledge_chunks", {})
    questions = data.get("questions", {})
    attempts = data.get("attempts", {})

    # Distinct owner_ids
    owner_counts = Counter()
    owner_courses = {}
    for cid, c in courses.items():
        oid = c.get("owner_id")
        owner_str = str(oid) if oid is not None else "None"
        owner_counts[owner_str] += 1
        owner_courses.setdefault(owner_str, []).append((cid, c.get("name", "")))

    print("==================================================")
    print("DISTINCT OWNER IDs WITH COURSE COUNTS:")
    for oid, count in owner_counts.most_common():
        print(f"  Owner ID: {oid} -> {count} course(s)")
        for cid, name in owner_courses[oid][:3]:
            print(f"     - [{cid[:8]}] {name}")
    print("==================================================")

    # 1. Courses with owner_id None or starting with usr_demo / test_
    flagged_owner_courses = {}
    for cid, c in courses.items():
        oid = c.get("owner_id")
        if oid is None or str(oid).startswith("usr_demo") or str(oid).startswith("test_"):
            flagged_owner_courses[cid] = c

    # 2. Courses with test names
    flagged_test_name_courses = {}
    for cid, c in courses.items():
        cname = c.get("name", "")
        if cname in TEST_COURSE_NAMES or any(tn.lower() in cname.lower() for tn in TEST_COURSE_NAMES):
            flagged_test_name_courses[cid] = c

    # 3. Courses named "... : Theory & Applications" with no real documents
    flagged_theory_app_courses = {}
    for cid, c in courses.items():
        cname = c.get("name", "")
        if "Theory & Applications" in cname or "theory & applications" in cname.lower():
            # Check if has real documents
            course_docs = [d for d in documents.values() if d.get("course_id") == cid]
            if not course_docs:
                flagged_theory_app_courses[cid] = c

    # All candidate courses to delete under test/synthetic criteria
    candidate_cids_to_remove = set(flagged_owner_courses.keys()) | set(flagged_test_name_courses.keys()) | set(flagged_theory_app_courses.keys())

    # Check orphan child records (records pointing to nonexistent or deleted courses)
    all_course_ids = set(courses.keys())
    
    # Existing orphan counts right now (course_id not in courses)
    current_orphan_units = [uid for uid, u in units.items() if u.get("course_id") not in all_course_ids]
    current_orphan_topics = [tid for tid, t in topics.items() if t.get("course_id") not in all_course_ids]
    current_orphan_concepts = [cid for cid, co in concepts.items() if co.get("course_id") not in all_course_ids]
    current_orphan_chunks = [chid for chid, ch in chunks.items() if ch.get("course_id") not in all_course_ids]
    current_orphan_attempts = [aid for aid, a in attempts.items() if a.get("course_id") not in all_course_ids]
    current_orphan_docs = [did for did, d in documents.items() if d.get("course_id") not in all_course_ids]

    # Extra files in storage directory
    extra_files = []
    for fpath in glob.glob(os.path.join(STORAGE_DIR, "*")):
        fname = os.path.basename(fpath)
        if (".bak" in fname or ".tmp_" in fname) and fname != "studymind_db.json":
            extra_files.append((fname, os.path.getsize(fpath)))

    print("\n--- DRY-RUN SUMMARY ---")
    print(f"Total courses currently: {len(courses)}")
    print(f"Total documents currently: {len(documents)}")
    print(f"Total course_units currently: {len(units)}")
    print(f"Total topics currently: {len(topics)}")
    print(f"Total concepts currently: {len(concepts)}")
    print(f"Total knowledge_chunks currently: {len(chunks)}")
    print(f"Total questions currently: {len(questions)}")
    print(f"Total attempts currently: {len(attempts)}")

    print(f"\nFlagged courses by criteria:")
    print(f"  - owner_id None or usr_demo / test_: {len(flagged_owner_courses)}")
    print(f"  - Test course names: {len(flagged_test_name_courses)}")
    print(f"  - '... Theory & Applications' with no documents: {len(flagged_theory_app_courses)}")
    print(f"  - Unique total flagged courses: {len(candidate_cids_to_remove)}")

    print(f"\nCurrent orphan records (course_id missing from courses):")
    print(f"  - Orphan units: {len(current_orphan_units)}")
    print(f"  - Orphan topics: {len(current_orphan_topics)}")
    print(f"  - Orphan concepts: {len(current_orphan_concepts)}")
    print(f"  - Orphan chunks: {len(current_orphan_chunks)}")
    print(f"  - Orphan documents: {len(current_orphan_docs)}")
    print(f"  - Orphan attempts: {len(current_orphan_attempts)}")

    print(f"\nExtra backup and temporary files in storage:")
    for fname, fsize in extra_files:
        print(f"  - {fname} ({fsize / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    analyze()
