import os
import sys
import json
import numpy as np

# Ensure root path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.core.config import settings
from backend.app.services.database import db
from backend.app.rag.engine import rag_engine

TARGET_COURSE_ID = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"

def calibrate_refusal():
    print("[Calibration] Initializing fused refusal threshold calibration on real course data...")

    # 1. Fetch chunks for target course
    chunks = db.list_all("knowledge_chunks", lambda c: c.get("course_id") == TARGET_COURSE_ID)
    if not chunks:
        # Fallback to any available chunks
        chunks = db.list_all("knowledge_chunks")
        if not chunks:
            print("[Calibration] ERROR: No chunks found in database.")
            return settings.RETRIEVAL_REFUSAL_THRESHOLD
        course_id = chunks[0].get("course_id")
    else:
        course_id = TARGET_COURSE_ID

    print(f"[Calibration] Using {len(chunks)} real ingested knowledge chunks from course {course_id}.")

    # 2. Curate representative in-scope questions grounded in real course documents
    in_scope_items = [
        # PDF Grounded (UNIT 2_BDA.pdf, Unit 1 intro to bigdata, Unit 1_material_BDA)
        {"question": "What is the role of NameNode and DataNode in HDFS architecture?", "label": "in_scope", "source_type": "pdf"},
        {"question": "How does MapReduce handle fault tolerance during node failures?", "label": "in_scope", "source_type": "pdf"},
        {"question": "Explain the 5 V's of Big Data: volume, velocity, variety, veracity, and value.", "label": "in_scope", "source_type": "pdf"},
        {"question": "What is the function of Secondary NameNode in Hadoop HDFS?", "label": "in_scope", "source_type": "pdf"},
        {"question": "How does block size in HDFS affect storage efficiency and parallel processing?", "label": "in_scope", "source_type": "pdf"},
        
        # PPTX Grounded (2.3 Data_Locality.pptx, 2.2 Data_Placement_Strategies.pptx, Cluster_Resource_Management.pptx)
        {"question": "What is data locality and why is moving computation cheaper than moving data?", "label": "in_scope", "source_type": "pptx"},
        {"question": "How does rack awareness work in data placement strategies across switches?", "label": "in_scope", "source_type": "pptx"},
        {"question": "Explain the difference between process-local, node-local, and rack-local data locality.", "label": "in_scope", "source_type": "pptx"},
        {"question": "What are the core responsibilities of a cluster resource manager like YARN or Mesos?", "label": "in_scope", "source_type": "pptx"},
        {"question": "How do replica placement policies ensure fault tolerance against rack failure?", "label": "in_scope", "source_type": "pptx"},

        # Multi-hop / Conceptual Notes Grounded
        {"question": "How does data locality relate to parallel task scheduling in distributed data processing?", "label": "in_scope", "source_type": "multi-hop"},
        {"question": "What are the trade-offs between shared-memory and distributed-memory architectures?", "label": "in_scope", "source_type": "multi-hop"},
        {"question": "Explain how YARN decouples resource management from the MapReduce execution model.", "label": "in_scope", "source_type": "multi-hop"},
        {"question": "What mechanisms prevent data loss when a slave node crashes in a Hadoop cluster?", "label": "in_scope", "source_type": "multi-hop"},
        {"question": "How do data serialization formats impact distributed network transfer efficiency?", "label": "in_scope", "source_type": "multi-hop"}
    ]

    # Additional sampled in-scope questions extracted from real chunks
    seen_docs = set()
    for c in chunks[:25]:
        doc = c.get("document_name", "")
        summary = c.get("content_summary", "")
        if summary and doc not in seen_docs and len(in_scope_items) < 25:
            seen_docs.add(doc)
            in_scope_items.append({
                "question": f"Explain {summary} as described in {doc}.",
                "label": "in_scope",
                "source_type": c.get("source_type", "document")
            })

    # 3. Off-scope questions (completely unrelated domains)
    off_scope_questions = [
        "How do you bake sourdough bread with an active starter at home?",
        "What is the capital city of Mongolia and its current population?",
        "Explain the combustion cycle in a liquid bipropellant rocket engine.",
        "Who won the 1994 FIFA World Cup soccer final in California?",
        "What is the secret recipe for chocolate molten lava cake?",
        "How do you replace front brake pads on a 2018 Honda Civic?",
        "What is the plot summary of Hamlet by William Shakespeare?",
        "Explain quantum chromodynamics and gluon color charge exchange.",
        "How do gardeners prevent aphids on tomato plants organically?",
        "What are the official rules of professional cricket bowling deliveries?",
        "What causes plate tectonics and continental drift in geology?",
        "How do dentists treat dental caries and root canal infections?",
        "What is the process of cellular mitosis in diploid eukaryotic cells?",
        "How does a four-stroke internal combustion engine cycle work?",
        "What are the historical origins of the French Impressionism art movement?"
    ]
    off_scope_items = [{"question": q, "label": "off_scope", "source_type": "off_scope"} for q in off_scope_questions]

    evaluation_set = in_scope_items + off_scope_items
    print(f"[Calibration] Evaluation dataset: {len(in_scope_items)} in-scope, {len(off_scope_items)} off-scope (Total: {len(evaluation_set)})")

    # 4. Measure top fused retrieval score and dense score for each question
    print("[Calibration] Running fused retrieval (RRF + BM25 + dense) across all evaluation questions...")
    question_scores = []
    for item in evaluation_set:
        retrieved = rag_engine.retrieve_chunks(course_id, item["question"], top_k=settings.MAX_RETRIEVED_CHUNKS)
        if retrieved:
            top_chk = retrieved[0]
            fused_score = top_chk.get("score", settings.FLOAT_ZERO)
            dense_sim = top_chk.get("dense_similarity", settings.FLOAT_ZERO)
        else:
            fused_score = settings.FLOAT_ZERO
            dense_sim = settings.FLOAT_ZERO

        question_scores.append({
            "question": item["question"],
            "label": item["label"],
            "source_type": item.get("source_type"),
            "fused_score": round(float(fused_score), 4),
            "dense_similarity": round(float(dense_sim), 4)
        })

    # 5. Grid search over candidate thresholds on fused score to maximize F1
    min_t = settings.CALIBRATION_MIN_THRESHOLD
    max_t = settings.CALIBRATION_MAX_THRESHOLD
    steps = settings.CALIBRATION_THRESHOLD_STEPS
    candidate_thresholds = np.linspace(min_t, max_t, steps)

    best_threshold = settings.RETRIEVAL_REFUSAL_THRESHOLD
    best_f1 = -settings.FLOAT_ONE
    best_metrics = {}
    pr_curve = []

    for t in candidate_thresholds:
        threshold = round(float(t), 4)
        tp = 0  # In-scope accepted (>= threshold)
        fp = 0  # Off-scope accepted (>= threshold)
        fn = 0  # In-scope rejected (< threshold)
        tn = 0  # Off-scope rejected (< threshold)

        for q in question_scores:
            predicted_in_scope = q["fused_score"] >= threshold
            actual_in_scope = (q["label"] == "in_scope")

            if predicted_in_scope and actual_in_scope:
                tp += 1
            elif predicted_in_scope and not actual_in_scope:
                fp += 1
            elif not predicted_in_scope and actual_in_scope:
                fn += 1
            else:
                tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else settings.FLOAT_ZERO
        recall = tp / (tp + fn) if (tp + fn) > 0 else settings.FLOAT_ZERO
        denom = precision + recall
        f1 = (2 * precision * recall) / denom if denom > settings.FLOAT_ZERO else settings.FLOAT_ZERO

        pr_entry = {
            "threshold": threshold,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn
        }
        pr_curve.append(pr_entry)

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_metrics = pr_entry

    print("=" * 65)
    print("[Calibration Results - Real Course Big Data Analytics]")
    print(f"Optimal RETRIEVAL_REFUSAL_THRESHOLD: {best_threshold}")
    print(f"Optimal F1 Score: {best_metrics.get('f1_score')}")
    print(f"Precision: {best_metrics.get('precision')} | Recall: {best_metrics.get('recall')}")
    print(f"Confusion Matrix: TP={best_metrics.get('tp')}, FP={best_metrics.get('fp')}, FN={best_metrics.get('fn')}, TN={best_metrics.get('tn')}")
    print("=" * 65)

    # 6. Save results to eval/refusal_calibration_results.json and backend/data/refusal_calibration_results.json
    result_data = {
        "course_id": course_id,
        "optimal_refusal_threshold": best_threshold,
        "optimal_f1_score": best_metrics.get("f1_score"),
        "optimal_precision": best_metrics.get("precision"),
        "optimal_recall": best_metrics.get("recall"),
        "confusion_matrix": {
            "tp": best_metrics.get("tp"),
            "fp": best_metrics.get("fp"),
            "fn": best_metrics.get("fn"),
            "tn": best_metrics.get("tn")
        },
        "evaluation_samples_count": len(evaluation_set),
        "in_scope_count": len(in_scope_items),
        "off_scope_count": len(off_scope_items),
        "evaluated_questions": question_scores
    }

    eval_dir = os.path.join(ROOT_DIR, "eval")
    os.makedirs(eval_dir, exist_ok=True)
    out_eval = os.path.join(eval_dir, "refusal_calibration_results.json")
    with open(out_eval, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2)

    data_dir = os.path.join(ROOT_DIR, "backend", "data")
    os.makedirs(data_dir, exist_ok=True)
    out_data = os.path.join(data_dir, "refusal_calibration_results.json")
    with open(out_data, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2)

    print(f"[Calibration] Saved optimal threshold and results to: {out_eval} and {out_data}")
    return best_threshold

if __name__ == "__main__":
    calibrate_refusal()
