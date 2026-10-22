import os
import tempfile
import pytest
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.models.schemas import PrerequisiteEdge
from backend.app.services.ingestion_tracker import ingestion_tracker
from eval.fixtures.sample_loader import DEMO_COURSE_ID

def test_phase1_ingestion_progress_tracker():
    task_id = "test_progress_123"
    ingestion_tracker.init_task(task_id, "sample_lecture.pdf", total_stages=9)
    prog = ingestion_tracker.get_progress(task_id)
    assert prog is not None
    assert prog["task_id"] == task_id
    assert prog["progress_pct"] == 5

    ingestion_tracker.update_stage(task_id, 3, "Extracting text and bboxes", 35)
    prog = ingestion_tracker.get_progress(task_id)
    assert prog["stage_index"] == 3
    assert prog["progress_pct"] == 35

    ingestion_tracker.complete_task(task_id, {"chunks_count": 12})
    prog = ingestion_tracker.get_progress(task_id)
    assert prog["status"] == "completed"
    assert prog["progress_pct"] == 100

def test_phase1_pydantic_prerequisite_edge_validation():
    edge = PrerequisiteEdge(
        concept="Optimal Substructure",
        prerequisite_of="0/1 Knapsack",
        confidence=0.92,
        reason="Knapsack builds upon optimal substructure"
    )
    assert edge.concept == "Optimal Substructure"
    assert edge.prerequisite_of == "0/1 Knapsack"
    assert edge.confidence == 0.92

    # Validation failure for confidence out of range
    with pytest.raises(Exception):
        PrerequisiteEdge(concept="A", prerequisite_of="B", confidence=1.5)

def test_phase1_networkx_prerequisite_dag():
    import networkx as nx
    G = nx.DiGraph()
    G.add_edge("c1", "c2", weight=0.95)
    G.add_edge("c2", "c3", weight=0.90)
    assert nx.is_directed_acyclic_graph(G)
    # Check topological order
    order = list(nx.topological_sort(G))
    assert order == ["c1", "c2", "c3"]

def test_phase1_pipeline_text_document_layout_chunks():
    pipeline = IngestionPipeline()
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("# Topic 1: Algorithms\n\nDynamic programming solves problems by caching overlapping subproblems.\n\n# Topic 2: Graphs\n\nDijkstra algorithm finds shortest paths.")
        temp_path = f.name

    try:
        import uuid
        fname = f"sample_doc_{uuid.uuid4().hex[:6]}.txt"
        res = pipeline.process_file(DEMO_COURSE_ID, temp_path, fname)
        assert res["status"] in ["processed", "already_indexed"]
        assert res["chunks_count"] >= 2
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
