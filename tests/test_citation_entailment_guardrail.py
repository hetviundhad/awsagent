import pytest
import uuid
from backend.app.rag.engine import rag_engine
from backend.app.rag.self_rag import self_rag_guardrail
from backend.app.services.database import db

@pytest.fixture
def mock_course():
    c_id = f"test-rag-course-{uuid.uuid4().hex[:8]}"
    db.insert("courses", {
        "id": c_id,
        "name": "Cellular Biology 101",
        "description": "Biological systems, cellular structures, and ATP synthesis",
        "subject": "Biology"
    })
    # Add a knowledge chunk on cellular mitochondria
    doc_id = str(uuid.uuid4())
    db.insert("documents", {
        "id": doc_id,
        "course_id": c_id,
        "filename": "cell_biology_chapter_3.pdf",
        "file_type": "pdf",
        "status": "processed"
    })
    chk_id = str(uuid.uuid4())
    db.insert("knowledge_chunks", {
        "id": chk_id,
        "course_id": c_id,
        "document_id": doc_id,
        "document_name": "cell_biology_chapter_3.pdf",
        "page_number": 42,
        "source_type": "pdf",
        "content": "Mitochondria generate cellular ATP through oxidative phosphorylation across the inner mitochondrial membrane. The electron transport chain creates a proton gradient that drives ATP synthase.",
        "content_summary": "Mitochondria ATP synthesis via oxidative phosphorylation.",
        "embedding": [0.05] * 384
    })
    return c_id

def test_off_topic_question_is_refused(mock_course):
    """
    Test requirement: an off-topic question is refused when outside knowledge is false.
    Must output: refused: bool = True and "This isn't covered in your uploaded material."
    """
    res = rag_engine.answer_query(
        course_id=mock_course,
        query="Explain the Schwarzschild radius of a rotating Kerr black hole in general relativity.",
        allow_outside_knowledge=False
    )
    assert res["refused"] is True, "Off-topic query must be refused"
    assert res["grounded"] is False
    assert "This isn't covered in your uploaded material." in res["answer"]
    assert any(
        "This isn't covered in your uploaded material." in seg.get("text", "")
        for seg in res.get("answer_segments", [])
    )

def test_sourced_answer_has_no_uncited_sentences():
    """
    Test requirement: a sourced answer has NO uncited sentences.
    Every sentence tagged as 'sourced' must have at least one valid citation.
    """
    retrieved_chunks = [
        {
            "id": "chk_mito_01",
            "document_name": "biology_textbook.pdf",
            "source_type": "pdf",
            "page_number": 15,
            "content": "Mitochondria synthesize cellular ATP through oxidative phosphorylation and electron transport chains.",
            "content_summary": "Mitochondria and ATP generation."
        }
    ]

    candidate_answer = (
        "Mitochondria synthesize cellular ATP through oxidative phosphorylation. "
        "The electron transport chains facilitate this biochemical process. "
        "Quantum superposition in subatomic particles enables non-local quantum entanglement."
    )

    # Without outside knowledge allowed, unsupported sentences are dropped
    segments, refused = self_rag_guardrail.segment_and_verify_answer(
        answer=candidate_answer,
        retrieved_chunks=retrieved_chunks,
        allow_outside_knowledge=False
    )

    assert refused is False
    assert len(segments) > 0

    for seg in segments:
        if seg["type"] == "sourced":
            # Strict guarantee: every sourced sentence must have citations
            assert len(seg["citations"]) > 0, f"Uncited sentence found in sourced segment: {seg['text']}"
            assert seg["citations"][0]["document_name"] == "biology_textbook.pdf"

    # Verify the unsupported quantum sentence was dropped from the sourced output
    all_sourced_text = " ".join([s["text"] for s in segments if s["type"] == "sourced"])
    assert "quantum entanglement" not in all_sourced_text.lower(), (
        "Unsupported sentence was not dropped from sourced output!"
    )

def test_outside_knowledge_separation():
    """
    Test requirement: Never interleave outside text inside sourced paragraphs.
    When outside knowledge is allowed, outside sentences are grouped into type='outside' segments.
    """
    retrieved_chunks = [
        {
            "id": "chk_bio_02",
            "document_name": "cell_biology.pdf",
            "source_type": "pdf",
            "page_number": 20,
            "content": "Chloroplasts perform photosynthesis to convert light energy into chemical energy.",
            "content_summary": "Chloroplasts and photosynthesis."
        }
    ]

    mixed_answer = (
        "Chloroplasts perform photosynthesis to convert light energy into chemical energy. "
        "The stock market fluctuates based on macroeconomic interest rate decisions."
    )

    segments, refused = self_rag_guardrail.segment_and_verify_answer(
        answer=mixed_answer,
        retrieved_chunks=retrieved_chunks,
        allow_outside_knowledge=True
    )

    assert refused is False
    sourced_segs = [s for s in segments if s["type"] == "sourced"]
    outside_segs = [s for s in segments if s["type"] == "outside"]

    assert len(sourced_segs) > 0
    assert len(outside_segs) > 0
    # Sourced must have citation, outside must not fabricate citations
    assert len(sourced_segs[0]["citations"]) > 0
    assert len(outside_segs[0]["citations"]) == 0
    assert outside_segs[0]["type"] == "outside"
