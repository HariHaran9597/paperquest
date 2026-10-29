import math

from fastapi.testclient import TestClient

from paperquest.attention import TOKENS, run_attention
from paperquest.main import app
from paperquest.specs import load_paper, load_quest, validate_quest_evidence

client = TestClient(app)


def test_attention_weights_are_a_probability_distribution():
    result = run_attention(query_token=4, position_strength=0.72)
    assert len(result["weights"]) == len(TOKENS)
    assert all(0 <= weight <= 1 for weight in result["weights"])
    assert math.isclose(sum(result["weights"]), 1.0, abs_tol=1e-5)
    assert len(result["output_vector"]) == 4


def test_changing_position_signal_changes_deterministic_result():
    off = run_attention(query_token=4, position_strength=0.0)
    on = run_attention(query_token=4, position_strength=0.72)
    assert off["scores"] != on["scores"]
    assert off["weights"] != on["weights"]


def test_health_and_curated_quest_are_available():
    assert client.get("/health").json() == {"status": "ok", "version": "0.2.0"}
    assert client.get("/ready").json() == {"status": "ready", "content": "valid"}
    quest = client.get("/api/v1/quest").json()
    assert quest["paper_url"] == "https://arxiv.org/abs/1706.03762"
    assert {item["section"] for item in quest["evidence"]} == {
        "3.2.1 Scaled Dot-Product Attention",
        "3.5 Positional Encoding",
    }
    assert "curator_note" in quest["evidence"][0]


def test_experiment_endpoint_returns_inspectable_intermediates():
    response = client.post(
        "/api/v1/experiment/run",
        json={"query_token": 4, "position_strength": 0.72},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["scores"]) == len(TOKENS)
    assert len(body["weights"]) == len(TOKENS)
    assert body["method"] == "softmax(QK^T / sqrt(d_k)) V"
    assert "does not reproduce" in body["limitation"]


def test_invalid_inputs_are_rejected():
    assert client.post(
        "/api/v1/experiment/run",
        json={"query_token": 99, "position_strength": 0.5},
    ).status_code == 422
    assert client.post(
        "/api/v1/experiment/run",
        json={"query_token": 1, "position_strength": 1.2},
    ).status_code == 422
    assert client.post(
        "/api/v1/experiment/run",
        json={"query_token": 1, "position_strength": 0.5, "code": "print(1)"},
    ).status_code == 422


def test_versioned_spec_resolves_every_evidence_reference():
    quest, paper = load_quest(), load_paper()
    validate_quest_evidence(quest, paper)
    assert set(quest.evidence_ids) == {passage.id for passage in paper.passages}


def test_compare_endpoint_returns_two_runs_and_weight_deltas():
    response = client.post(
        "/api/v1/experiment/compare",
        json={"query_token": 4, "position_strength": 0.72},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["baseline"]["position_strength"] == 0.0
    assert result["current"]["position_strength"] == 0.72
    assert len(result["weights_delta"]) == len(TOKENS)


def test_quiz_checks_answer_without_exposing_it_in_quest_payload():
    quest = client.get("/api/v1/quest").json()
    assert "correct_option_id" not in quest["quiz"]
    assert client.post("/api/v1/quiz/answer", json={"option_id": "a"}).json()["correct"] is True
    assert client.post("/api/v1/quiz/answer", json={"option_id": "b"}).json()["correct"] is False
    assert client.post("/api/v1/quiz/answer", json={"option_id": "z"}).status_code == 422


def test_security_headers_and_oversized_request_guard():
    health = client.get("/health")
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    response = client.post(
        "/api/v1/experiment/run",
        content=b" " * 16_385,
        headers={"content-type": "application/json", "content-length": "16385"},
    )
    assert response.status_code == 413

