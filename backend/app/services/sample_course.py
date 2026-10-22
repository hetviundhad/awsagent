"""
Sample course loader service.
Loads sample fixture data from eval/fixtures/sample_course.json for a user.
Strictly labelled 'Sample data' and scoped to the logged-in user.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from backend.app.services.database import db

FIXTURES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "eval", "fixtures", "sample_course.json"))

def load_sample_course_for_user(user_id: str) -> Dict[str, Any]:
    """
    Loads sample course from eval/fixtures/sample_course.json for the specified user.
    All entities are created with fresh IDs and tagged with user_id and '[Sample data]'.
    """
    if not os.path.exists(FIXTURES_PATH):
        raise FileNotFoundError(f"Sample fixture not found at {FIXTURES_PATH}")

    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        fixture = json.load(f)

    now_iso = datetime.now().isoformat()
    c_meta = fixture.get("course", {})
    course_id = f"sample_course_{uuid.uuid4().hex[:8]}"

    course_record = {
        "id": course_id,
        "owner_id": user_id,
        "name": c_meta.get("name", "Sample Course (Sample data)"),
        "description": c_meta.get("description", "Sample course dataset [Sample data]"),
        "subject": c_meta.get("subject", "General"),
        "semester": c_meta.get("semester", "Sample 2026"),
        "is_sample": True,
        "created_at": now_iso
    }
    db.insert("courses", course_record)

    # Insert units
    unit_id_map = {}
    for u in fixture.get("course_units", []):
        u_id = f"cu_sample_{uuid.uuid4().hex[:8]}"
        u_record = {
            "id": u_id,
            "course_id": course_id,
            "title": u.get("title", "Unit (Sample data)"),
            "order": u.get("order", 1),
            "description": u.get("description", ""),
            "created_at": now_iso
        }
        db.insert("course_units", u_record)
        unit_id_map[u.get("order", 1)] = u_id

    # Insert topics
    topic_id_map = {}
    for t in fixture.get("topics", []):
        t_id = f"top_sample_{uuid.uuid4().hex[:8]}"
        t_record = {
            "id": t_id,
            "course_id": course_id,
            "name": t.get("name", "Topic (Sample data)"),
            "order": t.get("order", 1),
            "description": t.get("description", ""),
            "created_at": now_iso
        }
        db.insert("topics", t_record)
        topic_id_map[t.get("order", 1)] = t_id

    # Insert concepts
    concept_id_map = {}
    first_topic_id = list(topic_id_map.values())[0] if topic_id_map else None
    for idx, c in enumerate(fixture.get("concepts", [])):
        c_id = f"con_sample_{uuid.uuid4().hex[:8]}"
        c_record = {
            "id": c_id,
            "course_id": course_id,
            "topic_id": first_topic_id,
            "name": c.get("name", "Concept (Sample data)"),
            "description": c.get("description", ""),
            "prerequisites": [],
            "created_at": now_iso
        }
        db.insert("concepts", c_record)
        concept_id_map[idx] = c_id

    # Insert questions
    first_concept_id = list(concept_id_map.values())[0] if concept_id_map else None
    for q in fixture.get("questions", []):
        q_id = f"q_sample_{uuid.uuid4().hex[:8]}"
        q_record = {
            "id": q_id,
            "course_id": course_id,
            "topic_id": first_topic_id,
            "concept_id": first_concept_id,
            "type": q.get("type", "mcq"),
            "stem": q.get("stem", ""),
            "options": q.get("options", []),
            "answer": q.get("answer", ""),
            "explanation": q.get("explanation", ""),
            "difficulty": q.get("difficulty", "Medium"),
            "verification_status": "verified",
            "is_sample": True,
            "created_at": now_iso
        }
        db.insert("questions", q_record)

    return course_record
