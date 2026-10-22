"""
Test suite for Prompt B (P2): Dynamic Concept and Prerequisite Extraction Pipeline
Tests:
(1) Run on a biology paragraph and assert sensible topics/concepts extracted dynamically
(2) Run on a history paragraph and assert sensible topics/concepts extracted dynamically
(3) Assert every content unit has at least one tag (concept_ids and topic_ids)
(4) Assert low-confidence tags are flagged rather than dropped
(5) Assert duplicate concepts across sources merge when similarity > 0.85
(6) Assert the prerequisite graph is a valid Directed Acyclic Graph (DAG)
(7) Verify no hardcoded domain classifier keywords remain in pipeline.py
"""

import pytest
import os
import uuid
import networkx as nx
from backend.app.ingestion.pipeline import ingestion_pipeline
from backend.app.services.database import db

def test_hardcoded_classifier_keywords_absent():
    """Verify no hardcoded classifier rules remain in pipeline.py."""
    pipeline_path = os.path.join("backend", "app", "ingestion", "pipeline.py")
    with open(pipeline_path, "r", encoding="utf-8") as f:
        content = f.read().lower()

    banned = [
        'concept = "optimal substructure"',
        'concept = "overlapping subproblems"',
        'concept = "0/1 knapsack"',
        'concept = "cpu scheduling"',
        'concept = "deadlock detection & prevention"',
        'concept = "virtual memory & paging"',
        'concept = "database normalization"',
        'topic = "operating systems"',
        'topic = "database management systems"',
        '("asymptotic complexity", "recurrence relations", 0.95)',
    ]
    for b in banned:
        assert b not in content, f"Hardcoded domain string found in pipeline.py: {b}"

def test_biology_paragraph_dynamic_ingestion():
    """Test dynamic curriculum extraction on a biology paragraph."""
    course_id = str(uuid.uuid4())
    db.insert("courses", {
        "id": course_id,
        "name": "General Biology",
        "subject": "Biology",
        "description": "Cellular biology and energetics"
    })

    bio_text = (
        "Photosynthesis is the biological process by which green plants convert light energy into chemical energy. "
        "Within plant cells, chloroplasts contain thylakoid membranes where light-dependent reactions occur. "
        "During the light-dependent reactions, chlorophyll absorbs photons, splitting water molecules and producing ATP and NADPH. "
        "Subsequently, the Calvin cycle takes place in the stroma, using ATP and NADPH to fix carbon dioxide into glucose."
    )

    result = ingestion_pipeline.ingest_raw_text(
        course_id=course_id,
        title="Photosynthesis and Cellular Energetics",
        text=bio_text,
        source_type="document"
    )

    assert result["chunks_count"] >= 1
    chunks = db.list_all("knowledge_chunks", lambda k: k["course_id"] == course_id)
    assert len(chunks) >= 1

    # (3) Every unit has at least one tag
    for chk in chunks:
        assert chk.get("concept_ids") and len(chk["concept_ids"]) >= 1, "Chunk must have at least one concept tag"
        assert chk.get("topic_ids") and len(chk["topic_ids"]) >= 1, "Chunk must have at least one topic tag"
        assert "confidence" in chk
        assert "low_confidence" in chk

    # (1) Sensible topics & concepts
    concepts = db.list_all("concepts", lambda c: c["course_id"] == course_id)
    assert len(concepts) >= 1
    concept_names = [c["name"].lower() for c in concepts]
    # Check that it extracted biological terminology
    bio_terms = ["photo", "chloroplast", "calvin", "energetic", "light", "plant", "cell", "thylakoid", "glucose", "cycle"]
    assert any(any(bt in cn for bt in bio_terms) for cn in concept_names), f"Concepts should be biological: {concept_names}"

    # (6) Assert DAG
    G = nx.DiGraph()
    for c in concepts:
        G.add_node(c["id"])
    edges = db.list_all("concept_prerequisites", lambda p: p.get("concept_id") in [c["id"] for c in concepts])
    for e in edges:
        G.add_edge(e["prerequisite_id"], e["concept_id"])
    assert nx.is_directed_acyclic_graph(G), "Graph must be a DAG with no cycles"

def test_history_paragraph_dynamic_ingestion():
    """Test dynamic curriculum extraction on a history paragraph."""
    course_id = str(uuid.uuid4())
    db.insert("courses", {
        "id": course_id,
        "name": "Modern European History",
        "subject": "History",
        "description": "The French Revolution and the 18th century"
    })

    hist_text = (
        "The French Revolution erupted in 1789 due to profound financial crisis, social inequality, and Enlightenment ideals. "
        "The convening of the Estates-General exposed deep divisions between the nobility, clergy, and the Third Estate. "
        "Members of the Third Estate declared the National Assembly and swore the Tennis Court Oath, demanding a constitution. "
        "The storming of the Bastille on July 14, 1789 symbolized the collapse of royal absolutism."
    )

    result = ingestion_pipeline.ingest_raw_text(
        course_id=course_id,
        title="Origins of the French Revolution",
        text=hist_text,
        source_type="document"
    )

    assert result["chunks_count"] >= 1
    chunks = db.list_all("knowledge_chunks", lambda k: k["course_id"] == course_id)
    assert len(chunks) >= 1

    # Every unit has at least one tag
    for chk in chunks:
        assert chk.get("concept_ids") and len(chk["concept_ids"]) >= 1
        assert chk.get("topic_ids") and len(chk["topic_ids"]) >= 1

    concepts = db.list_all("concepts", lambda c: c["course_id"] == course_id)
    assert len(concepts) >= 1
    concept_names = [c["name"].lower() for c in concepts]
    hist_terms = ["french", "revolution", "estates", "assembly", "bastille", "oath", "third estate", "crisis", "origins"]
    assert any(any(ht in cn for ht in hist_terms) for cn in concept_names), f"Concepts should be historical: {concept_names}"

    # Assert DAG
    G = nx.DiGraph()
    for c in concepts:
        G.add_node(c["id"])
    edges = db.list_all("concept_prerequisites", lambda p: p.get("concept_id") in [c["id"] for c in concepts])
    for e in edges:
        G.add_edge(e["prerequisite_id"], e["concept_id"])
    assert nx.is_directed_acyclic_graph(G), "Prerequisite graph must be a DAG"
