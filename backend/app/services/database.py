import os
import json
import uuid
import threading
import concurrent.futures
from typing import Dict, List, Any, Optional
from datetime import datetime
from backend.app.core.config import settings

class DatabaseManager:
    """
    Unified Database Manager.
    - Seamlessly connects to Supabase if SUPABASE_URL and SUPABASE_KEY are provided.
    - Synchronizes an active state store structured 1:1 with the Supabase PostgreSQL schema.
    - Automatically persists data to local JSON disk atomically so state persists across restarts without corruption.
    - Thread-safe using RLock for all operations.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self.supabase_client = None
        self._custom_db_path = None
        self.data: Dict[str, Dict[str, Any]] = {
            "courses": {},
            "course_units": {},
            "documents": {},
            "topics": {},
            "concepts": {},
            "concept_prerequisites": {},
            "visual_elements": {},
            "knowledge_chunks": {},
            "conversations": {},
            "messages": {},
            "questions": {},
            "question_history": {},
            "assessments": {},
            "assessment_questions": {},
            "attempts": {},
            "learner_mastery": {},
            "misconceptions": {},
            "study_plans": {},
            "revision_materials": {},
            "evaluation_results": {}
        }
        self.init_db()
        import atexit
        atexit.register(self.flush)

    @property
    def db_path(self) -> str:
        if getattr(self, "_custom_db_path", None):
            return self._custom_db_path
        return settings.DB_PATH

    @db_path.setter
    def db_path(self, val: str):
        self._custom_db_path = val

    def reinit(self, db_path: Optional[str] = None):
        """Reset internal in-memory tables and reload from specified db_path or settings.DB_PATH."""
        with self._lock:
            self._custom_db_path = db_path
            self.data = {
                "courses": {},
                "course_units": {},
                "documents": {},
                "topics": {},
                "concepts": {},
                "concept_prerequisites": {},
                "visual_elements": {},
                "knowledge_chunks": {},
                "conversations": {},
                "messages": {},
                "questions": {},
                "question_history": {},
                "assessments": {},
                "assessment_questions": {},
                "attempts": {},
                "learner_mastery": {},
                "misconceptions": {},
                "study_plans": {},
                "revision_materials": {},
                "evaluation_results": {}
            }
            self.init_db()

    def init_db(self):
        from backend.app.core.config import is_test_environment
        # 1. Check if Supabase client can be initialized (skip during tests to avoid remote pollution)
        if not is_test_environment() and settings.SUPABASE_URL and settings.SUPABASE_KEY and "supabase.co" in settings.SUPABASE_URL:
            try:
                from supabase import create_client
                self.supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                print(f"[DatabaseManager] Connected to Supabase at {settings.SUPABASE_URL}")
            except Exception as e:
                print(f"[DatabaseManager] Failed to connect to Supabase: {e}. Falling back to internal store.")
        elif is_test_environment():
            self.supabase_client = None

        # 2. Load cached persistent state if exists
        target_path = self.db_path
        if target_path and os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    for table, records in saved.items():
                        if table in self.data:
                            self.data[table].update(records)
                print(f"[DatabaseManager] Loaded database state from {target_path}")
            except Exception as e:
                print(f"[DatabaseManager] Could not load db cache: {e}")

    _last_save_time: float = 0.0
    _dirty: bool = False
    total_save_state_time: float = 0.0
    save_state_count: int = 0

    def save_state(self, force: bool = False):
        """
        Persist current database state atomically to disk.
        Debounced: skips write if called within DB_DEBOUNCE_SECONDS unless force=True.
        """
        import time
        now = time.time()
        with self._lock:
            target_path = self.db_path
            if not target_path:
                return

            debounce_window = getattr(settings, "DB_DEBOUNCE_SECONDS", 2.0)
            if not force and (now - self._last_save_time < debounce_window):
                # Debounced: defer disk persistence
                return

            t0 = time.perf_counter()
            parent_dir = os.path.dirname(os.path.abspath(target_path))
            os.makedirs(parent_dir, exist_ok=True)
            temp_path = f"{target_path}.tmp_{os.getpid()}_{uuid.uuid4().hex[:6]}"
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, default=str)
                os.replace(temp_path, target_path)
                self._last_save_time = now
                self._dirty = False
                dur = time.perf_counter() - t0
                self.total_save_state_time += dur
                self.save_state_count += 1
            except Exception as e:
                print(f"[DatabaseManager] Error saving state: {e}")
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

    def flush(self):
        """Forces immediate atomic disk persistence of all dirty changes."""
        self.save_state(force=True)

    def is_supabase_active(self) -> bool:
        return self.supabase_client is not None

    @staticmethod
    def _clean_for_supabase(table: str, item: Dict[str, Any]) -> Dict[str, Any]:
        json_columns = {
            "questions": {"options"}, "study_plans": {"schedule"},
            "revision_materials": {"key_formulas", "flashcards", "common_mistakes"},
            "messages": {"citations"}, "assessment_submissions": {"report"},
            "assessments": {"last_report"}, "evaluation_results": {"details"},
        }.get(table, set())
        excluded = {"visual_element", "embedding", "verification_details"}
        return {key: value for key, value in item.items()
                if key not in excluded and (not isinstance(value, (dict, list)) or key in json_columns)}

    # Background worker for non-blocking Supabase sync
    _sync_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="supabase_sync")

    def _sync_to_supabase(self, table: str, items: List[Dict[str, Any]]):
        if not self.supabase_client or not items:
            return
        def _worker():
            try:
                filtered = [
                    self._clean_for_supabase(table, it) for it in items
                    if not str(it.get("id", "")).startswith("sim_")
                    and not str(it.get("student_id", "")).startswith("sim_")
                    and not str(it.get("course_id", "")).startswith("demo-")
                    and not str(it.get("id", "")).startswith("demo-")
                ]
                if not filtered:
                    return
                chunk_size = 50
                for i in range(0, len(filtered), chunk_size):
                    batch = filtered[i:i + chunk_size]
                    self.supabase_client.table(table).insert(batch).execute()
            except Exception as e:
                print(f"[DatabaseManager] Background Supabase sync notice for {table}: {e}")

        self._sync_executor.submit(_worker)

    # Generic CRUD operations
    def insert(self, table: str, item: Dict[str, Any], save_disk: bool = True) -> Dict[str, Any]:
        with self._lock:
            if "id" not in item or not item["id"]:
                item["id"] = str(uuid.uuid4())
            if "created_at" not in item:
                item["created_at"] = datetime.utcnow().isoformat()
                
            self.data.setdefault(table, {})[item["id"]] = item
            self._not_found_cache.discard((table, item["id"]))
            self._dirty = True
            is_sim = str(item.get("id", "")).startswith("sim_") or str(item.get("student_id", "")).startswith("sim_")
            if save_disk and not is_sim:
                self.save_state(force=False)

            if self.supabase_client and not is_sim:
                self._sync_to_supabase(table, [item])

            return item

    def insert_batch(self, table: str, items: List[Dict[str, Any]], save_disk: bool = True) -> List[Dict[str, Any]]:
        if not items:
            return items
        now = datetime.utcnow().isoformat()
        has_non_sim = False
        with self._lock:
            for it in items:
                if "id" not in it or not it["id"]:
                    it["id"] = str(uuid.uuid4())
                if "created_at" not in it:
                    it["created_at"] = now
                self.data.setdefault(table, {})[it["id"]] = it
                if not str(it.get("id", "")).startswith("sim_") and not str(it.get("student_id", "")).startswith("sim_"):
                    has_non_sim = True

            self._dirty = True
            if save_disk and has_non_sim:
                self.save_state(force=False)

        if self.supabase_client and has_non_sim:
            self._sync_to_supabase(table, items)

        return items

    _not_found_cache: set = set()

    def get_by_id(self, table: str, item_id: str) -> Optional[Dict[str, Any]]:
        if not item_id or not isinstance(item_id, str):
            return None
        with self._lock:
            if table in self.data and item_id in self.data[table]:
                return self.data[table][item_id]
        # Fast exit if known not-found or invalid id (e.g. contains spaces/newlines)
        cache_key = (table, item_id)
        if cache_key in self._not_found_cache or " " in item_id or "\n" in item_id:
            return None

        if self.supabase_client and not str(item_id).startswith("demo-"):
            try:
                response = self.supabase_client.table(table).select("*").eq("id", item_id).limit(1).execute()
                rows = response.data or []
                if rows:
                    with self._lock:
                        self.data.setdefault(table, {})[item_id] = rows[0]
                    return rows[0]
                else:
                    self._not_found_cache.add(cache_key)
            except Exception:
                self._not_found_cache.add(cache_key)
        else:
            self._not_found_cache.add(cache_key)
        with self._lock:
            return self.data.get(table, {}).get(item_id)

    def get(self, table: str, filter_fn) -> Optional[Dict[str, Any]]:
        results = self.list_all(table, filter_fn)
        return results[0] if results else None

    def list_all(self, table: str, filter_fn=None) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self.data.get(table, {}).values())
        if filter_fn:
            items = [item for item in items if filter_fn(item)]
        return items

    def update(self, table: str, item_id: str, updates: Dict[str, Any], save_disk: bool = True) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self.supabase_client and item_id not in self.data.get(table, {}) and not str(item_id).startswith("demo-"):
                self.get_by_id(table, item_id)
            if table in self.data and item_id in self.data[table]:
                self.data[table][item_id].update(updates)
                is_sim = str(item_id).startswith("m_sim_") or str(updates.get("student_id", "")).startswith("sim_")
                if save_disk and not is_sim:
                    self.save_state()
                if self.supabase_client and not is_sim and not str(item_id).startswith("demo-") and not str(updates.get("course_id", "")).startswith("demo-"):
                    try:
                        clean_updates = self._clean_for_supabase(table, {k: v for k, v in updates.items() if k != "concept_name"})
                        self.supabase_client.table(table).update(clean_updates).eq("id", item_id).execute()
                    except Exception as e:
                        print(f"[DatabaseManager] Warning: Supabase update skipped for {table}: {e}")
                return self.data[table][item_id]
            return None

    def delete(self, table: str, item_id: str, save_disk: bool = True) -> bool:
        with self._lock:
            if table in self.data and item_id in self.data[table]:
                del self.data[table][item_id]
                if save_disk:
                    self.save_state()
                if self.supabase_client:
                    try:
                        self.supabase_client.table(table).delete().eq("id", item_id).execute()
                    except Exception as e:
                        print(f"[Supabase Delete Error] Table {table}: {e}")
                return True
            return False

# Global database singleton
db = DatabaseManager()
