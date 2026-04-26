# auto_loop.md — Autonomous research loop for the PPT harness

This file is the analogue of karpathy/autoresearch's `program.md`. It is the
"skill" you point an autonomous coding agent at to drive overnight experiments
on the PPT pipeline. The loop, the editable surface, and the metric are
deliberately small and reviewable.

## Setup

1. Pick a run tag based on today's date (e.g. `apr26`). The branch
   `autoresearch/<tag>` must not already exist.
2. `git checkout -b autoresearch/<tag>` from `main`.
3. Read these files for context (do **not** modify them):
   - `README.md`
   - `src/autoresearch/graph/builder.py` and `pipeline.py` — the harness.
   - `src/autoresearch/evals.py` and `judge.py` — read-only metrics.
   - `scripts/autoresearch_iter.py` — fixed-budget runner you will call.
4. Confirm `pytest -q` and `ruff check .` are green before starting.
5. `python scripts/autoresearch_iter.py --desc "baseline"` to record the
   starting frontier in `results.tsv`. Mark its row `keep`.

## What you CAN edit (the policy surface)

- `src/autoresearch/agents/personas.yaml` — system prompts and tool allowlists
  for Researcher / Designer / Visual Designer / QA.
- `src/autoresearch/seeds.py` — the seeded `upgraded_client` script that
  drives demo-mode runs. Treat its content as a stand-in for what a real LLM
  would produce; tightening it teaches the prompt what good looks like.
- `src/autoresearch/agents/designer.py` `build_user_prompt` only — you may
  adjust the user-prompt template, **not** the schema or merge logic.

## What you CANNOT edit

- `evals.py`, `judge.py` — the ground-truth metrics. Editing these is
  cheating, like editing `evaluate_bpb` in karpathy/autoresearch.
- `state.py`, `graph/pipeline.py`, `pptx/render.py` — the harness shape.
- `scripts/autoresearch_iter.py` — the runner.
- The 5 deterministic gate rules in `agents/qa.py::structural_findings`.
- Adding new dependencies to `pyproject.toml`.

## The metric

`mean_judge` from `scripts/autoresearch_iter.py` (range 0.0–1.0, higher is
better). Tie-break with `mean_evals`. Both are computed across the pinned
eval set in `EVAL_TOPICS` so single-topic over-fitting is visible.

The judge weights five axes that all have headroom past the QA gate:

- narrative_flow
- block_distribution_entropy
- citation_per_factual_block
- objective_alignment_per_slide
- audience_specificity

## The loop

```
LOOP FOREVER:
  1. Note current branch HEAD.
  2. Edit the policy surface with one experimental idea (small diff).
  3. git commit -m "<short description>".
  4. python scripts/autoresearch_iter.py --desc "<short description>"
  5. Read the new mean_judge from results.tsv (last row).
  6. If mean_judge improved over the running best:
        - Update the row's status to `keep`. Advance the branch.
     Else if it crashed or regressed:
        - Update the row's status to `discard` or `crash`.
        - git reset --hard to the previous commit.
  7. Run `pytest -q && ruff check .` periodically; if either fails, fix or
     revert. Tests are part of the contract — we don't ship a regressed
     harness even for a higher judge score.
```

Do not commit `results.tsv` — keep it untracked, like the upstream design.

## Stopping criterion

You don't have one. The human stops you. If you run out of ideas, re-read
`docs/research/personas.md` and `docs/research/orchestration.md` for new
angles, try combining near-misses, or attack the weakest judge axis from the
last `python scripts/autoresearch_analyze.py` run.

## Simplicity rule

A 0.005 mean_judge gain that adds 50 lines of prompt scaffolding is not
worth it. A 0.000 change that **simplifies** a persona prompt and keeps the
judge flat is a great outcome. Weigh complexity against gain explicitly.
