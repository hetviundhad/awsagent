import os
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from backend.app.services.database import db

SAMPLE_COURSE_ID = "sample-algorithms-course-2026"
DEMO_COURSE_ID = SAMPLE_COURSE_ID

def seed_sample_course_if_needed(force: bool = False, parent_task_id: Optional[str] = None, owner_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Optional sample data loader (labelled 'Sample data') for evaluation and testing.
    Loads structured sample data from eval/fixtures/sample_course.json.
    """
    existing_course = db.get_by_id("courses", SAMPLE_COURSE_ID)
    if existing_course and not force:
        return existing_course

    # Load fixture json
    fixture_path = os.path.join(os.path.dirname(__file__), "sample_course.json")
    course_meta = {
        "name": "[Sample data] Data Structures and Algorithms",
        "description": "Comprehensive sample course covering data structures, asymptotic analysis, dynamic programming, and greedy techniques. [Sample data]",
        "subject": "Computer Science",
        "semester": "Fall 2026"
    }
    units_data = []
    topics_data = []
    concepts_data = []
    questions_data = []

    if os.path.exists(fixture_path):
        try:
            with open(fixture_path, "r", encoding="utf-8") as f:
                fix = json.load(f)
                course_meta.update(fix.get("course", {}))
                units_data = fix.get("course_units", [])
                topics_data = fix.get("topics", [])
                concepts_data = fix.get("concepts", [])
                questions_data = fix.get("questions", [])
        except Exception:
            pass

    course = {
        "id": SAMPLE_COURSE_ID,
        "owner_id": owner_id or "default_student",
        "name": course_meta.get("name", "[Sample data] Algorithms"),
        "description": course_meta.get("description", "Sample course data"),
        "subject": course_meta.get("subject", "Computer Science"),
        "semester": course_meta.get("semester", "Fall 2026"),
        "exam_date": "2026-11-20",
        "created_at": datetime.now().isoformat(),
        "document_count": 2,
        "topic_count": max(len(topics_data), 3),
        "concept_count": max(len(concepts_data), 3),
        "overall_mastery": 0.0,
        "is_sample": True
    }
    db.insert("courses", course)

    # Insert sample document records
    sample_docs = [
        {"id": f"doc_{SAMPLE_COURSE_ID}_1", "course_id": SAMPLE_COURSE_ID, "filename": "Algorithms.pdf", "file_type": "pdf", "page_count": 120},
        {"id": f"doc_{SAMPLE_COURSE_ID}_2", "course_id": SAMPLE_COURSE_ID, "filename": "Lecture 6 Slides.pptx", "file_type": "pptx", "page_count": 35}
    ]
    for d in sample_docs:
        db.insert("documents", d)

    # Insert sample course units
    if not units_data:
        units_data = [
            {"title": "Unit 1: Foundations & Asymptotics (Sample data)", "order": 1, "description": "Big-O and analysis"},
            {"title": "Unit 2: Divide and Conquer (Sample data)", "order": 2, "description": "Recurrence relations"},
            {"title": "Unit 3: Dynamic Programming (Sample data)", "order": 3, "description": "Optimal substructure and memoization"}
        ]
    for idx, u in enumerate(units_data, 1):
        db.insert("course_units", {
            "id": f"unit_{SAMPLE_COURSE_ID}_{idx}",
            "course_id": SAMPLE_COURSE_ID,
            "unit_number": idx,
            "title": u.get("title", f"Unit {idx}"),
            "description": u.get("description", "")
        })

    # Insert sample concepts with prerequisites
    base_case_id = f"c_{SAMPLE_COURSE_ID}_base_cases"
    optimal_sub_id = f"c_{SAMPLE_COURSE_ID}_optimal_substructure"
    knapsack_id = f"c_{SAMPLE_COURSE_ID}_knapsack"

    sample_concepts = [
        {"id": base_case_id, "name": "Base Cases", "description": "Foundational terminating condition for recursion.", "course_id": SAMPLE_COURSE_ID},
        {"id": optimal_sub_id, "name": "Optimal Substructure", "description": "An optimal solution contains within it optimal solutions to subproblems.", "course_id": SAMPLE_COURSE_ID},
        {"id": knapsack_id, "name": "0/1 Knapsack", "description": "Dynamic programming knapsack decision recurrence.", "course_id": SAMPLE_COURSE_ID}
    ]
    for c in sample_concepts:
        db.insert("concepts", c)

    # Prerequisites
    db.insert("concept_prerequisites", {
        "id": f"pr_{SAMPLE_COURSE_ID}_1",
        "course_id": SAMPLE_COURSE_ID,
        "concept_id": knapsack_id,
        "prerequisite_id": optimal_sub_id,
        "weight": 0.95
    })
    db.insert("concept_prerequisites", {
        "id": f"pr_{SAMPLE_COURSE_ID}_2",
        "course_id": SAMPLE_COURSE_ID,
        "concept_id": optimal_sub_id,
        "prerequisite_id": base_case_id,
        "weight": 0.90
    })

    # Sample knowledge chunks
    sample_chunks = [
        {
            "id": f"chk_{SAMPLE_COURSE_ID}_1",
            "course_id": SAMPLE_COURSE_ID,
            "document_name": "Algorithms.pdf",
            "page_number": 42,
            "content": "A problem has optimal substructure if an optimal solution contains within it optimal solutions to subproblems. Dynamic programming solves problems with optimal substructure and overlapping subproblems.",
            "concept_ids": [optimal_sub_id]
        },
        {
            "id": f"chk_{SAMPLE_COURSE_ID}_2",
            "course_id": SAMPLE_COURSE_ID,
            "document_name": "Lecture 6 Slides.pptx",
            "slide_number": 22,
            "content": "Top-down memoization caches subproblem outputs recursively, while bottom-up tabulation iteratively fills tables from base cases.",
            "concept_ids": [optimal_sub_id, knapsack_id]
        }
    ]
    for chk in sample_chunks:
        db.insert("knowledge_chunks", chk)

    return course

seed_demo_course_if_needed = seed_sample_course_if_needed
