import os
import sys
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.app.core.config import settings
from backend.app.services.database import db
# Suppress remote supabase sync for acceptance script
db.supabase_client = None
db._push_to_supabase = lambda *args, **kwargs: None

from backend.app.rag.engine import rag_engine

TARGET_COURSE_ID = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"

def print_separator(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def main():
    course = db.get_by_id("courses", TARGET_COURSE_ID)
    if not course:
        print(f"ERROR: Course {TARGET_COURSE_ID} not found in database.")
        sys.exit(1)

    print("=" * 80)
    print("STUDYMIND AI — PHASE 2 ACCEPTANCE REPORT: SOURCE-GROUNDED TUTOR")
    print(f"Course: {course.get('name')} (ID: {TARGET_COURSE_ID})")
    print(f"Embedding Provider: {settings.EMBEDDING_PROVIDER} | LLM Provider: {settings.LLM_PROVIDER} ({settings.LLM_MODEL})")
    print("=" * 80)

    # 1. Refusal Calibration Results
    print_separator("1. REFUSAL CALIBRATION RESULTS (CALIBRATED ON REAL COURSE)")
    calib_thr = rag_engine.get_calibrated_threshold()
    calib_file = os.path.join(PROJECT_ROOT, "eval", "refusal_calibration_results.json")
    calib_data = {}
    if os.path.exists(calib_file):
        with open(calib_file, "r", encoding="utf-8") as f:
            calib_data = json.load(f)

    print(f"Chosen Fused Refusal Threshold: {calib_thr}")
    print(f"Optimal F1 Score:  {calib_data.get('optimal_f1_score', 'N/A')}")
    print(f"Optimal Precision: {calib_data.get('optimal_precision', 'N/A')}")
    print(f"Optimal Recall:    {calib_data.get('optimal_recall', 'N/A')}")
    cm = calib_data.get("confusion_matrix", {})
    print(f"Confusion Matrix:  TP={cm.get('tp')}, FP={cm.get('fp')}, FN={cm.get('fn')}, TN={cm.get('tn')}")

    # 2. Five In-Scope Questions Grounded in Real Documents
    print_separator("2. FIVE IN-SCOPE GROUNDED QUESTIONS (PDF, PPTX, MULTI-HOP)")
    in_scope_queries = [
        ("PDF Grounded: UNIT 2_BDA.pdf", "What is the role of NameNode and DataNode in HDFS architecture?"),
        ("PDF Grounded: Unit 1 intro to bigdata", "Explain the 5 V's of Big Data: volume, velocity, variety, veracity, and value."),
        ("PPTX Grounded: 2.3 Data_Locality.pptx", "What is data locality and why is moving computation cheaper than moving data?"),
        ("PPTX Grounded: Cluster_Resource_Management.pptx", "What are the core responsibilities of a cluster resource manager like YARN or Mesos?"),
        ("Multi-Hop: Across PPTX and PDF/Docx", "What is the relationship between HDFS distributed storage and MapReduce distributed computing in Hadoop?")
    ]

    for label, q in in_scope_queries:
        print(f"\n--- [{label}] ---")
        print(f"Question: \"{q}\"")
        ans_obj = rag_engine.answer_query(
            course_id=TARGET_COURSE_ID,
            query=q,
            allow_outside_knowledge=False
        )
        print(f"Status: Refused={ans_obj.get('refused')}, Grounded={ans_obj.get('grounded')}, Confidence={ans_obj.get('confidence_score')}")
        citations = ans_obj.get("citations", [])
        print(f"Citations count: {len(citations)}")
        for i, cit in enumerate(citations[:2], start=1):
            doc = cit.get("document_name")
            page = f"Page {cit.get('page_number')}" if cit.get("page_number") else ""
            slide = f"Slide {cit.get('slide_number')}" if cit.get("slide_number") else ""
            loc = page or slide or "Section"
            print(f"  [{i}] {doc} ({loc}) — Chunk ID: {cit.get('chunk_id')}")
            print(f"      Snippet: {cit.get('snippet', '')[:100]}...")
        
        # Concept IDs returned
        retrieved_cids = []
        retrieved = rag_engine.retrieve_chunks(TARGET_COURSE_ID, q, top_k=3)
        for chk in retrieved:
            for cid in chk.get("concept_ids", []):
                if cid and cid not in retrieved_cids:
                    retrieved_cids.append(cid)
        print(f"Retrieved Concept IDs ({len(retrieved_cids)}): {retrieved_cids[:4]}")
        answer_preview = ans_obj.get("answer", "")[:260].replace("\n", " ")
        print(f"Answer Preview: {answer_preview}...")

    # 3. Five Off-Scope Questions (Must Be Refused)
    print_separator("3. FIVE OFF-SCOPE QUESTIONS (REFUSAL GATE VERIFICATION)")
    off_scope_queries = [
        "How do you bake sourdough bread with an active starter at home?",
        "What is the capital city of Mongolia and its current population?",
        "Explain the combustion cycle in a liquid bipropellant rocket engine.",
        "Who won the 1994 FIFA World Cup soccer final in California?",
        "What is the secret recipe for chocolate molten lava cake?"
    ]

    for q in off_scope_queries:
        res = rag_engine.answer_query(
            course_id=TARGET_COURSE_ID,
            query=q,
            allow_outside_knowledge=False
        )
        closest = res.get("closest_source", {})
        closest_doc = closest.get("document_name") if closest else "None"
        print(f"\nQuestion: \"{q}\"")
        print(f"  Refused: {res.get('refused')} | Grounded: {res.get('grounded')} | Score: {res.get('confidence_score')}")
        print(f"  Answer start: {res.get('answer', '')[:90].replace(chr(10), ' ')}...")
        print(f"  Closest source in course: {closest_doc} (Top match: {int(res.get('confidence_score', 0) * 100)}%)")

    # 4. Outside-Knowledge Example with Flagged Sentences
    print_separator("4. OUTSIDE-KNOWLEDGE MODE (allow_outside_knowledge=True)")
    out_q = "Explain the combustion cycle in a liquid bipropellant rocket engine."
    out_res = rag_engine.answer_query(
        course_id=TARGET_COURSE_ID,
        query=out_q,
        allow_outside_knowledge=True
    )
    print(f"Question: \"{out_q}\"")
    print(f"Refused: {out_res.get('refused')} | Is Outside Knowledge: {out_res.get('is_outside_knowledge')}")
    print("Answer Segments Classification:")
    for seg in out_res.get("answer_segments", [])[:3]:
        badge = f"[{seg.get('type', 'outside').upper()}]"
        print(f"  {badge} \"{seg.get('text', '')[:100]}...\"")
    print(f"Answer text preview: {out_res.get('answer', '')[:220].replace(chr(10), ' ')}...")

    # 5. Hindi Answer (language=hi)
    print_separator("5. HINDI LANGUAGE TUTOR RESPONSE (language='hi')")
    hi_q = "What is data locality and why is it important in Hadoop?"
    hi_res = rag_engine.answer_query(
        course_id=TARGET_COURSE_ID,
        query=hi_q,
        language="hi",
        allow_outside_knowledge=False
    )
    print(f"Question: \"{hi_q}\"")
    print(f"Refused: {hi_res.get('refused')} | Grounded: {hi_res.get('grounded')}")
    citations = hi_res.get("citations", [])
    print(f"Citations unchanged ({len(citations)}): {[c.get('document_name') for c in citations[:2]]}")
    print(f"Hindi Answer Preview:\n{hi_res.get('answer', '')[:350]}")

    print_separator("PHASE 2 ACCEPTANCE COMPLETE")

if __name__ == "__main__":
    main()
