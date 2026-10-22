import os
import zipfile
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_ZIP = os.path.join(ROOT_DIR, "studymind_project_share.zip")

EXCLUDED_DIRS = {
    "node_modules",
    "__pycache__",
    "storage",
    "dist",
    ".pytest_cache",
    ".git"
}

EXCLUDED_FILES = {
    ".env",
    ".env.local",
    "studymind_project_share.zip"
}

def is_excluded(rel_path: str, is_dir: bool = False) -> bool:
    parts = rel_path.replace("\\", "/").split("/")
    
    # Check directory exclusion
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True
        if part.startswith(".tmp_") or part.endswith(".tmp"):
            return True

    # Check path pattern backend/data/storage
    norm = rel_path.replace("\\", "/").lower()
    if "backend/data/storage" in norm:
        return True

    filename = parts[-1]
    if filename in EXCLUDED_FILES:
        return True

    # Check pattern matching
    if filename.endswith(".bak") or ".bak" in filename:
        return True
    if ".tmp_" in filename or filename.startswith(".tmp_"):
        return True
    if filename.endswith(".pyc"):
        return True

    return False

def make_zip():
    print(f"[ZIP] Creating project zip at: {OUTPUT_ZIP}")
    file_count = 0
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(ROOT_DIR):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if not is_excluded(os.path.relpath(os.path.join(root, d), ROOT_DIR), is_dir=True)]
            
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, ROOT_DIR)
                
                if is_excluded(rel_path):
                    continue
                
                zipf.write(full_path, rel_path)
                file_count += 1

    size_mb = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)
    print(f"[ZIP] Complete! Archived {file_count} files into {OUTPUT_ZIP} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    make_zip()
