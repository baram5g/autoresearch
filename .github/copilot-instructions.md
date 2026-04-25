# Copilot instructions for `autoresearch`

This repo is **research on AI agent harnesses + a working LangGraph POC** that generates a partner-compliance-training PowerPoint via a multi-agent pipeline. Research notes live in `docs/research/`; case study + heuristics in `docs/case_study/`; runnable code lives in `src/autoresearch/`.

## Build, test, lint

Editable install with dev extras (Python ≥ 3.11; we tested with 3.13):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Common commands:

```bash
pytest                                                       # full suite
pytest tests/graph/test_pipeline.py                          # one file
pytest tests/pptx/test_renderers.py::test_flowchart_renderer # one test
ruff check . && ruff format --check .
mypy
autoresearch generate --topic "Anti-bribery" --out out.pptx        # demo run (seeded fake LLM)
autoresearch generate --topic "GDPR" --mode baseline --out b.pptx  # sparse baseline run
autoresearch score --topic "Anti-bribery"                          # print rubric scores
python scripts/run_case_study.py                                   # regen examples/*.pptx + docs/case_study/results.md
AUTORESEARCH_TRACE=1 autoresearch generate --topic "x"             # per-node timing to stderr
```

`pyproject.toml` sets `pythonpath = ["src"]`, so tests import `autoresearch` directly — no `sys.path` hacks.

## Architecture (the parts you can't see from one file)

The pipeline is a single LangGraph `StateGraph[GraphState]` (see `src/autoresearch/state.py`):

```
START → researcher → designer → visual → qa ─▶ render → END
                       ▲                 │
                       └────── loop ─────┘   when QA emits "LOOP:" findings AND qa_passes ≤ MAX_REVIEW_LOOPS (=2)
```

- **`state.py`** is the contract between every node. `GraphState` is a `TypedDict`; the only list slot with a reducer is `research_notes` (append-only via `_merge_lists`). `review_findings` is **replace-each-pass** (a fresh list per QA run); `qa_passes` is a last-write-wins counter incremented by QA. **Each node returns ONLY the keys it owns.** Mutating another node's slot is a bug.
- **`graph/pipeline.py`** is the *only* place topology lives — node order, conditional edges, and the `MAX_REVIEW_LOOPS = 2` cap. Routing reads `qa_passes` and the latest `review_findings`. Don't put routing logic inside agents.
- **`graph/builder.py`** wires persona-bound `LLMAgent`s + the renderer + tracing into `build_graph`. This is the entry point used by the CLI and the case-study runner.
- **`agents/`** holds persona-bound nodes. Personas are *declarative* (`agents/personas.yaml`: role, system_prompt, allowed_tools); the Python `LLMAgent` base loads a persona by `persona_name` and calls a provider-agnostic `LLMClient.call_structured(...)`. Edit prompts/tool policy in YAML, not in `.py`.
- **`llm.py`** defines the `LLMClient` Protocol and `FakeLLMClient` (scripts Pydantic responses per persona; raises if a script entry is missing rather than silently returning stale data). Real-LLM bindings would implement the same Protocol.
- **`tools/protocols.py`** defines `WebSearch`, `FetchURL`, `ImagePromptStore` Protocols + in-process fakes. Agents inject these — never import a concrete client directly.
- **`pptx/render.py`** maps each `ContentBlock.kind` to a renderer via the `RENDERERS` dict. Adding a content type requires three coordinated edits: extend `ContentBlockKind` in `state.py`, register a renderer in `RENDERERS`, add a test under `tests/pptx/`. Unknown kinds fall back to a bullet dump — keep that fallback.
- **`agents/qa.py`** combines a deterministic `structural_findings` pass (no LLM call needed; encodes the heuristics in `docs/case_study/heuristics.md`) with an LLM-driven content audit. If the structural pass already emits `LOOP:` findings, the LLM call is **skipped** — the designer hasn't earned an audit yet.
- **`evals.py`** is a pure-function rubric (`score_deck → DeckScore`) over five axes. No LLM, no network — usable as a CI gate.
- **`seeds.py`** provides scripted FakeLLMClients (`baseline_client`, `upgraded_client`) for demos and the case study, so end-to-end runs are hermetic and deterministic.
- **`tracing.py`** wraps nodes with timing-to-stderr when `AUTORESEARCH_TRACE` is set. Drop-in replaceable with OTel `tracer.start_as_current_span` later.

## Conventions specific to this codebase

- **QA loop signalling.** A QA pass triggers another designer pass *only* by emitting strings prefixed `"LOOP:"` in `review_findings`. Plain findings are informational and never loop. The router also requires `qa_passes ≤ MAX_REVIEW_LOOPS`; the `≤` (not `<`) is intentional given increment-after-pass semantics.
- **State-slot ownership** (see `docs/research/personas.md`): researcher → `research_notes`; instructional_designer → `deck_plan` + `learning_objectives`; visual_designer → image-block `prompt` fields *inside* `deck_plan.slides[*].blocks` only (no pedagogy mutation); qa_reviewer → `review_findings` + `qa_passes`.
- **Persona = YAML, not Python.** Edit `agents/personas.yaml` for prompts/tool allowlists; the `Agent` subclass should only declare `persona_name`, `output_schema`, `build_user_prompt`, `merge`.
- **No network in tests.** `tests/conftest.py` provides `fake_agent`; `llm.FakeLLMClient` and `tools.protocols.Fake*` cover LLM and tool side-effects. Never call real LLMs or HTTP from `tests/`.
- **Structured output, not strings.** Every LLM call goes through `LLMClient.call_structured(schema=...)` and returns a Pydantic model. Schema validation failures are bugs in the prompt or the schema, not the harness.
- **Persona vs agent vs graph** is the central separation of concerns. Prompt text in `graph/`, or `if`/loop logic in `agents/`, or routing in `cli.py` — all wrong file.

## Where things go

- `docs/research/` — harness theory: `concepts`, `frameworks`, `personas`, `orchestration`, `building_a_harness`, `using_a_harness`.
- `docs/case_study/` — `heuristics.md` (rules baked into the pipeline) and `results.md` (regenerated by `scripts/run_case_study.py`).
- `examples/` — generated `.pptx` artifacts from the case study (gitignored; rerun the script to regenerate).
- `scripts/run_case_study.py` — hermetic baseline-vs-upgraded runner; updates `results.md` + `examples/*.pptx`.
