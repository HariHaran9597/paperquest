import json

from langgraph.types import Command

from paperquest.authoring import build_authoring_graph
from paperquest.specs import load_quest


def test_langgraph_requires_human_approval_before_saving(tmp_path):
    draft = load_quest().model_dump(mode="json")
    graph = build_authoring_graph(lambda _evidence: draft, output_dir=tmp_path)
    config = {"configurable": {"thread_id": "test-review"}}

    paused = graph.invoke({}, config=config)
    assert paused["__interrupt__"][0].value["type"] == "quest_review"
    assert paused["__interrupt__"][0].value["validation_report"]["weights_sum_to_one"] is True
    assert list(tmp_path.iterdir()) == []

    rejected = graph.invoke(Command(resume="reject"), config=config)
    assert rejected["approved"] is False
    assert list(tmp_path.iterdir()) == []


def test_approved_authoring_result_is_json_draft_not_publication(tmp_path):
    draft = load_quest().model_dump(mode="json")
    graph = build_authoring_graph(lambda _evidence: draft, output_dir=tmp_path)
    config = {"configurable": {"thread_id": "test-approve"}}
    graph.invoke({}, config=config)
    approved = graph.invoke(Command(resume="approve"), config=config)

    saved = tmp_path / "attention-is-all-you-need-positional-signal-v1-1.0.0.json"
    assert approved["approved"] is True
    assert saved.exists()
    assert json.loads(saved.read_text(encoding="utf-8"))["experiment_id"] == draft["experiment_id"]
