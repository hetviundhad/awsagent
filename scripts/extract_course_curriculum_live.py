import os
import sys
import json
import time
import uuid
import re
from typing import List, Dict, Any, Tuple, Optional
import networkx as nx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.database import db
# Suppress remote supabase sync during local batch curriculum extraction
db.supabase_client = None
db._push_to_supabase = lambda *args, **kwargs: None

from backend.app.core.config import settings
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.ingestion.concept_filter import concept_filter
from backend.app.models.schemas import ExtractedCurriculum

TARGET_COURSE_ID = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    import numpy as np
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    dot = np.dot(a, b)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(dot / (na * nb))

def reextract_docx_if_needed(pipeline: IngestionPipeline, doc_id: str, doc_obj: Dict[str, Any]):
    """If docx chunks are binary or empty, re-extract with clean docx parser."""
    chunks = db.list_all("knowledge_chunks", lambda c: c.get("document_id") == doc_id)
    needs_reextract = False
    if not chunks:
        needs_reextract = True
    else:
        sample = chunks[0].get("content", "")
        if sample.startswith("PK") or len(sample) < 20:
            needs_reextract = True

    if needs_reextract:
        file_path = doc_obj.get("storage_path")
        if file_path and os.path.exists(file_path):
            print(f"[Docx Re-extract] Parsing clean XML text from {doc_obj.get('filename')}...")
            new_chunks, _ = pipeline._extract_document(TARGET_COURSE_ID, doc_id, file_path, doc_obj.get("filename"))
            # Remove old chunks
            for chk in chunks:
                db.delete("knowledge_chunks", chk["id"])
            # Embed and insert new chunks
            for chk in new_chunks:
                chk["embedding"] = pipeline.embedding_provider.embed_text(chk["content"])
                db.insert("knowledge_chunks", chk)
            doc_obj["page_count"] = len(new_chunks)
            db.update("documents", doc_id, doc_obj)
            print(f"[Docx Re-extract] Extracted {len(new_chunks)} clean text chunks for {doc_obj.get('filename')}.")

def call_groq_llm(prompt_system: str, prompt_user: str, max_retries: int = 8, doc_idx: int = 0) -> str:
    import httpx
    groq_key = settings.GROQ_API_KEY
    if not groq_key or not groq_key.strip():
        raise RuntimeError("GROQ_API_KEY is not configured!")

    candidate_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "allam-2-7b", "qwen/qwen3.8-27b"]

    backoff = 2.0
    last_err = None

    for attempt in range(max_retries):
        model_name = candidate_models[(doc_idx + attempt) % len(candidate_models)]
        try:
            with httpx.Client(timeout=45.0) as client:
                res = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "StudyMind/1.0"
                    },
                    json={
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": prompt_system},
                            {"role": "user", "content": prompt_user}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 2500
                    }
                )
                if res.status_code == 429:
                    print(f"  [Rate Limit 429 on {model_name}] Switching to next model...")
                    time.sleep(2.0)
                    continue
                if res.status_code >= 500:
                    print(f"  [Server Error {res.status_code} on {model_name}] Waiting {backoff:.1f}s...")
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                if res.status_code == 200:
                    msg = res.json()["choices"][0]["message"]
                    content = (msg.get("content") or "").strip()
                    if not content:
                        content = (msg.get("reasoning") or "").strip()
                    if content:
                        return content
                    continue
                last_err = f"HTTP {res.status_code}: {res.text[:200]}"
        except Exception as e:
            last_err = str(e)
            print(f"  [Network/Call Exception on {model_name} attempt {attempt+1}]: {e}")
            time.sleep(backoff)
            backoff *= 1.5

    raise RuntimeError(f"LLM call failed after {max_retries} retries: {last_err}")

def extract_concepts_for_document(doc: Dict[str, Any], chunks: List[Dict[str, Any]], doc_idx: int = 0) -> Dict[str, Any]:
    """Extracts curriculum JSON from real document chunks using LLM with retry."""
    filename = doc.get("filename", "")
    print(f"\n--- Extracting Concepts for: {filename} ({len(chunks)} chunks) ---")

    # Sample representative excerpts across the document
    sampled_chunks = chunks[:15] if len(chunks) <= 20 else chunks[:8] + chunks[len(chunks)//2:len(chunks)//2+5] + chunks[-4:]
    excerpts = []
    total_len = 0
    for idx, chk in enumerate(sampled_chunks):
        c_text = chk.get("content", "").strip()
        if len(c_text) > 40:
            snippet = f"[Chunk {chk.get('id')[:8]} | Slide/Page {chk.get('slide_number') or chk.get('page_number') or (idx+1)}]: {c_text[:300]}"
            if total_len + len(snippet) > 2600:
                break
            excerpts.append(snippet)
            total_len += len(snippet)

    context_str = "\n\n".join(excerpts)
    clean_title = os.path.splitext(filename)[0].replace("_", " ").title()

    prompt_system = (
        "You are an expert academic curriculum ontologist and professor in Big Data Analytics and Distributed Systems. "
        "Analyze the provided academic textbook/slide excerpts and extract atomic, rigorously grounded academic concepts.\n"
        "RULES:\n"
        "1. GROUNDING: Every concept name and definition must come directly from facts present in the text excerpts.\n"
        "2. BOILERPLATE BAN: Strictly REJECT non-conceptual items (e.g., Agenda, Introduction, Course Objectives, Syllabus, Thank You, Author Names, References, Q&A).\n"
        "3. CONCEPT FORMAT: Concept name must be 1 to 5 words (e.g. 'Rack Awareness', 'Data Locality', 'MapReduce Shuffling', 'YARN NodeManager').\n"
        "4. DEFINITIONS: Each definition must be exactly ONE clear, academic sentence defining the concept based on the text.\n"
        "5. EXTRACT 3 to 6 key concepts per topic, grouped under 1 to 2 clear topics.\n"
        "6. Return ONLY valid JSON matching this schema:\n"
        "{\n"
        '  "topics": [\n'
        '    {\n'
        '      "name": "Topic Name",\n'
        '      "concepts": [\n'
        '        {\n'
        '          "name": "Concept Name",\n'
        '          "definition": "One-line definition from excerpt.",\n'
        '          "difficulty": 3,\n'
        '          "prerequisites": ["Earlier Concept Name"]\n'
        '        }\n'
        '      ]\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    prompt_user = (
        f"Document: {clean_title}\n\n"
        f"EXCERPTS:\n\"\"\"\n{context_str}\n\"\"\"\n\n"
        "Extract valid concepts in strict JSON format now."
    )

    raw_output = call_groq_llm(prompt_system, prompt_user, doc_idx=doc_idx)
    return safe_parse_curriculum_json(raw_output)

def safe_parse_curriculum_json(raw_text: str) -> Dict[str, Any]:
    # 1. Direct JSON parse
    m = re.search(r'\{[\s\S]*\}', raw_text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    # 2. Regex concept recovery if JSON was cut off
    concept_pattern = re.compile(
        r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"definition"\s*:\s*"([^"]+)"',
        re.DOTALL
    )
    found_concepts = []
    for match in concept_pattern.finditer(raw_text):
        c_name = match.group(1).strip()
        c_def = match.group(2).strip()
        found_concepts.append({
            "name": c_name,
            "definition": c_def,
            "difficulty": 3,
            "prerequisites": []
        })

    if found_concepts:
        t_match = re.search(r'"name"\s*:\s*"([^"]+)"', raw_text)
        t_name = t_match.group(1).strip() if t_match else "Core Principles"
        return {
            "topics": [
                {
                    "name": t_name,
                    "concepts": found_concepts
                }
            ]
        }
    raise ValueError(f"Unable to parse concepts from: {raw_text[:200]}")

def main():
    print("=" * 60)
    print("STEP 2: LIVE CONCEPT EXTRACTION ON REAL COURSE DOCUMENTS")
    print(f"Target Course ID: {TARGET_COURSE_ID}")
    print("=" * 60)

    course = db.get_by_id("courses", TARGET_COURSE_ID)
    if not course:
        print(f"ERROR: Course {TARGET_COURSE_ID} not found in database!")
        sys.exit(1)

    print(f"Course: {course.get('name')}")
    pipeline = IngestionPipeline()

    docs = db.list_all("documents", lambda d: d.get("course_id") == TARGET_COURSE_ID)
    print(f"Found {len(docs)} documents in course.")

    # 1. Ensure clean text chunks for all documents (especially DOCX)
    for doc in docs:
        if doc.get("filename", "").lower().endswith(".docx"):
            reextract_docx_if_needed(pipeline, doc["id"], doc)

    # 2. Extract concepts for each document in batches with exponential backoff & retry
    failed_docs = []
    doc_results = {}

    for doc_idx, doc in enumerate(docs):
        doc_id = doc["id"]
        fname = doc["filename"]
        chunks = db.list_all("knowledge_chunks", lambda c: c.get("document_id") == doc_id)
        if not chunks:
            print(f"Warning: Document {fname} has 0 chunks! Skipping.")
            continue

        try:
            curriculum_json = extract_concepts_for_document(doc, chunks, doc_idx=doc_idx)
            doc_results[doc_id] = (doc, chunks, curriculum_json)
            time.sleep(1.0)
        except Exception as e:
            print(f"ERROR extracting concepts for {fname}: {e}")
            failed_docs.append((doc_idx, doc, chunks, str(e)))

    # Retry failed documents at the end
    if failed_docs:
        print(f"\nRetrying {len(failed_docs)} failed documents with exponential backoff...")
        still_failed = []
        for d_idx, doc, chunks, err_msg in failed_docs:
            fname = doc["filename"]
            time.sleep(3.0)
            try:
                curriculum_json = extract_concepts_for_document(doc, chunks, doc_idx=d_idx + 2)
                doc_results[doc["id"]] = (doc, chunks, curriculum_json)
                print(f"Successfully recovered {fname} on retry!")
            except Exception as retry_err:
                print(f"Retry FAILED for {fname}: {retry_err}")
                still_failed.append((doc, retry_err))
        if still_failed:
            print(f"CRITICAL: {len(still_failed)} documents failed extraction completely.")
            for d, err in still_failed:
                d["status"] = "needs analysis"
                d["error_message"] = f"Extraction failed: {err}"
                db.update("documents", d["id"], d)

    # 3. Process, validate, filter boilerplate, and deduplicate concepts
    print("\n--- Processing and Deduplicating Concepts Across All 8 Documents ---")
    existing_concepts: List[Dict[str, Any]] = []
    concept_name_to_id: Dict[str, str] = {}
    concept_name_to_obj: Dict[str, Dict[str, Any]] = {}
    topic_map: Dict[str, str] = {}
    all_raw_concepts_count = 0
    rejected_boilerplate = 0

    all_course_chunks = db.list_all("knowledge_chunks", lambda c: c.get("course_id") == TARGET_COURSE_ID)
    print(f"Total chunks in course: {len(all_course_chunks)}")

    course_subject = course.get("subject") or "Distributed Computing"
    for doc_id, (doc, chunks, curriculum_json) in doc_results.items():
        doc_name = doc.get("filename", "")
        for t_data in curriculum_json.get("topics", []):
            t_name = t_data.get("name", "Distributed Data Processing").strip()
            if t_name not in topic_map:
                t_obj = pipeline._get_or_create_topic(TARGET_COURSE_ID, t_name)
                topic_map[t_name] = t_obj["id"]

            t_id = topic_map[t_name]

            for c_data in t_data.get("concepts", []):
                all_raw_concepts_count += 1
                c_name = c_data.get("name", "").strip()
                c_def = c_data.get("definition", "").strip()
                c_diff = c_data.get("difficulty", 3)

                # Lexical and boilerplate validation
                is_valid, reason = concept_filter.validate_candidate_name(c_name, course_subject)
                if not is_valid or concept_filter.is_boilerplate(c_name):
                    print(f"  [Boilerplate Rejected]: '{c_name}' ({reason})")
                    rejected_boilerplate += 1
                    continue

                if len(c_def) < 15 or concept_filter.is_boilerplate(c_def):
                    print(f"  [Boilerplate Rejected Definition]: '{c_name}' -> '{c_def}'")
                    rejected_boilerplate += 1
                    continue

                # Find supporting chunks (lexical match or semantic similarity > 0.60)
                supporting_chunk_ids = []
                c_emb = pipeline.embedding_provider.embed_text(f"{c_name}: {c_def}")
                name_words = [w.lower() for w in re.findall(r'\b[a-zA-Z0-9]{3,}\b', c_name)]

                for chk in chunks:
                    chk_text = chk.get("content", "").lower()
                    # Verbatim word match
                    if any(w in chk_text for w in name_words):
                        supporting_chunk_ids.append(chk["id"])
                    else:
                        chk_emb = chk.get("embedding")
                        if not chk_emb:
                            chk_emb = pipeline.embedding_provider.embed_text(chk.get("content", ""))
                            chk["embedding"] = chk_emb
                        if cosine_similarity(c_emb, chk_emb) > 0.62:
                            supporting_chunk_ids.append(chk["id"])

                # If not found in this document's chunks, check entire course chunks
                if not supporting_chunk_ids:
                    for chk in all_course_chunks:
                        chk_text = chk.get("content", "").lower()
                        if any(w in chk_text for w in name_words):
                            supporting_chunk_ids.append(chk["id"])
                            if len(supporting_chunk_ids) >= 3:
                                break

                if not supporting_chunk_ids:
                    print(f"  [Rejected]: '{c_name}' has no supporting chunk citations in text.")
                    continue

                # Cross-document deduplication: embedding similarity + LLM confirmation
                merged_target_id = None
                for ex in existing_concepts:
                    ex_name = ex["name"]
                    ex_def = ex["description"]
                    ex_emb = ex["_emb"]
                    sim = cosine_similarity(c_emb, ex_emb)
                    if sim > 0.85:
                        is_same = pipeline._confirm_concept_duplicate_with_llm(ex_name, ex_def, c_name, c_def)
                        if is_same:
                            merged_target_id = ex["id"]
                            # Union supporting chunk IDs
                            ex_chunks = set(ex.get("supporting_chunk_ids", []))
                            ex_chunks.update(supporting_chunk_ids)
                            ex["supporting_chunk_ids"] = list(ex_chunks)
                            print(f"  [Merged Concept]: '{c_name}' merged into existing '{ex_name}' (sim: {sim:.2f})")
                            break

                if merged_target_id:
                    concept_name_to_id[c_name] = merged_target_id
                else:
                    new_id = f"con_{uuid.uuid4().hex[:8]}"
                    concept_record = {
                        "id": new_id,
                        "course_id": TARGET_COURSE_ID,
                        "topic_id": t_id,
                        "name": c_name,
                        "description": c_def,
                        "difficulty": "Medium" if c_diff == 3 else ("Easy" if c_diff < 3 else "Hard"),
                        "difficulty_num": c_diff,
                        "prerequisites": [p for p in c_data.get("prerequisites", []) if p],
                        "supporting_chunk_ids": supporting_chunk_ids,
                        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "_emb": c_emb
                    }
                    existing_concepts.append(concept_record)
                    concept_name_to_id[c_name] = new_id
                    concept_name_to_obj[c_name] = concept_record

    print(f"\nExtracted {all_raw_concepts_count} raw candidates, rejected {rejected_boilerplate} boilerplate items.")
    print(f"Final Deduplicated Concept Count: {len(existing_concepts)}")

    # 4. Clean and persist concepts to database
    db.supabase_client = None
    # Clear out any old concepts for this course
    old_concepts = db.list_all("concepts", lambda c: c.get("course_id") == TARGET_COURSE_ID)
    for oc in old_concepts:
        db.delete("concepts", oc["id"])

    # Clear old prerequisites for this course
    old_prereqs = db.list_all("concept_prerequisites", lambda p: p.get("course_id") == TARGET_COURSE_ID)
    for op in old_prereqs:
        db.delete("concept_prerequisites", op["id"])

    for c_rec in existing_concepts:
        # Strip temporary embedding before DB insert
        save_obj = dict(c_rec)
        save_obj.pop("_emb", None)
        db.insert("concepts", save_obj, save_disk=False)

    # 5. Build Prerequisite DAG and Remove Cycles
    print("\n--- Constructing Prerequisite DAG and Verifying Acyclicity ---")
    G = nx.DiGraph()
    for c in existing_concepts:
        G.add_node(c["id"], name=c["name"])

    for c in existing_concepts:
        curr_id = c["id"]
        for p_name in c.get("prerequisites", []):
            if p_name in concept_name_to_id:
                p_id = concept_name_to_id[p_name]
                if p_id != curr_id:
                    G.add_edge(p_id, curr_id)

    # If graph has disconnected nodes, create logical sequential progression between foundational concepts
    if G.number_of_edges() < len(existing_concepts) // 2:
        concept_ids = [c["id"] for c in existing_concepts]
        for i in range(1, len(concept_ids)):
            if not nx.has_path(G, concept_ids[i-1], concept_ids[i]) and not nx.has_path(G, concept_ids[i], concept_ids[i-1]):
                G.add_edge(concept_ids[i-1], concept_ids[i])

    # Check for cycles and break them
    try:
        cycles = list(nx.simple_cycles(G))
        if cycles:
            print(f"Detected {len(cycles)} cycle(s) in prerequisite graph. Breaking cycles...")
            for cycle in cycles:
                if len(cycle) >= 2:
                    G.remove_edge(cycle[-1], cycle[0])
                    print(f"  Removed cycle edge: {cycle[-1]} -> {cycle[0]}")
    except Exception as cycle_err:
        print(f"Cycle detection note: {cycle_err}")

    # Verify DAG is strictly acyclic
    is_dag = nx.is_directed_acyclic_graph(G)
    print(f"Is Prerequisite Graph strictly Acyclic (DAG)? {is_dag}")
    print(f"Total DAG Nodes: {G.number_of_nodes()}, Total Edges: {G.number_of_edges()}")

    # Insert DAG edges into database
    edge_count = 0
    for u, v in G.edges():
        db.insert("concept_prerequisites", {
            "id": str(uuid.uuid4()),
            "course_id": TARGET_COURSE_ID,
            "concept_id": v,
            "prerequisite_id": u,
            "relationship_type": "prerequisite",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }, save_disk=False)
        edge_count += 1

    # Disable background Supabase sync during bulk local operations to avoid network round-trip bottlenecks
    db.supabase_client = None

    # 6. Multi-label Tag every chunk with 1-3 concepts and topics
    print("\n--- Tagging All Chunks with 1-3 Concepts and Topics ---")
    tagged_chunk_count = 0
    # Cache concept embeddings (already stored in c['_emb'])
    concept_embs = {}
    for c in existing_concepts:
        concept_embs[c["id"]] = c.get("_emb") or pipeline.embedding_provider.embed_text(f"{c['name']}: {c['description']}")

    for chk in all_course_chunks:
        chk_text = chk.get("content", "").lower()
        chk_emb = chk.get("embedding")
        if not chk_emb:
            chk_emb = pipeline.embedding_provider.embed_text(chk.get("content", ""))
            chk["embedding"] = chk_emb

        scores = []
        for c in existing_concepts:
            c_name = c["name"]
            c_emb = concept_embs[c["id"]]
            sim = cosine_similarity(chk_emb, c_emb)
            if c_name.lower() in chk_text:
                sim = max(sim, 0.90)
            scores.append((c["id"], c.get("topic_id"), sim))

        scores.sort(key=lambda x: x[2], reverse=True)

        # Select top 1 to 3 concepts
        top_matches = scores[:min(3, len(scores))]
        c_ids = [item[0] for item in top_matches if item[2] >= 0.40]
        if not c_ids and scores:
            c_ids = [scores[0][0]]

        t_ids = list(dict.fromkeys([item[1] for item in top_matches if item[1]]))
        if not t_ids and scores and scores[0][1]:
            t_ids = [scores[0][1]]

        chk["concept_ids"] = c_ids
        chk["topic_ids"] = t_ids
        db.update("knowledge_chunks", chk["id"], chk, save_disk=False)
        tagged_chunk_count += 1

    print(f"Successfully tagged {tagged_chunk_count} chunks with 1-3 concepts and topics.")

    # 7. Update Document Statuses & Course Stats
    all_final_topics = db.list_all("topics", lambda t: t.get("course_id") == TARGET_COURSE_ID)
    all_final_concepts = db.list_all("concepts", lambda c: c.get("course_id") == TARGET_COURSE_ID)

    for doc in docs:
        doc_chunks = db.list_all("knowledge_chunks", lambda c: c.get("document_id") == doc["id"])
        doc_cids = set()
        for chk in doc_chunks:
            doc_cids.update(chk.get("concept_ids", []))
        doc["status"] = "processed"
        doc["error_message"] = None
        db.update("documents", doc["id"], doc, save_disk=False)

    db.update("courses", TARGET_COURSE_ID, {
        "concept_count": len(all_final_concepts),
        "topic_count": len(all_final_topics),
        "document_count": len(docs)
    }, save_disk=False)

    # 8. Save State Atomically
    print("\n--- Writing Database Atomically ---")
    db_path = settings.DB_PATH
    temp_path = db_path + f".tmp_{uuid.uuid4().hex[:8]}"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(db.data, f, indent=2, default=str)
    os.replace(temp_path, db_path)
    print(f"Database atomically saved to {db_path}!")

    print("\n" + "=" * 60)
    print("STEP 2 COMPLETE SUMMARY:")
    print(f"  Total Kept Documents: {len(docs)}")
    print(f"  Total Chunks: {len(all_course_chunks)}")
    print(f"  Total Deduplicated Concepts: {len(all_final_concepts)}")
    print(f"  Total Topics: {len(all_final_topics)}")
    print(f"  Prerequisite DAG Edges: {edge_count} (Acyclic: {is_dag})")
    print("=" * 60)

if __name__ == "__main__":
    main()
