import os
import sys
import time
import jwt
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "live: mark test as live test requiring real provider API keys")

# Ensure APP_ENV=test is set before any backend modules are loaded
os.environ["APP_ENV"] = "test"

# Ensure root directory is on sys.path for test discovery
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.core.config import settings
settings.APP_ENV = "test"

TEST_JWT_SECRET = "test-secret-key-for-supabase-jwt-token-testing-32bytes"
if not settings.SUPABASE_JWT_SECRET:
    settings.SUPABASE_JWT_SECRET = TEST_JWT_SECRET

from backend.app.main import app

@pytest.fixture(scope="session", autouse=True)
def guard_real_db_immutability():
    real_db_path = os.path.join(settings.STORAGE_DIR, "studymind_db.json")
    initial_stat = None
    if os.path.exists(real_db_path):
        s = os.stat(real_db_path)
        initial_stat = (s.st_size, s.st_mtime)

    yield

    if initial_stat and os.path.exists(real_db_path):
        s_after = os.stat(real_db_path)
        assert s_after.st_size == initial_stat[0], (
            f"REAL DB SIZE CHANGED during tests! Before: {initial_stat[0]}, After: {s_after.st_size}"
        )
        assert s_after.st_mtime == initial_stat[1], (
            f"REAL DB MTIME CHANGED during tests! Before: {initial_stat[1]}, After: {s_after.st_mtime}"
        )


_EMBED_CACHE = {}

def _get_embedding(text: str):
    if text not in _EMBED_CACHE:
        try:
            from backend.app.rag.engine import rag_engine
            _EMBED_CACHE[text] = rag_engine.embedding_provider.embed_text(text)
        except Exception:
            _EMBED_CACHE[text] = [0.05] * 384
    return _EMBED_CACHE[text]


def _seed_test_baseline(database):
    """Populate test DB with standard baseline objects for test suites."""
    from eval.fixtures.sample_loader import DEMO_COURSE_ID
    database.insert("courses", {
        "id": DEMO_COURSE_ID,
        "owner_id": "default_student",
        "name": "Data Structures & Algorithms: Theory & Applications",
        "description": "Comprehensive course covering divide-and-conquer, dynamic programming, and greedy algorithms.",
        "subject": "Computer Science",
        "is_sample": True,
        "color": "indigo"
    })
    for i in range(1, 4):
        database.insert("course_units", {
            "id": f"unit_demo_{i}",
            "course_id": DEMO_COURSE_ID,
            "unit_number": i,
            "title": f"Unit {i}: Core Algorithms",
            "description": f"Module {i}"
        })
        database.insert("documents", {
            "id": f"doc_demo_{i}",
            "course_id": DEMO_COURSE_ID,
            "filename": f"demo_material_{i}.pdf",
            "file_type": "pdf",
            "status": "processed"
        })
    database.insert("units", {
        "id": "unit_demo_1",
        "course_id": DEMO_COURSE_ID,
        "name": "Dynamic Programming",
        "order": 1
    })
    database.insert("topics", {
        "id": "topic_demo_1",
        "course_id": DEMO_COURSE_ID,
        "unit_id": "unit_demo_1",
        "name": "Dynamic Programming Foundations",
        "description": "Memoization, tabulation, and recurrence relations"
    })
    database.insert("topics", {
        "id": "topic_demo_2",
        "course_id": DEMO_COURSE_ID,
        "unit_id": "unit_demo_1",
        "name": "Divide and Conquer",
        "description": "Subproblem division and recursive combination"
    })
    database.insert("topics", {
        "id": "topic_demo_3",
        "course_id": DEMO_COURSE_ID,
        "unit_id": "unit_demo_1",
        "name": "Greedy Algorithms",
        "description": "Locally optimal choices"
    })
    database.insert("concepts", {
        "id": "con_dp_1",
        "course_id": DEMO_COURSE_ID,
        "topic_id": "topic_demo_1",
        "name": "Dynamic Programming Principles",
        "description": "Core concepts of memoization and overlapping subproblems"
    })
    database.insert("concepts", {
        "id": "concept_demo_1",
        "course_id": DEMO_COURSE_ID,
        "topic_id": "topic_demo_1",
        "name": "Optimal Substructure",
        "description": "Subproblem optimality"
    })
    database.insert("concepts", {
        "id": "concept_demo_2",
        "course_id": DEMO_COURSE_ID,
        "topic_id": "topic_demo_1",
        "name": "Overlapping Subproblems",
        "description": "Memoization caching"
    })
    database.insert("concepts", {
        "id": "concept_demo_3",
        "course_id": DEMO_COURSE_ID,
        "topic_id": "topic_demo_2",
        "name": "Divide and Conquer",
        "description": "Partitioning problems"
    })

    database.insert("concept_prerequisites", {
        "id": "prereq_demo_1",
        "course_id": DEMO_COURSE_ID,
        "concept_id": "concept_demo_2",
        "prerequisite_id": "concept_demo_1",
        "strength": 0.95
    })

    chunk_texts = [
        ("chunk_demo_1", "chapter_algorithms.pdf", 14, "pdf", None, "In dynamic programming, optimal substructure means an optimal solution contains optimal solutions to subproblems. Overlapping subproblems allows caching intermediate evaluations.", ["concept_demo_1", "concept_demo_2"]),
        ("chunk_demo_2", "chapter_algorithms.pdf", 15, "pdf", None, "Memoization is a top-down recursive caching technique used in dynamic programming algorithms to avoid redundant recomputations of overlapping subproblems.", ["concept_demo_2"]),
        ("chunk_demo_3", "lecture_dynamic_programming.pptx", None, "pptx", 3, "Divide and conquer algorithms partition problems into independent subproblems, solve each recursively, and recombine their solutions.", ["concept_demo_3"]),
        ("chunk_demo_4", "lecture_dynamic_programming.pptx", None, "pptx", 4, "Dynamic programming applies whenever problem states satisfy both principle of optimality and directed acyclic state dependency graphs.", ["concept_demo_1"]),
    ]

    for cid, doc_name, page_no, stype, slide_no, content, cids in chunk_texts:
        database.insert("knowledge_chunks", {
            "id": cid,
            "course_id": DEMO_COURSE_ID,
            "document_name": doc_name,
            "page_number": page_no,
            "slide_number": slide_no,
            "source_type": stype,
            "content": content,
            "concept_ids": cids,
            "embedding": _get_embedding(content)
        })


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch):
    os.environ["APP_ENV"] = "test"
    settings.APP_ENV = "test"
    if not settings.SUPABASE_JWT_SECRET:
        settings.SUPABASE_JWT_SECRET = TEST_JWT_SECRET

    test_db_path = str(tmp_path / "studymind_db.json")
    monkeypatch.setenv("STUDYMIND_DB_PATH", test_db_path)
    settings.STUDYMIND_DB_PATH = test_db_path

    from backend.app.services.database import db
    db.reinit(test_db_path)

    # Seed baseline demo course for tests instantly
    _seed_test_baseline(db)

    yield


def make_test_jwt(student_id: str, expired: bool = False) -> str:
    secret = settings.SUPABASE_JWT_SECRET or TEST_JWT_SECRET
    exp_time = int(time.time()) - 3600 if expired else int(time.time()) + 86400
    payload = {
        "sub": student_id,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": exp_time,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def make_test_auth_headers(student_id: str) -> dict:
    token = make_test_jwt(student_id)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers():
    return lambda student_id: make_test_auth_headers(student_id)
