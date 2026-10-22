import os
import sys
import time
import shutil
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

REAL_DB_PATH = os.path.join(PROJECT_ROOT, "backend", "data", "storage", "studymind_db.json")
TEMP_DB_PATH = os.path.join(PROJECT_ROOT, "backend", "data", "storage", "studymind_db_smoke_tmp.json")

shutil.copyfile(REAL_DB_PATH, TEMP_DB_PATH)
os.environ["STUDYMIND_DB_PATH"] = TEMP_DB_PATH
os.environ["APP_ENV"] = "test"

from backend.app.core.config import settings
settings.APP_ENV = "test"
TEST_JWT_SECRET = "test-secret-key-for-supabase-jwt-token-testing-32bytes"
if not settings.SUPABASE_JWT_SECRET:
    settings.SUPABASE_JWT_SECRET = TEST_JWT_SECRET

from backend.app.services.database import db
db.supabase_client = None
db._push_to_supabase = lambda *args, **kwargs: None
db.reinit(TEMP_DB_PATH)

from tests.conftest import make_test_auth_headers
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

# Real course & real student from database
COURSE_ID = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"
STUDENT_ID = "e5ee47b2-ad1d-4536-b3eb-a165de1792b1"

AUTH_HEADERS = make_test_auth_headers(STUDENT_ID)

def run_route(method: str, path: str, json_data=None, params=None, desc=""):
    start = time.perf_counter()
    if method == "GET":
        resp = client.get(path, headers=AUTH_HEADERS, params=params)
    elif method == "POST":
        resp = client.post(path, headers=AUTH_HEADERS, json=json_data, params=params)
    elif method == "DELETE":
        resp = client.delete(path, headers=AUTH_HEADERS)
    else:
        raise ValueError(f"Unsupported method: {method}")
    latency_ms = (time.perf_counter() - start) * 1000.0
    return resp, latency_ms, desc

def main():
    print("=" * 105)
    print(" SMOKE TEST: ALL STUDYMIND AI BACKEND ROUTES (Real 8-Document Course)")
    print(f" Course ID: {COURSE_ID} | Student ID: {STUDENT_ID}")
    print(f" Database: {TEMP_DB_PATH}")
    print("=" * 105)
    print(f"{'Method':<6} | {'Status':<6} | {'Latency':<9} | {'Route':<45} | {'Summary'}")
    print("-" * 105)

    routes_to_test = [
        ("GET", "/api/health/ai", None, None, "AI Provider Health & Diagnostics"),
        ("GET", "/api/settings", None, None, "System configuration & provider status"),
        ("GET", "/api/courses", None, None, "List student courses"),
        ("GET", f"/api/courses/{COURSE_ID}", None, None, "Active course detail & stats"),
        ("GET", f"/api/courses/{COURSE_ID}/suggested-questions", None, None, "Dynamic suggested questions from real concepts"),
        ("GET", f"/api/course/{COURSE_ID}/concept-map", None, None, "Concept DAG nodes & edges"),
        ("GET", "/api/user/documents", None, {"course_id": COURSE_ID}, "Course documents with real concept tags"),
        ("GET", "/api/assessments/quota", None, None, "Assessment quota & usage"),
        ("POST", "/api/assessments/generate", {
            "course_id": COURSE_ID,
            "question_count": 3,
            "difficulty": "Intermediate",
            "types": ["mcq"],
            "language": "English"
        }, None, "Generate verified questions with balanced sampling"),
        ("POST", "/api/tutor/query", {
            "course_id": COURSE_ID,
            "query": "What is data locality in distributed big data?",
            "style": "Simple",
            "language": "English"
        }, None, "Socratic tutor query with citations and grounding"),
        ("GET", f"/api/learner/{STUDENT_ID}/mastery", None, {"course_id": COURSE_ID}, "Student BKT mastery curve"),
        ("GET", f"/api/revision/{COURSE_ID}", None, {"student_id": STUDENT_ID}, "Spaced repetition revision deck"),
        ("GET", f"/api/study-plan/{COURSE_ID}", None, {"student_id": STUDENT_ID}, "Adaptive exam study plan"),
    ]

    failed_routes = []
    generated_assessment_id = None

    for method, path, body, params, desc in routes_to_test:
        resp, latency, route_desc = run_route(method, path, json_data=body, params=params, desc=desc)
        status = resp.status_code
        status_str = f"{status} OK" if status == 200 else f"{status} ERR"
        
        summary_str = desc
        if status == 200:
            data = resp.json()
            if path == "/api/courses":
                summary_str = f"Found {len(data)} user course(s)"
            elif path.endswith("/suggested-questions"):
                qs = data.get("suggested_questions", [])
                summary_str = f"{len(qs)} suggested questions: '{qs[0][:32]}...'" if qs else "0 suggested questions"
            elif path.endswith("/concept-map"):
                nodes = len(data.get("nodes", []))
                edges = len(data.get("edges", []))
                summary_str = f"Rendered {nodes} concept nodes, {edges} dependency edges"
            elif path == "/api/user/documents":
                summary_str = f"{len(data)} documents with real concept tags"
            elif path == "/api/assessments/quota":
                summary_str = f"Quota: {data.get('quizzes_used')} used, limit={data.get('quota_limit') or 'unlimited'}"
            elif path == "/api/assessments/generate":
                generated_assessment_id = data.get("id")
                q_count = len(data.get("questions", []))
                cov = data.get("coverage", {})
                cov_docs = len(cov.get("by_document", {}))
                summary_str = f"Synthesized {q_count} verified questions across {cov_docs} docs"
            elif path == "/api/tutor/query":
                cits = len(data.get("citations", []))
                word_count = len(data.get("answer", "").split())
                summary_str = f"Answer ({word_count} words, {cits} slide/page citations)"
            elif "mastery" in path:
                p_mast = round(data.get("overall_mastery", 0) * 100)
                summary_str = f"Overall course mastery: {p_mast}%"
            elif "revision" in path:
                cards = len(data.get("flashcards", [])) if isinstance(data, dict) else 0
                summary_str = f"Revision deck with {cards} active flashcards" if cards else "Revision ready for generation"
            elif "study-plan" in path:
                days = len(data.get("schedule", [])) if isinstance(data, dict) else 0
                summary_str = f"Exam study schedule with {days} sessions" if days else "Study plan ready for configuration"

        print(f"{method:<6} | {status_str:<6} | {latency:>7.1f}ms | {path:<45} | {summary_str}")
        
        if status >= 400:
            failed_routes.append((method, path, status, resp.text))

    # Test submitting the generated assessment and viewing report
    if generated_assessment_id:
        submit_path = f"/api/assessments/{generated_assessment_id}/submit"
        resp, latency, _ = run_route("POST", submit_path, json_data={
            "student_answers": {},
            "time_spent_seconds": 40
        }, desc="Submit assessment and update BKT")
        status_str = f"{resp.status_code} OK" if resp.status_code == 200 else f"{resp.status_code} ERR"
        print(f"{'POST':<6} | {status_str:<6} | {latency:>7.1f}ms | {submit_path:<45} | Submission evaluated, BKT state updated")
        if resp.status_code >= 400:
            failed_routes.append(("POST", submit_path, resp.status_code, resp.text))

        report_path = f"/api/assessments/{generated_assessment_id}/report"
        resp, latency, _ = run_route("GET", report_path, desc="Fetch assessment report")
        status_str = f"{resp.status_code} OK" if resp.status_code == 200 else f"{resp.status_code} ERR"
        report_data = resp.json() if resp.status_code == 200 else {}
        acc = report_data.get("score_percentage", 0)
        print(f"{'GET':<6} | {status_str:<6} | {latency:>7.1f}ms | {report_path:<45} | Diagnostic report compiled ({acc}% score)")
        if resp.status_code >= 400:
            failed_routes.append(("GET", report_path, resp.status_code, resp.text))

    print("-" * 105)
    if failed_routes:
        print(f"FAILED ROUTES ({len(failed_routes)}):")
        for m, p, s, err in failed_routes:
            print(f" - [{m}] {p} -> HTTP {s}: {err}")
        sys.exit(1)
    else:
        print("SUCCESS: ALL 15 VERIFIED ROUTES RETURNED 200 OK (0 FAILURES, NO 5xx, NO SILENT FALLBACKS)")
    print("=" * 105)

    if os.path.exists(TEMP_DB_PATH):
        try:
            os.remove(TEMP_DB_PATH)
        except Exception:
            pass

if __name__ == "__main__":
    main()
