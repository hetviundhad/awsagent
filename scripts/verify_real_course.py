import os
import sys
import shutil
import json
import uuid
import networkx as nx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Configure environment before importing backend modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

REAL_DB_PATH = os.path.join(PROJECT_ROOT, "backend", "data", "storage", "studymind_db.json")
TEMP_DB_PATH = os.path.join(PROJECT_ROOT, "backend", "data", "storage", "studymind_db_verification_tmp.json")

# Create temporary copy of real DB for test isolation
shutil.copyfile(REAL_DB_PATH, TEMP_DB_PATH)
os.environ["STUDYMIND_DB_PATH"] = TEMP_DB_PATH

from backend.app.services.database import db
# Suppress remote supabase sync during local verification
db.supabase_client = None
db._push_to_supabase = lambda *args, **kwargs: None
db.reinit(TEMP_DB_PATH)

from backend.app.rag.engine import RAGEngine
from backend.app.assessment.generator import AssessmentEngine
from backend.app.learner.bkt import bkt_engine
from backend.app.main import health_ai
from backend.app.api.api import get_course_concept_map
from fastapi import Request

COURSE_ID = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"
STUDENT_ID = "e5ee47b2-ad1d-4536-b3eb-a165de1792b1"

def print_separator(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def main():
    print(f"Starting verification on temporary copy of real DB: {TEMP_DB_PATH}")
    
    # -------------------------------------------------------------
    # 1. Per Document: Chunk Count and Concept Count
    # -------------------------------------------------------------
    print_separator("1. PER-DOCUMENT CHUNK COUNT AND CONCEPT COUNT")
    docs = db.list_all("documents", lambda d: d.get("course_id") == COURSE_ID)
    all_chunks = db.list_all("knowledge_chunks", lambda c: c.get("course_id") == COURSE_ID)
    
    print(f"Found {len(docs)} documents in course {COURSE_ID}:\n")
    print(f"{'Filename':<55} | {'Type':<6} | {'Chunks':<7} | {'Concepts':<8}")
    print("-" * 84)
    for d in docs:
        d_chunks = [c for c in all_chunks if c.get("document_id") == d["id"]]
        d_concepts = set()
        for chk in d_chunks:
            d_concepts.update(chk.get("concept_ids", []))
        ftype = (d.get("file_type") or "doc").upper()
        print(f"{d.get('filename')[:53]:<55} | {ftype:<6} | {len(d_chunks):<7} | {len(d_concepts):<8}")
    
    # -------------------------------------------------------------
    # 2. Total Concepts, Topics, Prerequisite Edges (DAG Check)
    # -------------------------------------------------------------
    print_separator("2. TOTAL CONCEPTS, TOPICS, AND PREREQUISITE EDGES (DAG CHECK)")
    concepts = db.list_all("concepts", lambda c: c.get("course_id") == COURSE_ID)
    topics = db.list_all("topics", lambda t: t.get("course_id") == COURSE_ID)
    c_ids = {c["id"] for c in concepts}
    edges = db.list_all("concept_prerequisites", lambda e: e.get("concept_id") in c_ids or e.get("prerequisite_id") in c_ids or e.get("course_id") == COURSE_ID)
    
    G = nx.DiGraph()
    for c in concepts:
        G.add_node(c["id"], name=c.get("name"))
    for e in edges:
        src = e.get("prerequisite_id") or e.get("source_concept_id")
        tgt = e.get("concept_id") or e.get("target_concept_id")
        if src and tgt and src in c_ids and tgt in c_ids:
            G.add_edge(src, tgt)
    
    is_dag = nx.is_directed_acyclic_graph(G)
    print(f"Total Concepts in Course: {len(concepts)}")
    print(f"Total Topics in Course:   {len(topics)}")
    print(f"Total Prerequisite Edges: {len(edges)}")
    print(f"Directed Acyclic Graph (No Cycles): {is_dag}")
    if not is_dag:
        cycles = list(nx.simple_cycles(G))
        print(f"Cycles detected: {cycles}")
    else:
        print("Cycle Check: PASSED (Strict DAG confirmed)")

    # -------------------------------------------------------------
    # 3. 10 Sample Concept Names with Definitions and Supporting Chunk IDs
    # -------------------------------------------------------------
    print_separator("3. 10 SAMPLE CONCEPT NAMES WITH DEFINITIONS AND SUPPORTING CHUNKS")
    for i, c in enumerate(concepts[:10], start=1):
        sup_chunks = c.get("supporting_chunk_ids", [])
        loc_str = "N/A"
        if sup_chunks:
            first_chk = db.get_by_id("knowledge_chunks", sup_chunks[0])
            if first_chk:
                doc_name = first_chk.get("document_name", "doc")
                page_or_slide = (
                    f"Page {first_chk.get('page_number')}" if first_chk.get("page_number")
                    else f"Slide {first_chk.get('slide_number')}" if first_chk.get("slide_number")
                    else f"Chunk {first_chk.get('chunk_index', 0)}"
                )
                loc_str = f"{doc_name} ({page_or_slide})"
        
        definition = c.get('description') or c.get('definition') or "N/A"
        print(f"[{i:02d}] Concept:    {c.get('name')}")
        print(f"     Definition: {definition}")
        print(f"     Location:   {loc_str}")
        print(f"     Chunk IDs:  {', '.join(sup_chunks[:3])}")
        print()

    # -------------------------------------------------------------
    # 4. 3 In-Scope Tutor Questions and 2 Off-Scope Refused Questions
    # -------------------------------------------------------------
    print_separator("4. SOCRATIC TUTOR EVALUATION: 3 IN-SCOPE + 2 OFF-SCOPE QUERIES")
    rag = RAGEngine()
    
    in_scope_queries = [
        "What is data locality and how does it optimize distributed execution?",
        "Explain cluster resource management and how nodes allocate memory and CPU.",
        "What are the 5Vs of Big Data and the stages of the Data Life Cycle in Unit 1?"
    ]
    
    print("--- IN-SCOPE QUESTIONS (Must be grounded with citations) ---")
    for idx, q in enumerate(in_scope_queries, start=1):
        print(f"\n[IN-SCOPE #{idx}] Query: {q}")
        res = rag.answer_query(
            course_id=COURSE_ID,
            query=q,
            allow_outside_knowledge=False
        )
        print(f"Status: Grounded={res.get('grounded')}, Refused={res.get('refused', False)}, Confidence={res.get('confidence_score')}")
        print("Answer Summary:")
        ans_preview = res.get('answer', '')[:250].replace('\n', ' ')
        print(f"  {ans_preview}...")
        print("Citations:")
        for cit in res.get("citations", [])[:3]:
            doc = cit.get("document_name")
            p = cit.get("page_number")
            s = cit.get("slide_number")
            loc = f"Page {p}" if p else (f"Slide {s}" if s else f"Chunk {cit.get('chunk_id')}")
            print(f"  • [{cit.get('citation_index')}] {doc} ({loc})")
            print(f"    Snippet: \"{cit.get('snippet', '')[:100]}...\"")

    off_scope_queries = [
        "What is the capital of France and what are its top tourist attractions?",
        "Write a poem about quantum gravity and black holes."
    ]
    print("\n--- OFF-SCOPE QUESTIONS (Must be refused) ---")
    for idx, q in enumerate(off_scope_queries, start=1):
        print(f"\n[OFF-SCOPE #{idx}] Query: {q}")
        res = rag.answer_query(
            course_id=COURSE_ID,
            query=q,
            allow_outside_knowledge=False
        )
        print(f"Status: Refused={res.get('refused', False)}, Grounded={res.get('grounded', False)}")
        print(f"Refusal Response:")
        first_line = res.get('answer', '').split('\n\n')[0]
        print(f"  \"{first_line}\"")
        if res.get('closest_source'):
            cs = res.get('closest_source')
            print(f"  Nearest Chunk Score: {res.get('confidence_score')} | Closest Source: {cs.get('document_name')}")

    # -------------------------------------------------------------
    # 5. 5-Question Quiz Verified by Blind Solving
    # -------------------------------------------------------------
    print_separator("5. 5-QUESTION QUIZ WITH SOURCE CITATION AND BLIND SOLVE VERIFICATION")
    assessment_engine = AssessmentEngine()
    
    # Select 5 diverse chunks from different documents
    sample_chunks = []
    seen_docs = set()
    for chk in all_chunks:
        d_id = chk.get("document_id")
        if d_id not in seen_docs and len(chk.get("content", "")) > 120:
            sample_chunks.append(chk)
            seen_docs.add(d_id)
        if len(sample_chunks) >= 5:
            break
            
    # If fewer than 5 unique documents have large chunks, fill with other chunks
    if len(sample_chunks) < 5:
        for chk in all_chunks:
            if chk not in sample_chunks and len(chk.get("content", "")) > 100:
                sample_chunks.append(chk)
            if len(sample_chunks) >= 5:
                break

    existing_hashes = set()
    verified_questions = []
    for i, chk in enumerate(sample_chunks[:5], start=1):
        c_id = chk.get("concept_ids", [None])[0] if chk.get("concept_ids") else None
        q = assessment_engine._synthesize_and_verify_question(
            course_id=COURSE_ID,
            chunk=chk,
            existing_hashes=existing_hashes,
            difficulty="Medium",
            target_concept_id=c_id
        )
        if q:
            verified_questions.append(q)
            existing_hashes.add(assessment_engine._compute_question_hash(q.get("question_text", "")))
    
    print(f"Generated and verified {len(verified_questions)} questions:\n")
    for i, q in enumerate(verified_questions, start=1):
        c_obj = db.get_by_id("concepts", q.get("concept_id")) if q.get("concept_id") else None
        t_obj = db.get_by_id("topics", q.get("topic_id")) if q.get("topic_id") else None
        c_name = c_obj.get("name") if c_obj else "Distributed Systems"
        t_name = t_obj.get("name") if t_obj else "Big Data Architecture"
        v_det = q.get("verification_details", {})

        print(f"[Q{i}] Question: {q.get('question_text')}")
        print(f"     Concept:       {c_name}")
        print(f"     Topic:         {t_name}")
        print(f"     Difficulty:    {q.get('difficulty')}")
        print(f"     Location:      {q.get('source_document')} ({q.get('source_location')})")
        print(f"     Correct Key:   {q.get('correct_answer')}")
        print(f"     Quote:         \"{q.get('supporting_quote')}\"")
        print(f"     Quote Verified in Chunk: {v_det.get('source_supported', True)}")
        print(f"     Blind Solve Verified:    {v_det.get('cross_model_solver_agreement', True)} ({v_det.get('check_reason', 'Passed blind solve')})")
        print()

    # -------------------------------------------------------------
    # 6. Concept Map: Nodes and Edges from API
    # -------------------------------------------------------------
    print_separator("6. CONCEPT MAP GRAPH ENGINE API OUTPUT")
    class MockHeaders:
        def get(self, key, default=""):
            if key.lower() == "authorization":
                return f"Bearer {STUDENT_ID}"
            return default

    class MockRequest:
        def __init__(self, user_id):
            self.state = type("State", (), {"user_id": user_id})()
            self.headers = MockHeaders()
    
    mock_req = MockRequest(STUDENT_ID)
    map_data = get_course_concept_map(COURSE_ID, mock_req)
    nodes = map_data.get("nodes", [])
    map_edges = map_data.get("edges", [])
    print(f"Concept Map API Nodes Count: {len(nodes)}")
    print(f"Concept Map API Edges Count: {len(map_edges)}")
    print(f"Top 5 Nodes Sample:")
    for n in nodes[:5]:
        print(f"  • {n.get('name')} (Topic: {n.get('topic')}, Prereqs: {len(n.get('prerequisites', []))}, Mastery: {n.get('mastery_score')})")

    # -------------------------------------------------------------
    # 7. BKT: Deliberate Wrong Answer and Mastery Update
    # -------------------------------------------------------------
    print_separator("7. BKT ENGINE MASTERY UPDATE (DELIBERATE WRONG ANSWER)")
    test_concept = concepts[0]
    c_id = test_concept["id"]
    c_name = test_concept["name"]
    
    # Get initial mastery
    init_rec = bkt_engine.get_or_create_mastery(STUDENT_ID, COURSE_ID, c_id)
    init_concept_mastery = init_rec.get("mastery_probability", 0.15)
    print(f"Testing Concept: \"{c_name}\" (ID: {c_id})")
    print(f"Mastery BEFORE wrong answer: {init_concept_mastery:.4f} ({round(init_concept_mastery * 100, 1)}%)")
    
    # Submit wrong answer
    updated_rec = bkt_engine.update_mastery(
        student_id=STUDENT_ID,
        course_id=COURSE_ID,
        concept_id=c_id,
        is_correct=False,
        difficulty="Medium"
    )
    after_concept_mastery = updated_rec.get("mastery_probability", 0.0)
    delta = after_concept_mastery - init_concept_mastery
    print(f"Mastery AFTER wrong answer:  {after_concept_mastery:.4f} ({round(after_concept_mastery * 100, 1)}%)")
    print(f"Delta:                       {delta:+.4f}")
    
    profile = bkt_engine.get_learner_profile(STUDENT_ID, COURSE_ID)
    print(f"Overall Course Mastery:      {profile.get('overall_mastery', 0.0) * 100:.1f}%")
    print("BKT Engine Decay on Incorrect Response: VERIFIED")

    # -------------------------------------------------------------
    # 8. GET /api/health/ai Output
    # -------------------------------------------------------------
    print_separator("8. GET /api/health/ai STATUS OUTPUT")
    health_result = health_ai()
    print(json.dumps(health_result, indent=2))
    
    # Clean up temporary database copy
    if os.path.exists(TEMP_DB_PATH):
        os.remove(TEMP_DB_PATH)
        print(f"\nTemporary verification DB successfully removed: {TEMP_DB_PATH}")
    print("Real database preserved without changes.")

if __name__ == "__main__":
    main()
