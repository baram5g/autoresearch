# Translator multi-agent example (EN → KO)

A self-contained, runnable example of a **multi-agent + multi-LLM**
translation pipeline, following the same persona-as-Markdown pattern
as the autoresearch harness.

```
[en text] → Translator → draft_ko
                              │
                              ▼
                        Reflector  ─→ findings (JSON)
                              │
                              ▼
                          Editor   ─→ final_ko
```

Three agents, three persona files, three (potentially distinct) LLMs.

| Agent      | Default model           | Why                                |
| ---------- | ----------------------- | ---------------------------------- |
| Translator | `gpt-4.1-mini`          | Cheap, fast first draft            |
| Reflector  | `claude-sonnet-4.5`     | Different model family ⇒ catches the translator's blind spots |
| Editor     | `gpt-4.1-mini`          | Same family as translator is fine — its job is targeted edits |

Models are declared in each persona's YAML frontmatter (`model:`); swap
them by editing the persona file — no Python changes.

## Quick start (hermetic, no API keys needed)

```bash
cd examples/translator_agent
python demo.py
```

## Run the tests

```bash
cd examples/translator_agent
pytest -q
```

All 7 tests run on `FakeLLM` — no network, no keys.

## Run for real

```bash
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
cd examples/translator_agent
pip install openai anthropic        # optional; only needed for real calls
python -m translator "Time flies like an arrow."
python -m translator "It's raining cats and dogs." --trace
python -m translator "Hello." --no-reflection   # baseline single-shot
```

## Layout

```
translator/
├── personas/
│   ├── translator.md     # frontmatter: role, model, allowed_tools
│   ├── reflector.md
│   └── editor.md
├── personas_loader.py    # md frontmatter parser
├── llm.py                # OpenAI / Anthropic / FakeLLM behind a Protocol
├── agents.py             # 3 agent classes + Finding parser
├── pipeline.py           # translate(en) → Trace
└── cli.py                # `python -m translator ...`
demo.py                   # runnable hermetic demo
tests/test_pipeline.py    # 7 tests, FakeLLM only
```

## Design choices worth flagging

- **Reflection is gated by severity.** Findings tagged `low` are
  ignored; only `high` and `med` trigger the Editor. This prevents the
  3-call pattern from ballooning to a 5–6-call argument loop on
  stylistic preferences.
- **Editor is skipped entirely when there are no actionable findings.**
  The Trace records `edited=False` so callers can audit the rate of
  draft-acceptance over a corpus.
- **`Trace` exposes every intermediate step.** Use `--trace` from the
  CLI or read `Trace.draft_ko` / `Trace.findings` programmatically to
  build a quality dashboard later.
- **Persona format matches the parent autoresearch repo** — Markdown
  body becomes the system prompt; YAML frontmatter carries `role` and
  `model`. The `model` key drives provider routing in `llm.py`.

## Extending it

| Want                    | Add                                                                                 |
| ----------------------- | ----------------------------------------------------------------------------------- |
| Korean glossary         | A `glossary.yaml` injected into the translator's user prompt                        |
| Long-document support   | Chunk by paragraph; run pipeline per chunk; re-stitch                              |
| LLM-as-judge eval       | A 4th persona that scores `(source, final_ko)` 1–5 and logs to `runs/<ts>.jsonl`    |
| LangGraph orchestration | Replace `pipeline.translate()` with a graph; same agents plug in unchanged          |
