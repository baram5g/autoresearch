# Using a harness in practice

Operational guidance for the dev → CI → production loop. Opinionated; tuned
to this repo's choices (LangGraph + python-pptx + Typer CLI), but the
underlying advice generalises.

## Dev loop

1. **Run the CLI on a tiny topic** during iteration:
   ```bash
   autoresearch generate --topic "smoke" --out /tmp/x.pptx
   ```
   This exercises the full graph cheaply.
2. **Iterate on prompts in YAML**, not in Python. Fast inner loop because
   you're not changing topology.
3. **When the failure is structural** (wrong slot written, wrong order, wrong
   loop count), fix it in `graph/pipeline.py` — *not* in a prompt.
4. **Snapshot good runs** as eval fixtures the moment you see them, before a
   regression eats them.

## Tests

Three tiers, in increasing cost:

| Tier              | What it checks                                    | Speed | Network? |
|-------------------|---------------------------------------------------|-------|----------|
| **Unit**          | Individual renderers, persona loader, schemas      | <1s   | No       |
| **Graph**         | Topology with `fake_agent` stubs                  | <1s   | No       |
| **Eval (offline)**| Recorded LLM responses → score deck on rubric     | sec   | No       |
| **Eval (live)**   | Real LLM, on a held-out topic, scored on rubric   | min   | Yes      |

Hard rule (already in copilot-instructions.md): **no live network in `tests/`**.
Live evals run via a separate `evals/` script, gated on a flag. Recordings go
under `tests/evals/fixtures/`.

## Observability

Three signals worth wiring early:

- **Per-node latency + token counts** → catch the "designer slowed 4×" regression
  without waiting for users to complain.
- **Loop counts per run** → if the QA loop is hitting its cap on >X% of runs,
  the designer prompt is the actual bug.
- **Tool error rates** → fetch failures often masquerade as content quality
  issues until you separate them.

LangSmith gives you all three for free if you set `LANGSMITH_API_KEY`. OTel
via `langchain.callbacks` is the framework-agnostic alternative.

## Cost & latency

- **Most expensive thing** in our pipeline is the designer (large structured
  output). Caching its output keyed on `(topic, audience, research_notes)` is
  worth it as soon as the loop fires twice.
- **Researcher** scales with citation density, not topic complexity. Cap
  citations per note; don't cap notes.
- **QA** is cheap *if* the prompt only re-reads `deck_plan` and the latest
  research notes. Don't replay the full transcript.
- **Image generation** dominates the visual designer's cost. Generate prompts
  in this run; defer rendering to a later batch step if cost is an issue.

## Failure modes (and what to do)

| Symptom                                       | Likely cause                              | Fix                                                                 |
|-----------------------------------------------|-------------------------------------------|---------------------------------------------------------------------|
| Designer ignores some research notes          | Prompt doesn't reference notes by id      | Number notes in YAML output, require designer to cite by id         |
| QA loops always hit the cap                   | Designer can't actually fix the finding   | Either tighten the `LOOP:` contract (only emit when actionable), or raise the cap and instrument why |
| Renderers crash on unknown `kind`             | New kind added in state, not in renderer  | Three-edit rule (kind in `state.py`, renderer in `RENDERERS`, test) |
| Citations don't resolve at QA time            | Researcher fabricated URLs                | Move citations through fetch MCP at retrieval time, not just at QA  |
| Decks pass tests but feel dry                 | Eval doesn't penalise low content variety | Add content-type-variety to the rubric                              |
| State slot mysteriously empty                 | Two nodes wrote to a non-list slot        | Move the slot to a list with a reducer, or fix ownership            |

## Production hygiene

- **Pin model versions** in config, not in code. Swap with one env var.
- **Never put secrets in `personas.yaml`**. The file is reviewed; secrets are not.
- **Cap `MAX_REVIEW_LOOPS` and `max_tokens` per node**. Both are cost
  liability without them.
- **Record every run's input + final state** as a JSON artifact. This is your
  only post-hoc debugging tool.
- **Write a deck only after QA returns no `LOOP:` findings**, even if the
  cap fires — that signal becomes the `output_quality_warning` flag in the
  artifact.

## The single most useful guideline

Whenever you're tempted to "just add a prompt instruction" to fix a behavioural
bug, ask: *would a typed schema, a tool allowlist change, or a graph edge fix
this more reliably?* Ninety percent of the time, yes. Reserve prompt edits for
the actual content of the prompt, not the control flow.
