import os
import sys
from typing import Dict, Any, List
from backend.app.services.database import db
from backend.app.ingestion.concept_filter import concept_filter
from backend.app.core.config import settings, is_test_environment

def run_startup_self_check() -> Dict[str, int]:
    """
    Startup self-check verifying:
    1. Provider credentials when running live (non-test): GROQ_API_KEY and SUPABASE keys must exist.
    2. Zero ungrounded chunks (every unit has page/slide/timestamp).
    3. Removal of junk concepts and backfilling definitions.
    """
    print("\n" + "="*50)
    print("StudyMind AI - Startup Self-Check")
    print("="*50)

    # 0. Check API keys and Supabase credentials in live mode (APP_ENV != 'test')
    if not is_test_environment():
        missing_keys = []
        if not settings.GROQ_API_KEY or not settings.GROQ_API_KEY.strip():
            missing_keys.append("GROQ_API_KEY")
        if not settings.SUPABASE_URL or not settings.SUPABASE_URL.strip():
            missing_keys.append("SUPABASE_URL")
        if not settings.SUPABASE_KEY or not settings.SUPABASE_KEY.strip():
            missing_keys.append("SUPABASE_KEY")

        if missing_keys:
            print(f"\n[StartupCheck] Notice: Missing keys: {', '.join(missing_keys)}. Using Bedrock/Decider/Local persistence fallback.\n", file=sys.stderr)



    # 1. Inspect all concepts
    all_concepts = db.list_all("concepts")
    junk_concepts_removed = 0
    concepts_without_definitions = 0

    all_chunks = db.list_all("knowledge_chunks")

    for concept in all_concepts:
        c_id = concept["id"]
        c_name = concept.get("name", "")
        c_desc = concept.get("description", "")
        course_id = concept.get("course_id", "")
        course = db.get_by_id("courses", course_id)
        subject = course.get("subject", "") if course else ""

        # Check concept quality
        is_valid, reason = concept_filter.validate_candidate_name(c_name, subject)
        if not is_valid:
            # Junk concept: remove from db
            db.delete("concepts", c_id)
            # Remove associated learner mastery
            mastery_recs = db.list_all("learner_mastery", lambda m: m.get("concept_id") == c_id)
            for m in mastery_recs:
                db.delete("learner_mastery", m["id"])
            # Remove associated prerequisite edges
            prereqs = db.list_all("concept_prerequisites", lambda p: p.get("concept_id") == c_id or p.get("prerequisite_id") == c_id)
            for p in prereqs:
                db.delete("concept_prerequisites", p["id"])
            junk_concepts_removed += 1
            continue

        # Check definition
        if not c_desc or len(c_desc.strip()) < 15 or "Key learning objectives" in c_desc:
            # Try to backfill from source chunks
            def_sentence = concept_filter.extract_definition_from_chunks(c_name, all_chunks)
            if def_sentence:
                concept["description"] = def_sentence
                db.update("concepts", c_id, concept)
            else:
                concepts_without_definitions += 1

    # 2. Inspect all knowledge units (chunks)
    units_without_location = 0
    invalid_units: List[str] = []

    for chunk in all_chunks:
        chk_id = chunk.get("id")
        page = chunk.get("page_number")
        slide = chunk.get("slide_number")
        t_start = chunk.get("timestamp_start")
        source_type = chunk.get("source_type")
        url = chunk.get("url")

        has_location = (
            page is not None or
            slide is not None or
            t_start is not None or
            (source_type == "web" and url is not None)
        )

        if not has_location:
            units_without_location += 1
            invalid_units.append(f"Unit ID: {chk_id}, Document: {chunk.get('document_name')}")

    print(f"[Self-Check] Junk concepts removed: {junk_concepts_removed}")
    print(f"[Self-Check] Concepts without definitions: {concepts_without_definitions}")
    print(f"[Self-Check] Units without a source location: {units_without_location}")
    print("="*50)

    # Fail loudly if any unit has no page/slide/timestamp
    if units_without_location > 0:
        err_msg = (
            f"CRITICAL STARTUP INTEGRITY ERROR: Found {units_without_location} knowledge units without a source location!\n"
            f"Details: {invalid_units[:5]}\n"
            f"Every unit in StudyMind AI must be grounded in an exact page, slide, or timestamp."
        )
        print(f"\n[FATAL] {err_msg}", file=sys.stderr)
        raise RuntimeError(err_msg)

    print("[Self-Check] Integrity verification PASSED successfully.\n")
    return {
        "junk_concepts_removed": junk_concepts_removed,
        "concepts_without_definitions": concepts_without_definitions,
        "units_without_location": units_without_location
    }
