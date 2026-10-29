from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from paperquest.attention import TOKENS, run_attention

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"

app = FastAPI(title="PaperQuest API", version="0.1.0")


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_token: int = Field(ge=0, lt=len(TOKENS))
    position_strength: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.get("/api/v1/quest")
def get_quest() -> dict:
    return {
        "id": "attention-is-all-you-need-positional-signal-v1",
        "version": "1.0.0",
        "title": "Attention Is All You Need",
        "authors": "Ashish Vaswani et al.",
        "venue": "NeurIPS 2017",
        "paper_url": "https://arxiv.org/abs/1706.03762",
        "audience": "ML and GenAI developers learning attention",
        "objective": "Inspect how a position signal changes one query's attention scores, weights, and output.",
        "claim": "Scaled dot-product attention computes compatibility scores, normalizes them with softmax, and uses the weights to combine value vectors.",
        "evidence": [
            {
                "section": "3.2.1 Scaled Dot-Product Attention",
                "reference": "Vaswani et al. (2017), paper section 3.2.1, page 3",
                "url": "https://arxiv.org/pdf/1706.03762#page=3",
            },
            {
                "section": "3.5 Positional Encoding",
                "reference": "Vaswani et al. (2017), paper section 3.5, page 5",
                "url": "https://arxiv.org/pdf/1706.03762#page=5",
            },
        ],
        "tokens": list(TOKENS),
        "defaults": {"query_token": 4, "position_strength": 0.72},
        "limitations": [
            "Vectors are fixed teaching inputs, not learned embeddings.",
            "This single attention row is not a reproduction of the trained Transformer or paper results.",
        ],
    }


@app.post("/api/v1/experiment/run")
def run_experiment(request: ExperimentRequest) -> dict:
    try:
        return run_attention(request.query_token, request.position_strength)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")

