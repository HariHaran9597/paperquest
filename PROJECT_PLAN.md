# PaperQuest — Project Plan

**Product promise:** Turn one AI research paper into one small experiment a developer can run, change, and understand.

**Audience:** ML/GenAI developers and students who read about new methods but struggle to translate dense papers into something they can try.

**Project goal:** Ship one reliable, public, end-to-end experience that demonstrates research grounding, a real ML concept, a bounded AI workflow, evaluation, and deployment. Users are not required for the project to count as shipped.

**Truth about the current preview:** `../paperquest` is a visual prototype with a deterministic toy attention calculation. It has no LLM, no paper-ingestion pipeline, and no trained-model reproduction. Keep it as the design reference; this folder is the clean implementation home.

**Release-scope decision:** v0.1.0 is intentionally one curated, prebuilt quest plus a deterministic FastAPI experiment. The originally proposed LangGraph authoring workflow is deferred to a later release: it is an authoring convenience, not necessary for a learner to solve the first problem, and it would add model/API setup before the core experience is proven. This project demonstrates ML through the attention calculation; it does not need an LLM wrapper to be an AI/ML project.

## Minimum shippable release: v0.1.0

This is the non-negotiable portfolio bar. Once every item below passes, v0.1.0 is shipped and can be linked on a resume.

- A stable public URL opens without login, API key, or GPU.
- A visitor can open one curated paper quest, inspect its source evidence, change an input, run the experiment, and see an explained result.
- The first quest is based on *Attention Is All You Need* and demonstrates scaled dot-product attention. It uses fixed, documented toy inputs; it does not claim to reproduce the paper's trained model or benchmark results.
- A small FastAPI backend validates experiment inputs and returns the calculated result. Invalid inputs produce clear errors.
- The public quest is prebuilt and versioned, so normal visitors do not trigger model calls.
- Tests, a small evaluation set, setup/deployment instructions, architecture notes, known limitations, and a short demo capture are in the public repository.
- The deployed service has health checks, request limits, logs without secrets, and a recovery path documented in the README.

**A release is not blocked by user count, accounts, paper uploads, arbitrary code execution, a multi-paper catalog, or an MCP server.** Those belong to later releases. No portfolio project can guarantee an interview; this release guarantees a concrete, reviewable proof of work when its acceptance checks pass.

## Product loop

`paper source → evidence-backed claim → small quest → run experiment → compare result → learn`

Every published quest is a versioned artifact with a source paper, exact cited passages, a learning objective, fixed inputs, a runnable method, expected outputs, tests, and limitations.

## Releases

### R0 — Design prototype (already built)

- Existing interactive attention concept and visual direction in `../paperquest`.
- Useful for feedback and product feel only; it is not the portfolio release.

### R1 — v0.1.0, public portfolio release (required)

1. Turn the attention visualization into a precise, documented scaled-dot-product experiment: explicit Q/K/V inputs, scores, softmax weights, and output.
2. Add a working API and a fixed, testable `QuestSpec` for the first paper.
3. Add paper passages and citation links beside the claim and explanation.
4. Add paper-section citations next to the claims they support. Keep the quest authored and reviewed by a human for v0.1.0.
5. Add deterministic repeatability, API/frontend tests, and an evaluation report.
6. Deploy the public demo; verify it on desktop and mobile; publish README, architecture diagram, limitations, and a short walkthrough.

### R2 — v0.2.0, bring a paper

- Accept arXiv IDs/links from an allowlist; fetch paper metadata and supported text/PDF through official endpoints.
- Parse and index the paper, retrieve relevant passages, and create an unpublished quest draft.
- Let the author edit, reject, or approve a draft. Approved quest code must come from supported templates and pass the fixed runner and tests.
- Cache generated drafts by paper ID and prompt/workflow version; rate-limit generation.
- Add 2–3 new quests only after each has source evidence, tests, a baseline, and a clearly scoped learning objective.

### R3 — v0.3.0, PaperQuest from your tools

- Add a small MCP server exposing bounded tools such as `search_papers`, `get_quest`, and `run_supported_experiment`.
- Add a learner progress/history view only if user feedback shows it helps.
- Consider stronger sandboxed code submission only after a security design and isolated runner are proven. Never execute arbitrary generated or uploaded code directly on the web process.

## Technical shape

- **Frontend:** keep the current lightweight browser UI while proving the interaction; organize it into reusable components as the quest catalog grows.
- **API:** Python + FastAPI + Pydantic request/response models.
- **AI workflow:** LangGraph with explicit, typed stages and a human approval interrupt. Use a hosted model behind a provider interface; keep provider secrets server-side.
- **Grounding:** retrieve only from the selected paper's stored passages. Start with a simple retriever for the first paper; add embeddings/vector storage only when retrieval quality tests show it is needed.
- **Experiment:** deterministic Python implementation of the attention equation with fixed seeds/inputs and a baseline. The current synthetic demo remains clearly labeled as illustrative.
- **Storage:** SQLite for the first release's papers, quest versions, and run metadata. Move to a managed database only when actual needs justify it.
- **Execution safety:** v0.1 runs only server-owned, fixed experiment code with validated inputs. Do not accept arbitrary Python from visitors in this release. If code execution is added later, isolate it and cap CPU/memory; see [Docker resource constraints](https://docs.docker.com/engine/containers/resource_constraints).
- **Paper sources:** start with arXiv IDs and metadata; OpenAlex is a possible discovery/metadata source. [arXiv API manual](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/api/user-manual.md) · [OpenAlex API](https://help.openalex.org/api/).
- **Workflow references:** [FastAPI request models](https://fastapi.tiangolo.com/tutorial/body/) · [LangGraph persistence](https://langchain-ai.github.io/langgraph/concepts/durable_execution/) · [LangGraph approval interrupts](https://langchain-ai.github.io/langgraph/concepts/breakpoints/).

## R1 goals and release checks

### Product goals

- A first-time visitor can run the quest in under five minutes without setup.
- The user can see the exact paper passage behind every claim shown as sourced.
- A user action changes experiment inputs and the computed result, not just decorative UI state.
- The page explains what is modeled and what is not reproduced.

### Engineering and evaluation goals

- 100% of published quest citations resolve to stored source passages.
- 100% of published challenge tests pass on the release build.
- Identical versioned inputs produce identical experiment outputs.
- A 20-item golden set checks that claim/evidence pairs are supported; report raw results and inspect every miss. Do not use an LLM judge as the only verifier.
- Measure and report API latency and model-call cost for quest drafting; do not call it free if a hosted model is used.
- Automated checks cover schema validation, invalid inputs, API behavior, workflow gates, and the browser's main quest path.

These are targets to verify, not claims to put in the resume before the tests produce evidence.

## Build checklist

### Product and content

- [ ] Freeze the first audience and learning objective: understand scaled dot-product attention by changing Q/K/V and observing scores, weights, and output.
- [ ] Select the exact paper sections/passages; record section and page/anchor references.
- [ ] Write the first `QuestSpec`: paper metadata, claim, evidence spans, instructions, fixed inputs, baseline, expected output, tests, limitations, version.
- [ ] Review the wording so the interface never implies that the toy vectors reproduce trained Transformer results.

### Implementation

- [ ] Create frontend/API project structure, config, local run commands, and health endpoint.
- [ ] Implement pure attention calculation and baseline as testable functions.
- [ ] Define validated API schemas and clear error responses.
- [ ] Connect the UI controls to the API; show intermediate scores/weights and final output.
- [ ] Store the curated paper and quest data; keep public demo usable with model generation disabled.
- [ ] Keep the first quest prebuilt and versioned; verify its paper references and all fixed challenge outputs.
- [ ] Add caching, request/time limits, secret handling, structured logs, and friendly error states.
- [ ] Add mobile/accessibility pass, run tests, deploy, and verify through the real public URL.

### Portfolio and release

- [ ] README starts with the user problem and a live demo link.
- [ ] Add architecture/data-flow diagram, local setup, tests/evaluation results, limitations, and deployment notes.
- [ ] Record a 60–90 second walkthrough showing the end-to-end quest.
- [ ] Tag `v0.1.0` only after all R1 release checks pass.
- [ ] Add the project to the resume only after the public URL and repository are verified.

## Open decisions and defaults

These are the only choices worth asking the user before implementation; defaults let work continue without a long planning loop.

1. **Audience:** default = ML/GenAI developers who want to understand papers by trying methods.
2. **First exercise:** default = implement/inspect scaled dot-product attention in Python; UI runs a fixed safe implementation and exposes its inputs/results.
3. **Paper scope:** default = one paper, *Attention Is All You Need*, for v0.1.0.
4. **Model provider:** no model provider is required for v0.1.0; visitor experience must work without a key.
5. **MCP timing:** default = R3, after the public quest and evaluation are solid.

Unless the user changes one of these, proceed with the defaults and finish R1 before expanding scope.

## Scope guard

Do not add authentication, subscriptions, social feeds, arbitrary paper URLs, automatic publication, autonomous code execution, fine-tuning, multiple papers, or multiple agents for appearance in v0.1. Add a feature only when it strengthens the core loop or is needed to pass a release check.
