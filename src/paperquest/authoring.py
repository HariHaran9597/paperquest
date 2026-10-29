"""Private, human-reviewed LangGraph workflow for drafting quest metadata.

This workflow never generates or executes Python. It can only propose a
QuestSpec for the one trusted experiment template shipped with PaperQuest.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable, TypedDict

import httpx
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import ValidationError

from paperquest.attention import TOKENS, run_attention
from paperquest.specs import QuestSpec, load_paper, validate_quest_evidence

ROOT = Path(__file__).resolve().parents[2]
APPROVED_DRAFTS = ROOT / "artifacts" / "approved-drafts"
SUPPORTED_EXPERIMENT = "fixed-toy-scaled-dot-product-attention-v1"


class AuthoringState(TypedDict, total=False):
    evidence: list[dict[str, Any]]
    draft: dict[str, Any]
    errors: list[str]
    validation_report: dict[str, Any]
    approved: bool
    saved_path: str


class DraftProvider:
    """Small OpenAI-compatible structured-output client; all config is env-only."""

    def __init__(self, *, client: httpx.Client | None = None):
        self.base_url = os.environ.get("PAPERQUEST_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.api_key = os.environ.get("PAPERQUEST_LLM_API_KEY", "")
        self.model = os.environ.get("PAPERQUEST_LLM_MODEL", "").strip()
        self.client = client or httpx.Client(timeout=httpx.Timeout(45.0, connect=10.0))

    def draft(self, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.api_key or not self.model:
            raise RuntimeError("Set PAPERQUEST_LLM_API_KEY and PAPERQUEST_LLM_MODEL to use local quest authoring.")
        schema = QuestSpec.model_json_schema()
        prompt = (
            "Draft a concise learner quest using only the supplied evidence. Return one JSON object "
            "matching the schema. Keep id unique, version 1.0.0, paper_id equal to the supplied "
            "paper id, experiment_id exactly fixed-toy-scaled-dot-product-attention-v1, and inputs "
            "consistent with the supplied fixed token sequence. Do not invent paper claims or citations. "
            "The experiment is an illustrative fixed-vector toy, not a trained model reproduction.\n\n"
            f"PAPER/EVIDENCE: {json.dumps(evidence, ensure_ascii=False)}\n\n"
            f"JSON SCHEMA: {json.dumps(schema)}"
        )
        response = self.client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": 0,
                "max_tokens": 1800,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": "You draft evidence-grounded learning metadata. Output JSON only."},
                    {"role": "user", "content": prompt},
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise RuntimeError("The configured provider returned no JSON text.")
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("The configured provider returned invalid JSON.") from exc
        if not isinstance(result, dict):
            raise RuntimeError("The configured provider response must be a JSON object.")
        return result


def build_authoring_graph(
    drafter: Callable[[list[dict[str, Any]]], dict[str, Any]],
    *,
    output_dir: Path = APPROVED_DRAFTS,
):
    """Build a testable graph with an explicit human approval interrupt."""

    def load_evidence(_: AuthoringState) -> AuthoringState:
        paper = load_paper()
        evidence = [
            {"paper_id": paper.id, "paper_title": paper.title, "authors": paper.authors,
             **passage.model_dump(mode="json")}
            for passage in paper.passages
        ]
        return {"evidence": evidence}  # type: ignore[typeddict-item]

    def create_draft(state: AuthoringState) -> AuthoringState:
        evidence = state.get("evidence", [])
        try:
            return {"draft": drafter(evidence), "errors": []}
        except Exception as exc:  # provider error messages can contain request details
            return {"errors": [f"Draft provider failed ({type(exc).__name__}). Check local configuration and retry."]}

    def validate_draft(state: AuthoringState) -> AuthoringState:
        errors = list(state.get("errors", []))
        if errors:
            return {"errors": errors}
        try:
            quest = QuestSpec.model_validate(state.get("draft"))
            paper = load_paper()
            validate_quest_evidence(quest, paper)
            if quest.experiment_id != SUPPORTED_EXPERIMENT:
                errors.append("Draft requested an unsupported experiment template.")
            if quest.inputs.tokens != list(TOKENS):
                errors.append("Draft token sequence differs from the trusted experiment inputs.")
            if quest.paper_id != paper.id:
                errors.append("Draft paper does not match the loaded evidence bundle.")
            return {"draft": quest.model_dump(mode="json"), "errors": errors}
        except (ValidationError, ValueError, TypeError):
            return {"errors": ["Draft failed schema or evidence validation. Inspect provider output locally."]}

    def evaluate(state: AuthoringState) -> AuthoringState:
        errors = list(state.get("errors", []))
        if errors:
            return {"errors": errors}
        quest = QuestSpec.model_validate(state["draft"])
        sample = run_attention(quest.inputs.default_query_token, quest.inputs.default_position_strength)
        report = {
            "schema_valid": True,
            "evidence_ids_resolve": True,
            "supported_experiment": quest.experiment_id == SUPPORTED_EXPERIMENT,
            "sample_run_succeeded": len(sample["weights"]) == len(quest.inputs.tokens),
            "weights_sum_to_one": abs(sum(sample["weights"]) - 1.0) < 1e-5,
            "note": "These checks validate structure and execution only; a human must verify claim accuracy against the cited paper.",
        }
        if not all(report[key] for key in ("schema_valid", "evidence_ids_resolve", "supported_experiment", "sample_run_succeeded", "weights_sum_to_one")):
            errors.append("Deterministic draft checks failed.")
        return {"validation_report": report, "errors": errors}

    def approval_gate(state: AuthoringState) -> AuthoringState:
        decision = interrupt({
            "type": "quest_review",
            "draft": state.get("draft"),
            "validation_report": state.get("validation_report"),
            "instruction": "Review every claim and source, then resume with approve or reject.",
        })
        approved = decision == "approve"
        return {"approved": approved}

    def persist(state: AuthoringState) -> AuthoringState:
        if not state.get("approved"):
            return {"approved": False}
        quest = QuestSpec.model_validate(state["draft"])
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "-", quest.id).strip("-")[:80]
        path = output_dir / f"{safe_id}-{quest.version}.json"
        path.write_text(json.dumps(quest.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
        return {"approved": True, "saved_path": str(path)}

    def after_create(state: AuthoringState) -> str:
        return "stop" if state.get("errors") else "validate"

    def after_validation(state: AuthoringState) -> str:
        return "stop" if state.get("errors") else "evaluate"

    def after_evaluation(state: AuthoringState) -> str:
        return "stop" if state.get("errors") else "review"

    graph = StateGraph(AuthoringState)
    graph.add_node("load_evidence", load_evidence)
    graph.add_node("create_draft", create_draft)
    graph.add_node("validate", validate_draft)
    graph.add_node("evaluate", evaluate)
    graph.add_node("review", approval_gate)
    graph.add_node("persist", persist)
    graph.add_edge(START, "load_evidence")
    graph.add_edge("load_evidence", "create_draft")
    graph.add_conditional_edges("create_draft", after_create, {"validate": "validate", "stop": END})
    graph.add_conditional_edges("validate", after_validation, {"evaluate": "evaluate", "stop": END})
    graph.add_conditional_edges("evaluate", after_evaluation, {"review": "review", "stop": END})
    graph.add_edge("review", "persist")
    graph.add_edge("persist", END)
    return graph.compile(checkpointer=MemorySaver())


def run_local_review() -> None:
    """Run the optional local authoring flow; public routes never call this."""
    provider = DraftProvider()
    graph = build_authoring_graph(provider.draft)
    config = {"configurable": {"thread_id": "local-paperquest-authoring"}}
    result = graph.invoke({}, config=config)
    if result.get("errors"):
        raise SystemExit(result["errors"][0])
    review = result.get("__interrupt__", ())
    if not review:
        raise SystemExit("Authoring flow did not reach the review gate.")
    payload = review[0].value
    print(json.dumps({"draft": payload["draft"], "checks": payload["validation_report"]}, indent=2))
    decision = input("Type approve to save a local draft, or anything else to reject: ").strip().lower()
    final = graph.invoke(Command(resume="approve" if decision == "approve" else "reject"), config=config)
    if final.get("approved"):
        print(f"Reviewed draft saved locally: {final['saved_path']} (not published automatically).")
    else:
        print("Draft rejected. No artifact saved.")


if __name__ == "__main__":
    run_local_review()
