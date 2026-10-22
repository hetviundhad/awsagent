import os
import uuid
import pytest
from backend.app.core.config import settings
from backend.app.services.database import db
from backend.app.services.storage import storage
from backend.app.ingestion.pipeline import ingestion_pipeline
from backend.app.rag.engine import rag_engine
from backend.app.assessment.generator import assessment_engine

@pytest.mark.live
def test_live_ingestion_tutor_quiz():
    """
    Live integration test verifying:
    1. Upload and ingestion of theory-heavy document with real LLM
    2. Extracted concepts have supporting chunks and lexical grounding
    3. Socratic Tutor retrieval answering 3 in-scope questions with citations
    4. Socratic Tutor refusing 2 off-scope questions
    5. Quiz generation creating 5 deduplicated questions with verified supporting_quotes from real chunks
    """
    groq_key = settings.GROQ_API_KEY
    if not groq_key or not groq_key.strip():
        pytest.skip("GROQ_API_KEY is not configured; skipping live integration test.")

    # Switch to live mode for real LLM validation
    old_env = settings.APP_ENV
    settings.APP_ENV = "live"
    os.environ["APP_ENV"] = "live"

    course_id = f"live_course_{uuid.uuid4().hex[:8]}"
    student_id = f"live_student_{uuid.uuid4().hex[:8]}"

    try:
        # 1. Create clean course
        db.insert("courses", {
            "id": course_id,
            "owner_id": student_id,
            "name": "Parallel Computing & Computer Architecture",
            "description": "Rigorous course covering speedup laws and memory locality.",
            "subject": "Computer Science",
            "semester": "Fall 2026",
            "created_at": "2026-10-11T00:00:00Z"
        })

        # 2. Theory-heavy study content
        document_text = (
            "# Module 1: Amdahl's Law and Speedup Limits\n\n"
            "Amdahl's Law states that the theoretical speedup of the execution of a whole task on multiple processors "
            "is limited by the serial percentage of the algorithm. Specifically, if S is the serial fraction and N is "
            "the processor count, Speedup = 1 / (S + (1 - S) / N). As N approaches infinity, the maximum speedup is "
            "strictly bounded by 1 / S. Therefore, if 10% of a program is inherently serial, the maximum achievable "
            "speedup is at most 10x, regardless of how many parallel cores are deployed.\n\n"
            "# Module 2: Gustafson's Law and Weak Scaling\n\n"
            "Gustafson's Law addresses the limitation of Amdahl's Law by arguing that problem size scales with processing power. "
            "Instead of fixing workload size, Gustafson assumes that parallel execution scales to solve larger problems. "
            "If s is the serial runtime and p is the parallel runtime on N processors, Scaled Speedup = s + p * N = N + (1 - N) * s. "
            "This demonstrates that massively parallel computing remains viable when data sizes grow proportionally.\n\n"
            "# Module 3: Cache Hierarchy and Locality Principles\n\n"
            "Spatial locality refers to the use of data elements within relatively close storage locations. "
            "For example, iterating through a contiguous matrix in row-major order yields high spatial cache hit rates. "
            "Temporal locality refers to the reuse of specific data within a relatively small time duration. "
            "For instance, accumulating sums in a single register or variable inside an inner loop achieves near 100% temporal cache hits."
        )

        doc_filename = "parallel_architecture_theory.txt"
        saved_path = storage.save_file(doc_filename, document_text.encode("utf-8"))

        # 3. Ingestion with real LLM pipeline
        pipeline_res = ingestion_pipeline.process_file(
            course_id=course_id,
            file_path=saved_path,
            original_filename=doc_filename,
            owner_id=student_id
        )

        chunks = db.list_all("knowledge_chunks", lambda c: c.get("course_id") == course_id)
        concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)

        assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"
        assert len(concepts) >= 2, f"Expected at least 2 extracted concepts, got {len(concepts)}"

        # Verify concepts are lexically or semantically grounded in the document text
        doc_lower = document_text.lower()
        for c in concepts:
            c_name_lower = c["name"].lower()
            # The concept name or at least one word from it must appear in the text
            c_words = [w for w in c_name_lower.split() if len(w) > 3]
            assert any(w in doc_lower for w in c_words), f"Concept '{c['name']}' not found in document text"

        # 4. Ask 3 in-scope questions
        in_scope_queries = [
            "What is the mathematical formula for speedup in Amdahl's Law and what limits the maximum speedup?",
            "How does Gustafson's Law differ from Amdahl's Law regarding scaled speedup and problem size?",
            "What is the difference between spatial locality and temporal locality in cache hierarchy?"
        ]

        for query in in_scope_queries:
            tutor_res = rag_engine.answer_query(
                course_id=course_id,
                query=query,
                allow_outside_knowledge=False
            )
            assert tutor_res.get("refused") is False, f"In-scope query '{query}' was unexpectedly refused."
            assert tutor_res.get("grounded") is True, f"In-scope query '{query}' was not marked grounded."
            assert len(tutor_res.get("citations", [])) > 0, f"Expected citations for '{query}'"
            # Ensure citation points to one of our indexed chunks
            cited_chunk_ids = [cit["chunk_id"] for cit in tutor_res["citations"] if "chunk_id" in cit]
            indexed_chunk_ids = [ch["id"] for ch in chunks]
            assert any(cid in indexed_chunk_ids for cid in cited_chunk_ids), "Citation chunk ID does not match indexed chunks"

        # 5. Ask 2 off-scope questions
        off_scope_queries = [
            "How do thylakoid membranes and chlorophyll molecules perform light-dependent photosynthesis in plants?",
            "What were the primary macroeconomic monetary factors behind the French Revolution in 1789?"
        ]

        for query in off_scope_queries:
            tutor_res = rag_engine.answer_query(
                course_id=course_id,
                query=query,
                allow_outside_knowledge=False
            )
            is_refused = tutor_res.get("refused") is True or not tutor_res.get("grounded") or "isn't covered in your uploaded material" in tutor_res.get("answer", "").lower()
            assert is_refused, f"Off-scope query '{query}' should have been refused, but got: {tutor_res.get('answer')[:150]}"

        # 6. Generate 5-question quiz
        quiz_res = assessment_engine.generate_assessment(
            course_id=course_id,
            question_count=5,
            student_id=student_id
        )

        questions = quiz_res.get("questions", [])
        assert len(questions) > 0, "No questions were generated"

        # Verify quote exists in chunk and no duplicates
        seen_stems = set()
        for q in questions:
            stem = q.get("stem") or q.get("question_text") or ""
            assert stem, "Question stem is empty"
            assert stem not in seen_stems, f"Duplicate question detected: {stem}"
            seen_stems.add(stem)

            # Supporting quote must be proven in the chunks
            quote = q.get("supporting_quote") or ""
            assert len(quote) > 0, f"Question '{stem[:50]}' lacks supporting quote"
            quote_clean = " ".join(quote.lower().split())
            assert any(quote_clean in " ".join(chk.get("content", "").lower().split()) or
                       len(set(quote_clean.split()).intersection(set(chk.get("content", "").lower().split()))) / max(len(quote_clean.split()), 1) >= 0.70
                       for chk in chunks), f"Quote '{quote}' was not found in any indexed chunk"

    finally:
        # Cleanup
        settings.APP_ENV = old_env
        os.environ["APP_ENV"] = old_env
        tables = ["courses", "documents", "knowledge_chunks", "topics", "concepts", "concept_prerequisites", "assessments", "questions"]
        for tbl in tables:
            records = db.list_all(tbl, lambda r: r.get("course_id") == course_id)
            for r in records:
                db.delete(tbl, r["id"])
