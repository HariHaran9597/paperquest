# PaperQuest

**Turn one AI paper into one small experiment you can run, change, and understand.**

PaperQuest is for ML and GenAI learners who can read a paper's terminology but want a concrete way to inspect the mechanism. The first quest uses the attention equation from [Attention Is All You Need](https://arxiv.org/abs/1706.03762). Change the selected query token or positional-signal strength, then inspect the scaled scores, softmax weights, and weighted value output.

## What is real in this release

- A browser UI calls a FastAPI endpoint; the backend validates the inputs and calculates the result.
- The experiment uses fixed, versioned teaching vectors and deterministic Python math. No account, model API key, or GPU is needed.
- The page links each paper claim to its paper section and page.
- Invalid inputs are rejected. The server runs only its fixed attention function; it never executes visitor-submitted code.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m uvicorn paperquest.main:app --app-dir src --reload
```

Open `http://127.0.0.1:8000`. API docs are at `/docs`; health is at `/health`.

Run checks with:

```powershell
python -m pytest
```

## Evaluation and limitation

Tests check input bounds, deterministic behavior, probability normalization, source metadata, and API responses. The vectors are deliberately fixed teaching inputs, **not learned embeddings**. This is an illustration of scaled dot-product attention, not a trained Transformer reproduction and not a reproduction of the paper's benchmark results. The first release does not generate new quests at runtime.

## Architecture

```text
Browser UI → FastAPI/Pydantic validation → deterministic attention function
          ↘ curated quest metadata → arXiv source references
```

The first quest is prebuilt; normal visitors trigger no LLM calls. Quest-authoring automation, additional papers, user accounts, arbitrary code execution, and MCP tools are outside v0.1.0. This is deliberate: an authoring agent would add complexity without improving the first learner's experience. The ML concept is the experiment itself; the project is not an LLM wrapper.

## Deploy

`render.yaml` defines a free Render web service, including the health check. Free instances can sleep after inactivity, so first load may take about a minute. The demo stores no user data and makes no paid model calls.

