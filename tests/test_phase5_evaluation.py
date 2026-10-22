import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.evaluation.ragas_eval import evaluation_suite
from eval.fixtures.sample_loader import seed_demo_course_if_needed, DEMO_COURSE_ID

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_course():
    seed_demo_course_if_needed()

def test_golden_evaluation_set_structure():
    """
    Phase 5: Golden evaluation set contains at least 30 items,
    including 8-10 unsupported questions and multimodal questions.
    """
    dataset = evaluation_suite.get_benchmark_dataset(DEMO_COURSE_ID)
    assert len(dataset) >= 30

    unsupported_items = [item for item in dataset if not item["is_answerable"]]
    assert len(unsupported_items) >= 8

    video_items = [item for item in dataset if item["type"] == "video"]
    assert len(video_items) >= 2

    visual_items = [item for item in dataset if item["type"] == "visual"]
    assert len(visual_items) >= 2

def test_rag_benchmark_real_metrics_computation():
    """
    Phase 5: Execute benchmark and verify all metrics are computed by code:
    Faithfulness, Relevancy, Precision, Recall, Citation Accuracy, Unsupported Refusal,
    False Refusal Rate, BKT AUC, and BKT Log-Loss.
    """
    # Run evaluation
    results = evaluation_suite.run_rag_evaluation(DEMO_COURSE_ID)

    assert "faithfulness" in results
    assert "answer_relevancy" in results
    assert "context_precision" in results
    assert "context_recall" in results
    assert "citation_accuracy" in results
    assert "unsupported_rate" in results
    assert "false_refusal_rate" in results
    assert "question_verification_rate" in results
    assert "bkt_auc" in results
    assert "bkt_log_loss" in results

    # Verify score bounds
    assert 0.0 <= results["faithfulness"] <= 1.0
    assert 0.0 <= results["answer_relevancy"] <= 1.0
    assert 0.0 <= results["context_precision"] <= 1.0
    assert 0.0 <= results["context_recall"] <= 1.0
    assert 0.0 <= results["citation_accuracy"] <= 1.0
    assert 0.0 <= results["unsupported_rate"] <= 1.0
    assert 0.0 <= results["false_refusal_rate"] <= 1.0
    assert 0.5 <= results["bkt_auc"] <= 1.0 # Standard valid AUC range
    assert results["bkt_log_loss"] > 0.0

    assert results["total_test_cases"] >= 30
    assert len(results["test_results"]) >= 30

def test_evaluation_export_endpoints():
    """
    Phase 5: Export results to JSON and CSV endpoints.
    """
    from tests.conftest import make_test_auth_headers
    headers = make_test_auth_headers("student_phase5_test")

    # 1. JSON Export
    json_res = client.get("/api/evaluation/export/json", headers=headers)
    assert json_res.status_code == 200
    json_data = json_res.json()
    assert "faithfulness" in json_data
    assert "test_results" in json_data

    # 2. CSV Export
    csv_res = client.get("/api/evaluation/export/csv", headers=headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    csv_text = csv_res.text
    assert "Faithfulness" in csv_text
    assert "Answer Relevancy" in csv_text
    assert "gold_" in csv_text or "eval_" in csv_text or "Case ID" in csv_text
