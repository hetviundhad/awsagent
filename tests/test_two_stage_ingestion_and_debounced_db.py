import os
import time
import uuid
import pytest
from unittest.mock import patch
from backend.app.services.database import DatabaseManager
from backend.app.services.ingestion_tracker import IngestionProgressTracker
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.rag.engine import RAGEngine

def test_two_stage_readiness_with_slow_llm(tmp_path):
    """
    Asserts Stage A completes before Stage B with a stubbed slow LLM,
    and that the tutor works on chunks between stages.
    """
    temp_db_file = str(tmp_path / "test_stage_db.json")
    test_db = DatabaseManager()
    test_db.db_path = temp_db_file
    test_db.reinit(temp_db_file)

    course_id = str(uuid.uuid4())
    owner_id = "test_student"
    test_db.insert("courses", {
        "id": course_id,
        "owner_id": owner_id,
        "name": "Distributed Systems Test Course",
        "subject": "Computer Science",
        "created_at": "2026-10-13T00:00:00"
    })

    # Create two temporary test documents
    doc1 = tmp_path / "doc1.txt"
    doc1.write_text("Data locality is the optimization technique of moving computational tasks close to where data resides. This minimizes network traffic across compute clusters.", encoding="utf-8")
    doc2 = tmp_path / "doc2.txt"
    doc2.write_text("Cluster resource management handles scheduling and allocation of memory, CPU, and GPUs across nodes in parallel systems.", encoding="utf-8")

    files_data = [
        {"filename": "doc1.txt", "file_path": str(doc1), "bytes": doc1.read_bytes()},
        {"filename": "doc2.txt", "file_path": str(doc2), "bytes": doc2.read_bytes()},
    ]

    pipeline = IngestionPipeline()
    rag = RAGEngine()

    # Stub slow LLM in curriculum extraction
    orig_extract = pipeline._extract_curriculum_structure
    def slow_extract_stub(*args, **kwargs):
        time.sleep(0.8) # simulate slow LLM
        return orig_extract(*args, **kwargs)

    with patch.object(pipeline, "_extract_curriculum_structure", side_effect=slow_extract_stub), \
         patch("backend.app.ingestion.pipeline.db", test_db), \
         patch("backend.app.rag.engine.db", test_db), \
         patch("backend.app.services.database.db", test_db):

        t0 = time.perf_counter()
        res = pipeline.process_course_documents(
            course_id=course_id,
            files_data=files_data,
            task_id="test_task_stage_a",
            owner_id=owner_id,
            sync_stage_b=False # runs stage B in background thread
        )
        t_stage_a = time.perf_counter() - t0

        # Assert Stage A returns immediately before Stage B completes
        assert res.get("stage_a_ready") is True
        assert res.get("chunks_count") > 0
        assert t_stage_a < 0.7 # Stage A must finish well before the 0.8s slow LLM

        # Assert tutor works on real chunks between Stage A and Stage B
        ans = rag.answer_query(
            course_id=course_id,
            query="What is the concept of data locality in distributed processing?",
            owner_id=owner_id,
            allow_outside_knowledge=False
        )
        assert ans.get("grounded") is True
        assert len(ans.get("citations", [])) > 0

        # Wait for background Stage B to complete while test_db remains patched
        concepts = []
        for _ in range(180):
            concepts = test_db.list_all("concepts", lambda c: c.get("course_id") == course_id)
            if concepts:
                break
            time.sleep(0.5)
        assert len(concepts) > 0

def test_debounced_persistence_and_crash_resilience(tmp_path):
    """
    Asserts debounced persistence prevents excessive writes, writes final state on flush,
    and survives simulated crashes with atomic temp file + os.replace.
    """
    db_file = str(tmp_path / "debounce_test.json")
    mgr = DatabaseManager()
    mgr.db_path = db_file
    mgr.reinit(db_file)

    # 1. Rapid successive writes should not trigger multiple disk saves
    t_start = mgr.total_save_state_time
    count_start = mgr.save_state_count

    for i in range(10):
        mgr.insert("courses", {"id": f"c_{i}", "name": f"Course {i}"}, save_disk=True)

    # Within debounce window, disk save should be deferred/debounced
    assert mgr.save_state_count <= count_start + 2

    # Flush guarantees persistence
    mgr.flush()
    assert os.path.exists(db_file)
    assert mgr.get_by_id("courses", "c_9") is not None

    # 2. Crash resilience: simulated crash while temp file exists
    temp_corrupt = f"{db_file}.tmp_corrupt_crash"
    with open(temp_corrupt, "w") as f:
        f.write("{ incomplete_broken_json")

    # Target DB must remain valid and uncorrupted
    mgr_reload = DatabaseManager()
    mgr_reload.db_path = db_file
    mgr_reload.reinit(db_file)
    assert mgr_reload.get_by_id("courses", "c_9") is not None

    if os.path.exists(temp_corrupt):
        os.remove(temp_corrupt)

def test_progress_stream_reports_per_doc_and_stage():
    """
    Asserts progress tracker reports per-document status and per-stage status.
    """
    tracker = IngestionProgressTracker()
    task_id = "test_progress_stream_task"
    filenames = ["doc_alpha.pdf", "doc_beta.pptx"]

    tracker.init_multi_doc_task(task_id, filenames, "course_123")
    state = tracker.get_progress(task_id)

    assert state is not None
    assert state["task_id"] == task_id
    assert state["status"] == "processing"
    assert "doc_alpha.pdf" in state["documents"]
    assert state["documents"]["doc_alpha.pdf"]["status"] == "queued"

    # Update individual document
    tracker.update_doc_status(task_id, "doc_alpha.pdf", "extracting")
    state = tracker.get_progress(task_id)
    assert state["documents"]["doc_alpha.pdf"]["status"] == "extracting"

    # Mark stage A ready
    tracker.mark_stage_a_ready(task_id, "course_123", chunks_count=18, elapsed_seconds=4.2)
    state = tracker.get_progress(task_id)
    assert state["stage_a_ready"] is True
    assert state["status"] == "ready_for_study"

    # Complete task
    tracker.complete_task(task_id, {"concepts_count": 12})
    state = tracker.get_progress(task_id)
    assert state["status"] == "completed"
    assert state["progress_pct"] == 100
