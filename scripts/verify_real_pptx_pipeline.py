import os
import sys
import tempfile
import uuid
import shutil

# Root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Enforce temp DB for test isolation
temp_dir = tempfile.mkdtemp(prefix="pptx_verify_")
temp_db_path = os.path.join(temp_dir, "studymind_temp_db.json")
os.environ["STUDYMIND_DB_PATH"] = temp_db_path
os.environ["APP_ENV"] = "test"

from backend.app.core.config import settings
settings.STUDYMIND_DB_PATH = temp_db_path
settings.APP_ENV = "test"

from backend.app.services.database import db
db.reinit(temp_db_path)

print(f"[PPTX Verify] Using isolated temp DB at: {temp_db_path}")

def run_verification():
    from backend.app.ingestion.pipeline import IngestionPipeline
    pipeline = IngestionPipeline()
    print("[PPTX Verify] Pipeline initialized successfully with isolated DB.")

if __name__ == "__main__":
    try:
        run_verification()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
