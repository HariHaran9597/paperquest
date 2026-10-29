import math

from fastapi.testclient import TestClient

from paperquest.attention import TOKENS, run_attention
from paperquest.main import app

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
    assert client.get("/health").json() == {"status": "ok", "version": "0.1.0"}
    quest = client.get("/api/v1/quest").json()
    assert quest["paper_url"] == "https://arxiv.org/abs/1706.03762"
    assert {item["section"] for item in quest["evidence"]} == {
        "3.2.1 Scaled Dot-Product Attention",
        "3.5 Positional Encoding",
    }


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

