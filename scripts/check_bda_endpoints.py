import urllib.request
import json

def check(url, headers={}):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return resp.status, data
    except urllib.error.HTTPError as he:
        return he.code, he.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return 500, str(e)

token = 'demo_token'
headers = {'Authorization': f'Bearer {token}'}

print('=== Backend Verification ===')
s, d = check('http://localhost:8000/api/courses', headers)
print(f"GET /courses: status {s}")
canonical = [c for c in d if c['name'] == 'Bda'][0]
bda_id = canonical['id']
print(f"Canonical Bda ID: {bda_id}")
print(f"  Concept count: {canonical.get('concept_count')}")
print(f"  Document count: {canonical.get('document_count')}")

student_id = "3d760296-758f-4fb1-a4a7-6303e2983677"

endpoints = [
    f'http://localhost:8000/api/courses/{bda_id}',
    f'http://localhost:8000/api/user/documents?course_id={bda_id}',
    f'http://localhost:8000/api/course/{bda_id}/concept-map',
    f'http://localhost:8000/api/learner/{student_id}/mastery?course_id={bda_id}',
    f'http://localhost:8000/api/revision/{bda_id}',
    f'http://localhost:8000/api/study-plan/{bda_id}',
    f'http://localhost:8000/api/courses/{bda_id}/suggested-questions',
    f'http://localhost:8000/api/assessments?course_id={bda_id}',
    'http://localhost:8000/api/evaluation/results',
]

for ep in endpoints:
    st, res = check(ep, headers)
    ep_name = ep.split('/api/')[-1]
    if isinstance(res, list):
        info = f"list of {len(res)} items"
    elif isinstance(res, dict):
        info = f"dict with keys {list(res.keys())[:5]}"
    else:
        info = str(res)[:60]
    print(f"GET {ep_name} -> {st} ({info})", flush=True)
