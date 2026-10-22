import pytest
from backend.app.rag.engine import RAGEngine
from backend.app.rag.self_rag import SelfRAGGuardrail
from eval.fixtures.sample_loader import DEMO_COURSE_ID, seed_demo_course_if_needed

@pytest.fixture(autouse=True)
def setup_demo_course():
    seed_demo_course_if_needed()

def test_phase2_hybrid_search_rrf():
    engine = RAGEngine()
    chunks = engine.retrieve_chunks(DEMO_COURSE_ID, "optimal substructure in dynamic programming", top_k=3)
    assert len(chunks) > 0
    # Every chunk should have score and dense_similarity
    for chk in chunks:
        assert "score" in chk
        assert chk["score"] > 0
        assert "dense_similarity" in chk

def test_phase2_self_rag_claim_splitting_and_verification():
    guardrail = SelfRAGGuardrail()
    sample_answer = (
        "Dynamic programming requires optimal substructure and overlapping subproblems. "
        "Memoization is a top-down recursive technique that caches answers. "
        "Quantum superposition allows qubits to factor primes exponentially faster."
    )
    claims = guardrail.split_claims(sample_answer)
    assert len(claims) >= 2

    # Mock retrieved chunks
    mock_chunks = [
        {
            "id": "chk_1",
            "document_name": "Algorithms.pdf",
            "content": "Dynamic programming applies when subproblems overlap and exhibits optimal substructure. Memoization caches recursive calls.",
            "content_summary": "DP Foundations"
        }
    ]

    verifications, unsupported = guardrail.verify_claims(sample_answer, mock_chunks)
    assert len(verifications) > 0
    # First claims should be supported
    assert any(v.supported for v in verifications)
    # Quantum claim should be flagged as unsupported
    assert any(not v.supported for v in verifications)
    assert len(unsupported) > 0

def test_phase2_answer_query_guardrail_gate():
    engine = RAGEngine()
    res = engine.answer_query(
        course_id=DEMO_COURSE_ID,
        query="What is dynamic programming?",
        allow_outside_knowledge=False
    )
    assert res["grounded"] is True
    assert "claims_verification" in res
    assert isinstance(res["claims_verification"], list)
    assert "citations" in res
    # Ensure citations have deep-link fields
    for cit in res["citations"]:
        assert "citation_index" in cit
        assert "source_type" in cit
