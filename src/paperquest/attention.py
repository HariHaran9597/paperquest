"""Deterministic toy scaled-dot-product attention for the first PaperQuest."""

from __future__ import annotations

import math

TOKENS = ("The", "animal", "didn't", "cross", "it", "because", "was tired")

# Hand-authored vectors make the experiment deterministic and inspectable.
# They are teaching inputs, not trained Transformer embeddings.
EMBEDDINGS = (
    (0.9, 0.1, 0.0, 0.2),
    (0.2, 1.0, 0.3, 0.1),
    (-0.1, 0.2, 0.9, 0.1),
    (0.0, 0.3, 0.1, 1.0),
    (0.1, 0.8, 0.5, 0.2),
    (0.4, -0.1, 0.5, 0.4),
    (0.8, 0.1, 0.2, -0.2),
)


def _position(position: int, strength: float) -> tuple[float, ...]:
    return (
        strength * math.sin(position),
        strength * math.cos(position),
        strength * math.sin(position / 100.0),
        strength * math.cos(position / 100.0),
    )


def _dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def run_attention(query_token: int, position_strength: float) -> dict:
    """Run one deterministic attention row and return inspectable intermediates."""
    if not 0 <= query_token < len(TOKENS):
        raise ValueError(f"query_token must be between 0 and {len(TOKENS) - 1}")
    if not math.isfinite(position_strength) or not 0.0 <= position_strength <= 1.0:
        raise ValueError("position_strength must be between 0 and 1")

    q = tuple(
        value + offset
        for value, offset in zip(
            EMBEDDINGS[query_token], _position(query_token, position_strength), strict=True
        )
    )
    keys = [
        tuple(value + offset for value, offset in zip(embedding, _position(i, position_strength), strict=True))
        for i, embedding in enumerate(EMBEDDINGS)
    ]
    values = EMBEDDINGS
    scale = math.sqrt(len(q))
    scores = [_dot(q, key) / scale for key in keys]
    peak = max(scores)
    exponentials = [math.exp(score - peak) for score in scores]
    denominator = sum(exponentials)
    weights = [value / denominator for value in exponentials]
    output = [
        sum(weights[i] * values[i][dimension] for i in range(len(TOKENS)))
        for dimension in range(len(q))
    ]
    return {
        "query_token": query_token,
        "query_label": TOKENS[query_token],
        "position_strength": position_strength,
        "scores": [round(score, 6) for score in scores],
        "weights": [round(weight, 6) for weight in weights],
        "output_vector": [round(value, 6) for value in output],
        "most_attended_token": TOKENS[weights.index(max(weights))],
        "tokens": list(TOKENS),
        "method": "softmax(QK^T / sqrt(d_k)) V",
        "limitation": "Fixed teaching vectors only; this does not reproduce a trained Transformer or the paper's results.",
    }

