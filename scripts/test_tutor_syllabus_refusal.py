import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')

from backend.app.rag.engine import rag_engine

def main():
    course_id = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"
    query = "What is the Course Articulation Matrix correlation level for PO11 and PO12?"


    
    print("Testing Tutor response on a missing syllabus topic:")
    print("Query:", query)
    res = rag_engine.query_tutor(
        course_id=course_id,
        query=query,
        allow_outside_knowledge=False
    )

    print("\nTutor Refused:", res.get("refused"))
    print("\nTutor Answer:\n" + res.get("answer"))

if __name__ == "__main__":
    main()
