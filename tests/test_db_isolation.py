import os
import uuid
import pytest
from backend.app.core.config import settings
from backend.app.services.database import db

def test_database_isolation_from_real_file():
    """
    Test Requirement:
    Settings.DB_PATH must be redirected to a temporary test database during pytest.
    Any insertions, updates, or deletes must never touch the real database file.
    """
    real_db_path = os.path.join(settings.STORAGE_DIR, "studymind_db.json")
    
    # Verify current db_path is NOT the real DB
    assert db.db_path != real_db_path, f"Database path should be isolated, but got {db.db_path}"
    assert "pytest" in db.db_path or "tmp" in db.db_path.lower() or "temp" in db.db_path.lower()
    
    # Record real DB stat if it exists
    real_stat_before = None
    if os.path.exists(real_db_path):
        s = os.stat(real_db_path)
        real_stat_before = (s.st_size, s.st_mtime)

    # Perform mutations on the test DB
    dummy_id = f"test_iso_{uuid.uuid4().hex[:8]}"
    db.insert("courses", {
        "id": dummy_id,
        "name": "Isolation Verification Course",
        "description": "Must not be written to real disk",
        "owner_id": "test_isolated_user"
    })
    
    # Verify dummy record is in test DB
    assert db.get_by_id("courses", dummy_id) is not None
    
    # Verify real DB file was NOT changed
    if real_stat_before and os.path.exists(real_db_path):
        real_stat_after = os.stat(real_db_path)
        assert real_stat_after.st_size == real_stat_before[0], "Real DB file size changed during test!"
        assert real_stat_after.st_mtime == real_stat_before[1], "Real DB file mtime changed during test!"
