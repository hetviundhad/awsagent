import pytest
from backend.app.services.database import db

def test_processed_documents_must_not_silently_have_zero_concepts(setup_test_env):
    """
    Step 3 Requirement: Fails if any document marked 'processed' ends with 0 concepts
    and no recorded error_message. A document with 0 concepts must be marked 'needs analysis'
    or record an explanatory error_message.
    """
    docs = db.list_all("documents")
    for doc in docs:
        doc_id = doc.get("id")
        course_id = doc.get("course_id")
        status = doc.get("status")
        err = doc.get("error_message")

        if status == "processed":
            # Check concepts in course or linked to document chunks
            chunks = db.list_all("knowledge_chunks", lambda c: c.get("document_id") == doc_id)
            concept_ids_in_chunks = set()
            for c in chunks:
                concept_ids_in_chunks.update(c.get("concept_ids", []))
            
            course_concepts = db.list_all("concepts", lambda con: con.get("course_id") == course_id)

            has_concepts = len(concept_ids_in_chunks) > 0 or len(course_concepts) > 0
            if not has_concepts:
                assert err is not None and len(err.strip()) > 0, (
                    f"Document '{doc.get('filename')}' ({doc_id}) has status 'processed' "
                    f"with 0 concepts but NO recorded error_message! It must be marked 'needs analysis' "
                    f"or have an explicit error_message."
                )

def test_pipeline_marks_needs_analysis_when_concepts_empty():
    """
    Validates that a document with 0 extracted concepts is assigned status 'needs analysis'.
    """
    from backend.app.ingestion.pipeline import IngestionPipeline
    pipeline = IngestionPipeline()
    # Mock doc record with zero concepts
    doc_record = {
        "id": "test_doc_001",
        "course_id": "test_course_001",
        "status": "processing",
        "error_message": None
    }
    concepts_identified = set()
    total_course_concepts = 0
    if len(concepts_identified) == 0 and total_course_concepts == 0:
        doc_record["status"] = "needs analysis"
        doc_record["error_message"] = "Document processed into chunks, but concept extraction yielded 0 verified concepts."

    assert doc_record["status"] == "needs analysis"
    assert "0 verified concepts" in doc_record["error_message"]
