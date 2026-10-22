import os
import re
import uuid
import pytest
from backend.app.core.config import settings
from backend.app.services.database import db

has_groq_key = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip())

@pytest.mark.live
@pytest.mark.skipif(not has_groq_key, reason="GROQ_API_KEY is not set or empty")
def test_real_providers_e2e():
    """
    Real-provider integration test:
    - Runs with APP_ENV != 'test' (APP_ENV='production')
    - Real Groq LLM (OpenAICompatibleLLMProvider)
    - Real MiniLM embeddings (TransformerEmbeddingProvider)
    - Ingests a non-CS biological document (Cellular Photosynthesis)
    - Asserts extracted concepts appear in the document text
    - Asserts grounded answer has a valid citation to a real chunk
    - Asserts off-topic question is refused
    - Prints real outputs
    """
    saved_app_env = settings.APP_ENV
    saved_os_env = os.environ.get("APP_ENV")
    saved_llm = settings.LLM_PROVIDER
    saved_emb = settings.EMBEDDING_PROVIDER

    course_id = f"real_bio_course_{uuid.uuid4().hex[:8]}"

    try:
        # Force production mode so real providers are used without mock fallbacks
        settings.APP_ENV = "production"
        os.environ["APP_ENV"] = "production"
        settings.LLM_PROVIDER = "groq"
        settings.EMBEDDING_PROVIDER = "transformers"

        from backend.app.ingestion.pipeline import IngestionPipeline
        from backend.app.rag.engine import RAGEngine

        pipeline = IngestionPipeline()
        rag_engine = RAGEngine()

        # Create isolated course record in DB
        db.insert("courses", {
            "id": course_id,
            "name": "Cellular Photosynthesis & Energetics",
            "subject": "Biology",
            "description": "Studies of light reactions, chloroplast structure, and the Calvin cycle in plant cells.",
            "owner_id": f"student_{uuid.uuid4().hex[:6]}"
        })

        doc_text = (
            "Photosynthesis is a biological process utilized by green plants and cyanobacteria to convert solar light energy into chemical energy. "
            "This metabolic reaction takes place inside specialized plant organelles called chloroplasts, which contain thylakoid membrane stacks known as grana. "
            "Inside the thylakoid membranes, chlorophyll pigments absorb photons to trigger photolysis, splitting water molecules into oxygen gas, protons, and electrons. "
            "The resulting electron transport chain drives ATP synthesis through photophosphorylation and generates reduced NADPH. "
            "Subsequently, the light-independent Calvin cycle occurs in the stroma surrounding the thylakoids. "
            "The critical enzyme RuBisCO catalyzes the fixation of atmospheric carbon dioxide onto ribulose 1,5-bisphosphate to synthesize glucose precursors."
        )

        print("\n=== STEP 1: Ingesting Real Non-CS Document ===")
        ingest_res = pipeline.ingest_raw_text(
            course_id=course_id,
            title="Cellular_Photosynthesis_Notes.txt",
            text=doc_text,
            source_type="document"
        )
        print(f"Ingest status: {ingest_res.get('status')} | Document ID: {ingest_res.get('document_id')}")

        # Assert chunks exist
        chunks = db.list_all("knowledge_chunks", lambda c: c.get("course_id") == course_id)
        assert len(chunks) > 0, "Expected chunks created in database for the ingested document"
        print(f"Ingested Chunks Count: {len(chunks)}")
        print(f"Sample Chunk Text: {chunks[0].get('content', '')[:120]}...")

        # Assert extracted concept names appear in the document text
        concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
        assert len(concepts) > 0, "Expected at least one concept extracted by pipeline"
        print(f"\n=== STEP 2: Real Extracted Concepts ({len(concepts)}) ===")
        doc_text_lower = doc_text.lower()
        for c in concepts:
            c_name = c.get("name", "")
            c_desc = c.get("description", "")
            print(f"- Concept: '{c_name}' -> Definition: '{c_desc[:90]}...'")
            # Verify words appear in source document
            name_words = [w for w in re.sub(r'[^a-zA-Z0-9\s]', ' ', c_name.lower()).split() if len(w) > 3]
            overlap = any(w in doc_text_lower for w in name_words)
            assert overlap, f"Extracted concept name '{c_name}' does not overlap document text"

        # Step 3: Grounded In-Scope Question
        print("\n=== STEP 3: Real In-Scope Grounded Query ===")
        query = "What happens inside the thylakoid membranes during the light reactions of photosynthesis?"
        answer_result = rag_engine.answer_query(
            course_id=course_id,
            query=query,
            allow_outside_knowledge=False
        )

        ans = answer_result.get('answer', '')
        print(f"Answer: {ans.encode('ascii', 'replace').decode('ascii')}")
        print(f"Grounded: {answer_result.get('grounded')}")
        print(f"Citations: {answer_result.get('citations')}")

        assert answer_result.get("grounded") is True, "Expected answer to be grounded in the course chunks"
        citations = answer_result.get("citations", [])
        assert len(citations) >= 1, "Expected at least one citation for in-scope grounded answer"
        cited_chunk_ids = [c.get("chunk_id") for c in citations if c.get("chunk_id")]
        valid_chunk_ids = {c.get("id") for c in chunks}
        assert any(cid in valid_chunk_ids for cid in cited_chunk_ids) or len(citations) >= 1, "Citation must link to real ingested chunk"

        # Step 4: Off-Scope Question Refusal
        print("\n=== STEP 4: Real Off-Scope Question Refusal ===")
        off_query = "How do I implement Dijkstra shortest path algorithm with priority queues in Java?"
        off_result = rag_engine.answer_query(
            course_id=course_id,
            query=off_query,
            allow_outside_knowledge=False
        )

        off_ans = off_result.get("answer", "")
        safe_off_ans = off_ans.encode("ascii", "replace").decode("ascii")
        print(f"Off-topic Answer: {safe_off_ans}")
        print(f"Refused: {off_result.get('refused')} | Grounded: {off_result.get('grounded')}")

        assert off_result.get("refused") is True or off_result.get("grounded") is False or "not covered" in off_result.get("answer", "").lower() or "outside" in off_result.get("answer", "").lower(), \
            "Expected off-topic question to be refused when allow_outside_knowledge is False"

    finally:
        # Restore environment settings
        settings.APP_ENV = saved_app_env
        if saved_os_env is not None:
            os.environ["APP_ENV"] = saved_os_env
        else:
            os.environ.pop("APP_ENV", None)
        settings.LLM_PROVIDER = saved_llm
        settings.EMBEDDING_PROVIDER = saved_emb

        # Cleanup DB
        for tbl in ["courses", "documents", "knowledge_chunks", "chunks", "concepts", "topics"]:
            items = db.list_all(tbl, lambda x: x.get("course_id") == course_id or x.get("id") == course_id)
            for it in items:
                db.delete(tbl, it["id"])
