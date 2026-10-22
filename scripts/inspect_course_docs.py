import json

with open("backend/data/storage/studymind_db.json", "r", encoding="utf-8") as f:
    data = json.load(f)

courses = data.get("courses", {})
documents = data.get("documents", {})

for cid, c in courses.items():
    docs = [d["filename"] for d in documents.values() if d.get("course_id") == cid]
    print(f"Course [{cid[:8]}] '{c.get('name')}' (owner: {c.get('owner_id')}) -> {len(docs)} doc(s): {docs[:2]}")
