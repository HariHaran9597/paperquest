# PaperQuest

**Turn a research-paper idea into a small experiment you can run, change, and inspect.**

PaperQuest is a no-login learning app for ML and GenAI learners. Its first quest uses the attention equation from [Attention Is All You Need](https://arxiv.org/abs/1706.03762). Change a query token and a teaching positional-signal strength; inspect the scaled scores, softmax weights, weighted value output, and a controlled off/on comparison.

## Try it locally

Requires Python 3.11 or newer. No API key or GPU is needed for the learner app.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m uvicorn paperquest.main:app --app-dir src --reload
```

Open `http://127.0.0.1:8000`. Health and readiness are at `/health` and `/ready`; interactive API docs are at `/docs`.

## What the learner can do

- Read a curated quest with versioned paper metadata and links to the cited sections/pages.
- Select a query token and run the deterministic scaled dot-product attention calculation.
- Inspect scores, normalized weights, and the weighted value output.
- Compare the selected positional-signal strength with a zero-signal baseline.
- Answer a short comprehension question and receive feedback.
- See explicit limitations beside the source material.

The inputs are fixed, hand-authored teaching vectors. The positional signal is a simplified illustration applied to query/key vectors. This is **not** a trained Transformer, a reproduction of the paper's model, or evidence about benchmark performance.

## Private local quest authoring (optional)

LangGraph powers a separate command-line workflow for drafting quest metadata. It uses only the bundled evidence passages, validates the `QuestSpec`, verifies evidence IDs, runs the trusted experiment, and pauses for human review. Approving saves a JSON draft under `artifacts/approved-drafts/`; it does not publish or alter the learner-facing quest. The authoring path never generates or executes code and is not called by public endpoints.

Install the optional dependency and configure an OpenAI-compatible endpoint in your local environment:

```powershell
python -m pip install -e ".[authoring]"
$env:PAPERQUEST_LLM_API_KEY = "your-key"
$env:PAPERQUEST_LLM_BASE_URL = "https://api.openai.com/v1"
$env:PAPERQUEST_LLM_MODEL = "model-available-to-your-provider"
paperquest-author
```

The key is read only from the environment, is never committed, and is not needed to run the app. Provider usage may incur cost according to that provider. The local graph uses an in-memory checkpoint for its one interactive CLI process; a process restart requires starting the draft again.

## Engineering and checks

```powershell
python -m pytest
node --check src/paperquest/web/app.js
python scripts/evaluate.py
```

The deterministic suite evaluates 35 combinations (7 query tokens × 5 signal strengths) for 175 numeric and repeatability invariants. It does not score semantic accuracy, evidence entailment, user learning, paper fidelity, or model quality. The report is in [`docs/evaluation-report.json`](docs/evaluation-report.json). Every citation still needs human review.

GitHub Actions runs tests, compile checks, JavaScript syntax check, and evaluation on pushes and pull requests. `Dockerfile` provides a host-neutral non-root container image; it is not deployed yet. Hosting and a public demo URL are intentionally left for a separate decision.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the components, data flow, trust boundaries, and operational limits. The public request path is:

```text
Browser → FastAPI + Pydantic → fixed attention function
        ↘ bundled, versioned paper and quest JSON
```

## Security and operating limits

- API inputs are schema-validated; unknown fields are rejected.
- The server runs only its own fixed experiment function. It does not accept uploaded documents or execute user/model-generated code.
- The API has basic request-size checks, response security headers, and a per-process in-memory rate limit. That limit is appropriate only for a small single-instance demo; it is not a distributed abuse-control system.
- There are no accounts, persistent learner records, telemetry, or public LLM calls.
- The authoring provider key stays server-side in a local environment variable. Never put it in browser code, screenshots, logs, or Git.

## Current release boundary

Complete in this repository: one learner quest, deterministic experiment and comparison, source-linked content, quiz, local human-reviewed authoring workflow, automated checks, Docker packaging, and documentation. Deferred: hosting, additional quests, arbitrary paper ingestion, public AI generation, accounts, learner history, MCP tools, and user-submitted code execution.
