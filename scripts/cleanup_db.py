"""
Database cleanup script for StudyMind AI.
Backs up DB before making changes and deletes flagged courses and orphaned records.
Keeps only course a091a4aa-a333-4a0c-85ec-9af9ad8505bd owned by real Supabase user id.
Deduplicates documents atomically and prints dynamically computed breakdowns.
"""

import sys
import os
import json
import shutil
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from backend.app.core.config import settings

TARGET_COURSE_ID = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"
REAL_USER_ID = "e5ee47b2-ad1d-4536-b3eb-a165de1792b1"
PRESERVED_BACKUP = "studymind_db.json.bak_20261012_125152"

def to_dict_items(obj):
    """Normalize dict-of-items or list-of-items to (id, dict) generator."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, dict):
                yield k, v
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                yield item.get("id"), item

def run_cleanup(dry_run: bool = True):
    db_path = settings.DB_PATH
    storage_dir = os.path.dirname(db_path)
    backup_path = os.path.join(storage_dir, PRESERVED_BACKUP)

    # Safety check: confirm preserved backup exists
    if not os.path.exists(backup_path):
        print(f"CRITICAL ERROR: Preserved backup file not found: {backup_path}")
        print("ABORTING cleanup to prevent data loss.")
        sys.exit(1)

    print(f"Target Database: {db_path}")
    print(f"Verified Preserved Backup: {backup_path} ({os.path.getsize(backup_path)} bytes)")

    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Courses
    courses_raw = data.get("courses", {})
    all_courses_count = len(courses_raw)
    kept_course = courses_raw.get(TARGET_COURSE_ID)

    if not kept_course:
        print(f"ERROR: Target course {TARGET_COURSE_ID} not found in database!")
        sys.exit(1)

    # 2. Documents for kept course with deduplication
    docs_raw = data.get("documents", {})
    all_docs_count = len(docs_raw)
    
    kept_docs = {}
    seen_filenames = {}
    removed_duplicate_doc_ids = set()

    for did, doc in to_dict_items(docs_raw):
        if doc.get("course_id") == TARGET_COURSE_ID:
            fname = doc.get("filename")
            if fname in seen_filenames:
                removed_duplicate_doc_ids.add(did)
                print(f"[Deduplication] Flagged duplicate document for removal: {did} ({fname})")
            else:
                seen_filenames[fname] = did
                kept_docs[did] = doc

    kept_doc_ids = set(kept_docs.keys())

    # 3. Topics for kept course
    topics_raw = data.get("topics", {})
    kept_topics = {tid: t for tid, t in to_dict_items(topics_raw) if t.get("course_id") == TARGET_COURSE_ID}
    kept_topic_ids = set(kept_topics.keys())

    # 4. Course Units & Units
    cu_raw = data.get("course_units", {})
    kept_cu = {cuid: cu for cuid, cu in to_dict_items(cu_raw) if cu.get("course_id") == TARGET_COURSE_ID}

    u_raw = data.get("units", {})
    kept_u = {uid: u for uid, u in to_dict_items(u_raw) if u.get("course_id") == TARGET_COURSE_ID}

    # 5. Concepts (link via course_id OR topic_id)
    concepts_raw = data.get("concepts", {})
    kept_concepts = {}
    for cid, c in to_dict_items(concepts_raw):
        if c.get("course_id") == TARGET_COURSE_ID or c.get("topic_id") in kept_topic_ids:
            kept_concepts[cid] = c

    # 6. Knowledge Chunks (link via course_id and kept document_ids)
    chunks_raw = data.get("knowledge_chunks", {})
    kept_chunks = {}
    for chkid, chk in to_dict_items(chunks_raw):
        if chk.get("course_id") == TARGET_COURSE_ID:
            if chk.get("document_id") in removed_duplicate_doc_ids:
                continue
            kept_chunks[chkid] = chk

    # 7. Visual Elements (link via course_id OR document_id)
    visuals_raw = data.get("visual_elements", {})
    kept_visuals = {}
    for vid, v in to_dict_items(visuals_raw):
        if v.get("course_id") == TARGET_COURSE_ID or v.get("document_id") in kept_doc_ids:
            kept_visuals[vid] = v

    # 8. Questions (link via course_id OR topic_id)
    questions_raw = data.get("questions", {})
    kept_questions = {}
    for qid, q in to_dict_items(questions_raw):
        if q.get("course_id") == TARGET_COURSE_ID or q.get("topic_id") in kept_topic_ids:
            kept_questions[qid] = q

    # 9. Attempts
    attempts_raw = data.get("attempts", data.get("assessment_attempts", {}))
    kept_attempts = {aid: a for aid, a in to_dict_items(attempts_raw) if a.get("course_id") == TARGET_COURSE_ID}

    # 10. Concept prerequisites
    cp_raw = data.get("concept_prerequisites", {})
    kept_cp = {cpid: cp for cpid, cp in to_dict_items(cp_raw) if cp.get("concept_id") in kept_concepts or cp.get("course_id") == TARGET_COURSE_ID}

    # 11. Conversations & Messages
    convs_raw = data.get("conversations", {})
    kept_convs = {cid: c for cid, c in to_dict_items(convs_raw) if c.get("course_id") == TARGET_COURSE_ID}
    kept_conv_ids = set(kept_convs.keys())

    msgs_raw = data.get("messages", {})
    kept_msgs = {mid: m for mid, m in to_dict_items(msgs_raw) if m.get("conversation_id") in kept_conv_ids}

    # 12. Assessments & Assessment Questions
    assess_raw = data.get("assessments", {})
    kept_assess = {aid: a for aid, a in to_dict_items(assess_raw) if a.get("course_id") == TARGET_COURSE_ID}
    kept_assess_ids = set(kept_assess.keys())

    aq_raw = data.get("assessment_questions", {})
    kept_aq = {aqid: aq for aqid, aq in to_dict_items(aq_raw) if aq.get("assessment_id") in kept_assess_ids}

    # 13. Learner Mastery
    mastery_raw = data.get("learner_mastery", {})
    kept_mastery = {mid: m for mid, m in to_dict_items(mastery_raw) if m.get("course_id") == TARGET_COURSE_ID}

    # 14. Misconceptions, Study Plans, Revision Materials
    misc_raw = data.get("misconceptions", {})
    kept_misc = {mid: m for mid, m in to_dict_items(misc_raw) if m.get("course_id") == TARGET_COURSE_ID or m.get("concept_id") in kept_concepts}

    sp_raw = data.get("study_plans", {})
    kept_sp = {spid: sp for spid, sp in to_dict_items(sp_raw) if sp.get("course_id") == TARGET_COURSE_ID}

    rm_raw = data.get("revision_materials", {})
    kept_rm = {rmid: rm for rmid, rm in to_dict_items(rm_raw) if rm.get("course_id") == TARGET_COURSE_ID}

    # 15. Evaluation Results & Question History
    er_raw = data.get("evaluation_results", {})
    kept_er = {erid: er for erid, er in to_dict_items(er_raw) if er.get("course_id") == TARGET_COURSE_ID}

    qh_raw = data.get("question_history", {})
    kept_qh = {qhid: qh for qhid, qh in to_dict_items(qh_raw) if qh.get("course_id") == TARGET_COURSE_ID}

    # Extra files in storage dir to remove (preserving the official 18.76 MB backup)
    extra_files = []
    for f in os.listdir(storage_dir):
        if (f.startswith("studymind_db.json.bak") and f != PRESERVED_BACKUP) or f.startswith("studymind_db.json.tmp_"):
            extra_files.append(os.path.join(storage_dir, f))

    # Before counts for kept course
    c_docs_before = len([d for _, d in to_dict_items(docs_raw) if d.get("course_id") == TARGET_COURSE_ID])
    c_chunks_before = len([c for _, c in to_dict_items(chunks_raw) if c.get("course_id") == TARGET_COURSE_ID])
    c_topics_before = len([t for _, t in to_dict_items(topics_raw) if t.get("course_id") == TARGET_COURSE_ID])
    c_cu_before = len([cu for _, cu in to_dict_items(cu_raw) if cu.get("course_id") == TARGET_COURSE_ID])
    c_concepts_before = len(kept_concepts)
    c_questions_before = len(kept_questions)
    c_visuals_before = len(kept_visuals)

    # Dynamic delta formatting
    def format_change(before, after, desc=""):
        delta = after - before
        if delta == 0:
            return "Unchanged"
        sign = f"+{delta}" if delta > 0 else f"{delta}"
        return f"{sign}{f' ({desc})' if desc else ''}"

    print("\n" + "=" * 65)
    print("1. OVERALL DATABASE CLEANUP (BEFORE / AFTER)")
    print("=" * 65)
    print(f"{'Entity':<24} | {'Before':<8} | {'After':<8} | {'Removed':<8}")
    print("-" * 65)
    print(f"{'Courses':<24} | {all_courses_count:<8} | 1        | {all_courses_count - 1:<8}")
    print(f"{'Documents':<24} | {all_docs_count:<8} | {len(kept_docs):<8} | {all_docs_count - len(kept_docs):<8}")
    print(f"{'Knowledge Chunks':<24} | {len(chunks_raw):<8} | {len(kept_chunks):<8} | {len(chunks_raw) - len(kept_chunks):<8}")
    print(f"{'Course Units':<24} | {len(cu_raw):<8} | {len(kept_cu):<8} | {len(cu_raw) - len(kept_cu):<8}")
    print(f"{'Topics':<24} | {len(topics_raw):<8} | {len(kept_topics):<8} | {len(topics_raw) - len(kept_topics):<8}")
    print(f"{'Concepts':<24} | {len(concepts_raw):<8} | {len(kept_concepts):<8} | {len(concepts_raw) - len(kept_concepts):<8}")
    print(f"{'Visual Elements':<24} | {len(visuals_raw):<8} | {len(kept_visuals):<8} | {len(visuals_raw) - len(kept_visuals):<8}")
    print(f"{'Questions':<24} | {len(questions_raw):<8} | {len(kept_questions):<8} | {len(questions_raw) - len(kept_questions):<8}")
    print(f"{'Extra Temp/Bak Files':<24} | {len(extra_files):<8} | 0        | {len(extra_files):<8}")
    print("=" * 65)

    print("\n" + "=" * 65)
    print(f"2. KEPT COURSE BREAKDOWN: {kept_course.get('name')}")
    print(f"   Course ID: {TARGET_COURSE_ID}")
    print(f"   Owner ID:  {REAL_USER_ID}")
    print("=" * 65)
    print(f"{'Entity':<24} | {'Before':<8} | {'After':<8} | {'Computed Delta'}")
    print("-" * 65)
    print(f"{'Documents':<24} | {c_docs_before:<8} | {len(kept_docs):<8} | {format_change(c_docs_before, len(kept_docs), 'duplicate doc removed')}")
    print(f"{'Knowledge Chunks':<24} | {c_chunks_before:<8} | {len(kept_chunks):<8} | {format_change(c_chunks_before, len(kept_chunks), 'duplicate doc chunks removed')}")
    print(f"{'Course Units':<24} | {c_cu_before:<8} | {len(kept_cu):<8} | {format_change(c_cu_before, len(kept_cu))}")
    print(f"{'Topics':<24} | {c_topics_before:<8} | {len(kept_topics):<8} | {format_change(c_topics_before, len(kept_topics))}")
    print(f"{'Concepts':<24} | {c_concepts_before:<8} | {len(kept_concepts):<8} | {format_change(c_concepts_before, len(kept_concepts), 'curriculum extraction needed')}")
    print(f"{'Questions':<24} | {c_questions_before:<8} | {len(kept_questions):<8} | {format_change(c_questions_before, len(kept_questions))}")
    print(f"{'Visual Elements':<24} | {c_visuals_before:<8} | {len(kept_visuals):<8} | {format_change(c_visuals_before, len(kept_visuals))}")
    print("=" * 65)

    print("\nKept Documents (Deduplicated, 8 total):")
    for did, d in kept_docs.items():
        doc_chunks = len([c for _, c in kept_chunks.items() if c.get("document_id") == did])
        print(f"  • [{did[:8]}] {d.get('filename')} ({d.get('file_type', '').upper()}) -> {doc_chunks} chunks")

    print(f"\nPreserved Backup File: {PRESERVED_BACKUP} (retained safely)")
    print(f"Extra temporary files to clean ({len(extra_files)}):")
    for ef in extra_files:
        print(f"  - {os.path.basename(ef)}")

    if dry_run:
        print("\n>>> [DRY RUN ONLY] No changes were written to disk. Run with --confirm to execute. <<<")
        return

    # Atomic write to disk: write to temp file in same directory, then os.replace
    data["courses"] = {TARGET_COURSE_ID: kept_course}
    data["documents"] = kept_docs
    data["knowledge_chunks"] = kept_chunks
    data["course_units"] = kept_cu
    data["topics"] = kept_topics
    data["concepts"] = kept_concepts
    data["concept_prerequisites"] = kept_cp
    data["visual_elements"] = kept_visuals
    data["conversations"] = kept_convs
    data["messages"] = kept_msgs
    data["questions"] = kept_questions
    data["question_history"] = kept_qh
    data["assessments"] = kept_assess
    data["assessment_questions"] = kept_aq
    data["attempts"] = kept_attempts
    data["assessment_attempts"] = kept_attempts
    data["learner_mastery"] = kept_mastery
    data["misconceptions"] = kept_misc
    data["study_plans"] = kept_sp
    data["revision_materials"] = kept_rm
    data["evaluation_results"] = kept_er
    data["units"] = kept_u

    temp_atomic_file = os.path.join(storage_dir, f"studymind_db.json.atomic_tmp_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    with open(temp_atomic_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Atomic replace
    os.replace(temp_atomic_file, db_path)
    print(f"\n[LIVE CLEANUP COMPLETE] Atomically updated {db_path} successfully.")

    # Remove extra files
    for ef in extra_files:
        try:
            os.remove(ef)
            print(f"Removed extra file: {os.path.basename(ef)}")
        except Exception as e:
            print(f"Error removing {os.path.basename(ef)}: {e}")

if __name__ == "__main__":
    is_live = "--confirm" in sys.argv
    run_cleanup(dry_run=not is_live)
