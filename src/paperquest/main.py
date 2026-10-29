from __future__ import annotations

import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from paperquest.attention import TOKENS, run_attention
from paperquest.specs import load_paper, load_quest

WEB = Path(__file__).resolve().parent / "web"

app = FastAPI(title="PaperQuest API", version="0.2.0", docs_url="/docs", redoc_url=None)
_requests: dict[str, deque[float]] = defaultdict(deque)
_RATE_LIMIT = 120
_RATE_WINDOW_SECONDS = 60
_last_bucket_cleanup = 0.0
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' "
        "https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'"
    ),
}


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_token: int = Field(ge=0, lt=len(TOKENS))
    position_strength: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)


class QuizAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    option_id: str = Field(pattern=r"^[a-z]$")


@app.middleware("http")
async def request_safety(request: Request, call_next):
    """Small per-process guardrail suitable for this single-instance demo."""
    global _last_bucket_cleanup
    if request.url.path.startswith("/api/"):
        client_key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        if now - _last_bucket_cleanup >= _RATE_WINDOW_SECONDS:
            stale = [key for key, values in _requests.items() if not values or now - values[-1] >= _RATE_WINDOW_SECONDS]
            for key in stale:
                _requests.pop(key, None)
            _last_bucket_cleanup = now
        bucket = _requests[client_key]
        while bucket and now - bucket[0] >= _RATE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= _RATE_LIMIT:
            response = JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
            response.headers.update(_SECURITY_HEADERS)
            return response
        bucket.append(now)
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > 16_384:
            response = JSONResponse(status_code=413, content={"detail": "Request body is too large"})
            response.headers.update(_SECURITY_HEADERS)
            return response
    response = await call_next(request)
    response.headers.update(_SECURITY_HEADERS)
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.get("/ready")
def readiness() -> dict[str, str]:
    """Validate the bundled content files at startup/readiness probe time."""
    load_paper()
    load_quest()
    return {"status": "ready", "content": "valid"}


@app.get("/api/v1/quest")
def get_quest() -> dict:
    quest = load_quest()
    paper = load_paper()
    passages = {passage.id: passage for passage in paper.passages}
    return {
        "id": quest.id,
        "version": quest.version,
        "title": quest.title,
        "authors": paper.authors,
        "venue": paper.venue,
        "paper_url": str(paper.url),
        "audience": quest.audience,
        "objective": quest.objective,
        "question": quest.question,
        "claim": quest.claim,
        "evidence": [
            {
                "id": passages[evidence_id].id,
                "section": passages[evidence_id].section,
                "reference": f"{paper.authors} ({paper.year}), paper section {passages[evidence_id].section}, page {passages[evidence_id].page}",
                "url": str(passages[evidence_id].url),
                "curator_note": passages[evidence_id].curator_note,
            }
            for evidence_id in quest.evidence_ids
        ],
        "tokens": quest.inputs.tokens,
        "defaults": {"query_token": quest.inputs.default_query_token, "position_strength": quest.inputs.default_position_strength},
        "baseline_position_strength": quest.inputs.baseline_position_strength,
        "quiz": {"question": quest.quiz.question, "options": [option.model_dump() for option in quest.quiz.options]},
        "limitations": quest.limitations,
    }


@app.post("/api/v1/experiment/run")
def run_experiment(request: ExperimentRequest) -> dict:
    try:
        return run_attention(request.query_token, request.position_strength)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/experiment/compare")
def compare_experiment(request: ExperimentRequest) -> dict:
    baseline_strength = load_quest().inputs.baseline_position_strength
    baseline = run_attention(request.query_token, baseline_strength)
    current = run_attention(request.query_token, request.position_strength)
    return {
        "baseline": baseline,
        "current": current,
        "weights_delta": [round(after - before, 6) for before, after in zip(baseline["weights"], current["weights"], strict=True)],
        "baseline_label": "Position signal off",
        "current_label": f"Position signal {request.position_strength:.0%}",
        "interpretation": "This shows how this fixed teaching example changes when the input signal changes; it is not a claim about a trained model.",
    }


@app.post("/api/v1/quiz/answer")
def answer_quiz(answer: QuizAnswer) -> dict[str, str | bool]:
    quiz = load_quest().quiz
    known_options = {option.id for option in quiz.options}
    if answer.option_id not in known_options:
        raise HTTPException(status_code=422, detail="Choose one of the listed options")
    return {
        "correct": answer.option_id == quiz.correct_option_id,
        "explanation": quiz.explanation,
        "feedback": "Correct." if answer.option_id == quiz.correct_option_id else "Not quite. Review the paper idea and try again.",
    }


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")

