# autoresearch

Research on **AI agent harnesses** (multi-agent orchestration frameworks: LangGraph, CrewAI, AutoGen, etc.) **plus a working LangGraph POC** that generates a partner-compliance-training PowerPoint deck driven by a multi-agent pipeline (personas → research → content → design → assembly).

## Layout

```
docs/
  research/        # Notes on harness frameworks (what / how to use / how to build)
  case_study/      # Compliance-training PPT case study notes (trends, content types, design)
src/autoresearch/
  agents/          # Persona-bound agents (researcher, instructional designer, designer, QA, …)
  tools/           # Tool wrappers used by agents (search, image, layout helpers)
  graph/           # LangGraph state machine wiring agents into an orchestrated pipeline
  pptx/            # python-pptx renderers (layouts, infographics, quiz/scenario blocks)
  cli.py           # `autoresearch` Typer CLI entrypoint
tests/             # pytest suite (mirrors src/autoresearch package layout)
examples/          # Runnable example configs and generated decks
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export OPENAI_API_KEY=...           # or other provider, see docs/research
autoresearch generate --topic "Anti-bribery for procurement partners" --out out.pptx
```

## Develop

```bash
pytest                              # run all tests
pytest tests/pptx/test_layouts.py::test_quiz_slide   # single test
ruff check . && ruff format --check .
mypy
```

## Scope

1. Survey: what an agent harness is, how to use one, how to build one.
2. Compare LangGraph / CrewAI / AutoGen on orchestration, personas, tool use, state.
3. Case study: generate compliance-training decks (quizzes, scenario case studies w/ images, infographics, flowcharts, tables) from a topic + audience profile.
