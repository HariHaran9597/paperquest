"""Versioned paper and quest schemas plus citation-reference checks."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

RESOURCE_DATA = Path(__file__).resolve().parent / "resources" / "data"
PAPER_PATH = RESOURCE_DATA / "papers" / "attention-is-all-you-need.json"
QUEST_PATH = RESOURCE_DATA / "quests" / "attention-v1.json"


class EvidencePassage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(min_length=1, max_length=80)
    section: str = Field(min_length=1, max_length=160)
    page: int = Field(ge=1, le=50)
    url: HttpUrl
    curator_note: str = Field(min_length=10, max_length=500)


class PaperSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    authors: str = Field(min_length=1, max_length=200)
    venue: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1900, le=2100)
    url: HttpUrl
    passages: list[EvidencePassage] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique_passage_ids(self) -> "PaperSpec":
        ids = [passage.id for passage in self.passages]
        if len(ids) != len(set(ids)):
            raise ValueError("Paper passage IDs must be unique")
        return self


class TokenInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tokens: list[str] = Field(min_length=2, max_length=64)
    default_query_token: int = Field(ge=0)
    default_position_strength: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    baseline_position_strength: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    position_strength_min: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    position_strength_max: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)

    @model_validator(mode="after")
    def valid_defaults(self) -> "TokenInputs":
        from paperquest.attention import TOKENS

        if self.tokens != list(TOKENS):
            raise ValueError("Quest tokens must match the supported experiment template")
        if self.default_query_token >= len(self.tokens):
            raise ValueError("default_query_token must identify a token")
        if self.position_strength_min >= self.position_strength_max:
            raise ValueError("position strength bounds must be increasing")
        if not self.position_strength_min <= self.default_position_strength <= self.position_strength_max:
            raise ValueError("default_position_strength must be within the input bounds")
        if not self.position_strength_min <= self.baseline_position_strength <= self.position_strength_max:
            raise ValueError("baseline_position_strength must be within the input bounds")
        return self


class QuizOption(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^[a-z]$")
    text: str = Field(min_length=1, max_length=240)


class QuizSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    question: str = Field(min_length=10, max_length=300)
    options: list[QuizOption] = Field(min_length=2, max_length=6)
    correct_option_id: str = Field(pattern=r"^[a-z]$")
    explanation: str = Field(min_length=10, max_length=400)

    @model_validator(mode="after")
    def correct_option_exists(self) -> "QuizSpec":
        ids = [option.id for option in self.options]
        if len(ids) != len(set(ids)) or self.correct_option_id not in ids:
            raise ValueError("Quiz option IDs must be unique and include the correct answer")
        return self


class QuestSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(min_length=1, max_length=100)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    paper_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    audience: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=10, max_length=400)
    question: str = Field(min_length=10, max_length=400)
    claim: str = Field(min_length=10, max_length=500)
    evidence_ids: list[str] = Field(min_length=1, max_length=10)
    experiment_id: str = Field(pattern=r"^[a-z0-9-]{1,100}$")
    inputs: TokenInputs
    quiz: QuizSpec
    limitations: list[str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def unique_evidence_ids(self) -> "QuestSpec":
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Quest evidence IDs must be unique")
        return self


def validate_quest_evidence(quest: QuestSpec, paper: PaperSpec) -> None:
    """Ensure the quest points only at evidence belonging to its selected paper."""
    if quest.paper_id != paper.id:
        raise ValueError("Quest paper_id does not match the loaded paper")
    available = {passage.id for passage in paper.passages}
    missing = set(quest.evidence_ids) - available
    if missing:
        raise ValueError(f"Quest references missing evidence IDs: {', '.join(sorted(missing))}")


@lru_cache(maxsize=1)
def load_paper() -> PaperSpec:
    return PaperSpec.model_validate(json.loads(PAPER_PATH.read_text(encoding="utf-8")))


@lru_cache(maxsize=1)
def load_quest() -> QuestSpec:
    quest = QuestSpec.model_validate(json.loads(QUEST_PATH.read_text(encoding="utf-8")))
    validate_quest_evidence(quest, load_paper())
    return quest
