import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.database import db
from tests.conftest import make_test_auth_headers

client = TestClient(app)

def test_user_a_cannot_read_user_b_resources():
    """
    Real Auth & Isolation test:
    User A cannot read User B's courses, mastery, files, or conversations.
    Expect 404/403.
    """
    user_a = "user_isolation_a_12345"
    user_b = "user_isolation_b_67890"

    headers_a = make_test_auth_headers(user_a)
    headers_b = make_test_auth_headers(user_b)

    # 1. Setup User B's Course, Conversation, Document, and Mastery in DB
    course_b_id = f"crs_isolated_{user_b}"
    db.insert("courses", {
        "id": course_b_id,
        "name": "User B Private Research Course",
        "description": "Private syllabus owned by User B",
        "owner_id": user_b,
        "is_public": False
    })

    conv_b_id = f"conv_isolated_{user_b}"
    db.insert("conversations", {
        "id": conv_b_id,
        "course_id": course_b_id,
        "student_id": user_b,
        "title": "Private Discussion on Genetics"
    })

    doc_b_id = f"doc_isolated_{user_b}"
    db.insert("documents", {
        "id": doc_b_id,
        "course_id": course_b_id,
        "filename": "private_thesis_notes.pdf",
        "file_type": "pdf",
        "owner_id": user_b,
        "file_path": "backend/data/storage/private_thesis_notes.pdf"
    })

    db.insert("learner_mastery", {
        "id": f"mst_isolated_{user_b}",
        "student_id": user_b,
        "course_id": course_b_id,
        "concept_id": "concept_private_b",
        "mastery_probability": 0.85
    })

    # Test 1: User A tries to read User B's mastery
    resp_mastery = client.get(f"/api/learner/{user_b}/mastery", headers=headers_a)
    assert resp_mastery.status_code in (403, 404), f"Expected 403/404, got {resp_mastery.status_code}"

    # Test 2: User A tries to read User B's recommendations
    resp_recom = client.get(f"/api/learner/{user_b}/recommendations", headers=headers_a)
    assert resp_recom.status_code in (403, 404), f"Expected 403/404, got {resp_recom.status_code}"

    # Test 3: User A tries to read User B's course
    resp_course = client.get(f"/api/courses/{course_b_id}", headers=headers_a)
    assert resp_course.status_code in (403, 404), f"Expected 403/404, got {resp_course.status_code}"

    # Test 4: User A tries to read User B's conversation messages
    resp_conv = client.get(f"/api/conversations/{conv_b_id}/messages", headers=headers_a)
    assert resp_conv.status_code in (403, 404), f"Expected 403/404, got {resp_conv.status_code}"

    # Test 5: User A tries to delete User B's conversation
    resp_del_conv = client.delete(f"/api/conversations/{conv_b_id}", headers=headers_a)
    assert resp_del_conv.status_code in (403, 404), f"Expected 403/404, got {resp_del_conv.status_code}"

    # Test 6: User A tries to download User B's file
    resp_file = client.get(f"/api/user/documents/{doc_b_id}/download", headers=headers_a)
    assert resp_file.status_code in (403, 404), f"Expected 403/404, got {resp_file.status_code}"

    # Test 7: User A tries to delete User B's document
    resp_del_file = client.delete(f"/api/user/documents/{doc_b_id}", headers=headers_a)
    assert resp_del_file.status_code in (403, 404), f"Expected 403/404, got {resp_del_file.status_code}"

    # Test 8: Unauthenticated request (no JWT token) gets 401 Unauthorized
    resp_unauth = client.get(f"/api/conversations", headers={})
    assert resp_unauth.status_code == 401, f"Expected 401, got {resp_unauth.status_code}"

    # Test 9: Expired token gets 401 Unauthorized
    from tests.conftest import make_test_jwt
    expired_token = make_test_jwt(user_a, expired=True)
    resp_expired = client.get("/api/conversations", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp_expired.status_code == 401, f"Expected 401 for expired token, got {resp_expired.status_code}"
