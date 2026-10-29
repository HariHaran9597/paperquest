"""Run deterministic invariants over the supported attention experiment."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from paperquest.attention import TOKENS, run_attention


def evaluate() -> dict:
    strengths = (0.0, 0.25, 0.5, 0.75, 1.0)
    cases = [(query, strength) for query in range(len(TOKENS)) for strength in strengths]
    passed = 0
    failures: list[dict] = []
    for query, strength in cases:
        first = run_attention(query, strength)
        second = run_attention(query, strength)
        checks = {
            "finite_scores": all(math.isfinite(value) for value in first["scores"]),
            "finite_weights": all(math.isfinite(value) for value in first["weights"]),
            "weights_normalize": math.isclose(sum(first["weights"]), 1.0, abs_tol=1e-5),
            "repeatable": first == second,
            "expected_dimensions": len(first["weights"]) == len(TOKENS) and len(first["output_vector"]) == 4,
        }
        passed += sum(checks.values())
        failures.extend(
            {"query_token": query, "position_strength": strength, "failed_check": name}
            for name, ok in checks.items() if not ok
        )
    total = len(cases) * 5
    return {
        "suite": "deterministic-attention-invariants",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cases": len(cases),
        "checks_per_case": 5,
        "checks_passed": passed,
        "checks_total": total,
        "pass_rate": round(passed / total, 4),
        "failures": failures,
        "scope_note": "Checks numeric invariants and repeatability of fixed teaching vectors only. They do not measure semantic correctness, paper fidelity, or trained-model quality.",
    }


if __name__ == "__main__":
    report = evaluate()
    target = Path(__file__).resolve().parents[1] / "docs" / "evaluation-report.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
