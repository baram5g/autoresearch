# Case study results: harness-driven deck improvement

Compares `baseline` (sparse, single-prompt-style output) vs `upgraded` (harness-driven: persona-bound agents, structural QA loop, mixed content kinds, citations) across two compliance topics. Both runs are hermetic and deterministic — they use scripted FakeLLMClients in `src/autoresearch/seeds.py` to isolate the *pipeline* changes from any LLM variance.

## Rubric

Five axes (see `src/autoresearch/evals.py`):

| Axis | What it measures |
|---|---|
| Objective coverage | Fraction of stated learning objectives that surface in slide titles/notes |
| Content variety | Distinct content kinds used / 7 (cap at 1.0) |
| Citation density | Citations per slide, capped at 1/slide |
| Quiz density | Quizzes / target (1 per 5 slides), capped at 1.0 |
| Scenario presence | 1.0 if the deck has any scenario block, else 0.0 |
| **Total** | weighted sum (0.25 / 0.20 / 0.20 / 0.20 / 0.15) |

## Topic: *Anti-bribery for procurement partners*

Audience: procurement partners

| Axis | Baseline | Upgraded | Δ |
|---|---|---|---|
| Objective coverage | 0.00 | 1.00 | +1.00 |
| Content variety | 0.29 | 1.00 | +0.71 |
| Citation density | 0.00 | 0.91 | +0.91 |
| Quiz density | 0.00 | 1.00 | +1.00 |
| Scenario presence | 0.00 | 1.00 | +1.00 |
| **Total** | **0.06** | **0.98** | **+0.92** |

Artifacts: `examples/anti_bribery_for_procurement_partners__baseline.pptx` (baseline), `examples/anti_bribery_for_procurement_partners__upgraded.pptx` (upgraded).

## Topic: *Data protection (GDPR) for partners*

Audience: EU partners

| Axis | Baseline | Upgraded | Δ |
|---|---|---|---|
| Objective coverage | 0.00 | 1.00 | +1.00 |
| Content variety | 0.29 | 1.00 | +0.71 |
| Citation density | 0.00 | 0.91 | +0.91 |
| Quiz density | 0.00 | 1.00 | +1.00 |
| Scenario presence | 0.00 | 1.00 | +1.00 |
| **Total** | **0.06** | **0.98** | **+0.92** |

Artifacts: `examples/data_protection__gdpr__for_partners__baseline.pptx` (baseline), `examples/data_protection__gdpr__for_partners__upgraded.pptx` (upgraded).

## Attribution

Concrete attributions for the upgraded deltas:

- **Content variety ↑** — researcher → designer split lets the designer pick from `infographic`/`flowchart`/`diagram`/`table`/`image`/`quiz`/`scenario` instead of dumping bullets. The renderer registry change in `pptx/render.py` is what cashes this in visually.
- **Citation density ↑** — researcher emits `[Nk]` ids; designer is prompted to cite by id; QA's structural pass refuses zero-citation decks via a `LOOP:` finding.
- **Quiz / scenario density ↑** — instructional-designer persona's system prompt encodes the 1-quiz-per-5-slides + ≥1-scenario heuristic; QA structural pass enforces it.
- **Objective coverage ↑** — designer emits `learning_objectives` as a first-class field (`DeckPlan.learning_objectives`) and slide notes echo them, so the rubric finds the keyword overlap.
- **No regressions** because the structural QA loop refuses to render decks that don't clear the floor.
