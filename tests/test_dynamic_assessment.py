"""
Test suite for Prompt A (P1): Fully Dynamic Question Synthesis & Verification Pipeline
Tests:
(a) a deliberately wrong key is rejected
(b) a paraphrased repeat is blocked (cosine similarity > 0.85)
(c) generation works on a non-CS text sample (e.g. Biology / Photosynthesis)
(d) grep / code inspection proves zero hardcoded concept-name strings remain in generator.py
"""

import pytest
import os
import re
from backend.app.assessment.generator import (
    _verify_numerical_expression,
    _verify_supporting_quote,
    _check_deduplication,
    synthesize_question,
    assessment_engine,
)
from backend.app.services.database import db

def test_hardcoded_concept_strings_absent():
    """Verify zero hardcoded concept names remain in generator.py."""
    generator_path = os.path.join("backend", "app", "assessment", "generator.py")
    with open(generator_path, "r", encoding="utf-8") as f:
        content = f.read().lower()

    # Former hardcoded concept substrings that must never appear as hardcoded question triggers
    banned_substrings = [
        "optimal substructure",
        "memoization",
        "knapsack",
        "fractional knapsack",
        "greedy choice",
        "subproblem overlap",
        "deadlock",
        "coffman",
        "round robin",
        "shortest job first",
        "bcnf",
        "third normal form",
        "tcp 3-way",
        "syn-ack",
        "three-way handshake",
        "cpu scheduling",
        "page replacement",
    ]

    for banned in banned_substrings:
        assert banned not in content, f"Hardcoded domain string '{banned}' found in generator.py!"

def test_deliberately_wrong_numerical_key_rejected():
    """(a) Test that a question with a wrong numerical answer fails verification."""
    # Expression produces 42, but claimed answer is 99
    valid, reason = _verify_numerical_expression("6 * 7", "99")
    assert not valid, "Numerical verification should reject mathematically wrong answer"
    assert "Discrepancy" in reason or "Numerical mismatch" in reason

    # Correct one passes
    valid_ok, reason_ok = _verify_numerical_expression("6 * 7", "42")
    assert valid_ok, f"Numerical verification should accept 42: {reason_ok}"

def test_deliberately_wrong_quote_rejected():
    """(a) Test that supporting quote not in unit text fails verification."""
    unit_text = "Photosynthesis takes place primarily inside chloroplasts containing chlorophyll pigments."
    fake_quote = "Mitochondria produce ATP through oxidative phosphorylation."
    valid, reason = _verify_supporting_quote(fake_quote, unit_text)
    assert not valid
    assert "Supporting quote not found" in reason

def test_paraphrased_repeat_blocked():
    """(b) Test that an identical or highly similar question stem is blocked (> 0.85 similarity)."""
    original_stem = "What organelle is responsible for photosynthesis in plant cells?"
    paraphrased_stem = "Which cellular organelle is responsible for photosynthesis in plant cells?"
    
    # Check deduplication with original in history
    history = [original_stem]
    is_duplicate, score = _check_deduplication(paraphrased_stem, history)
    assert is_duplicate, f"Paraphrased repeat should be blocked! Score: {score}"
    assert score > 0.85

def test_generation_on_non_cs_sample():
    """(c) Test generation on a non-CS text sample (Biology / Cellular Respiration)."""
    biology_unit = {
        "id": "bio-chunk-1",
        "source_id": "bio-textbook-ch4",
        "content": (
            "During cellular respiration, glycolysis converts one molecule of glucose into two molecules of pyruvate. "
            "This anaerobic process occurs in the cytoplasm and yields a net gain of 2 ATP molecules and 2 NADH molecules per glucose."
        ),
        "location": {"page": 84, "chapter": 4},
    }

    import uuid
    q = synthesize_question(
        content_unit=biology_unit,
        target_concept="Glycolysis",
        question_type="mcq",
        difficulty=2,
        course_id=f"test_bio_{uuid.uuid4().hex[:6]}"
    )

    assert q is not None, "synthesize_question should return a verified question dict"
    stem = q.get("question_text", "")
    assert len(stem) > 10
    options = q.get("options", [])
    assert len(options) >= 2
    assert q.get("verification_status") == "verified"
    assert q.get("source_location") == "Page 84"
    assert "Glycolysis" in q.get("concept_ids", [])
