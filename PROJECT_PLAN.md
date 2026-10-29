# PaperQuest release plan

## Product

PaperQuest helps ML/GenAI learners turn a research-paper idea into a small experiment they can inspect. The first release focuses on the attention equation in *Attention Is All You Need*.

## Release 0.2.0 — repository-complete v1

This release is code-complete when the following are present and verified:

- Public learner flow works without login, API key, or GPU.
- Paper and quest are versioned structured data; every quest evidence ID resolves to a stored passage and paper link.
- Learners can select a query token, adjust the fixed teaching positional signal, run the attention calculation, inspect intermediates, compare against the zero-signal baseline, and answer a short quiz.
- The app labels the experiment as fixed synthetic teaching inputs, not a trained model or paper reproduction.
- FastAPI validates inputs; health/readiness endpoints, security headers, request-size check, and documented single-process rate limit are present.
- Optional LangGraph CLI drafts only structured quest metadata, validates it against the trusted template/evidence, runs deterministic checks, pauses for human review, and saves only a local draft after explicit approval.
- Tests, deterministic numeric eval, CI, Docker packaging, architecture/security notes, and setup instructions are committed.

## Release checks

```powershell
python -m pytest -q
node --check src/paperquest/web/app.js
python scripts/evaluate.py
```

The eval covers numeric invariants and repeatability across query-token/signal combinations. It does not establish semantic correctness, claim/evidence entailment, learning outcomes, or similarity to a trained model. Paper claims need human source review.

## Deferred from this repo-completion milestone

- Select a host, deploy, configure a domain, and verify a stable public URL.
- Add papers or user-submitted paper ingestion.
- Publish AI-generated quests; public AI calls are intentionally absent.
- Add user accounts, learner history, MCP tools, or arbitrary code execution.

The Docker image is host-neutral. Hosting selection and a live link happen after the GitHub push, per the project decision.
