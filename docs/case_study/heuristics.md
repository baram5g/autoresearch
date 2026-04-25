# Pedagogical heuristics encoded in the pipeline

The instructional-designer persona is prompted with — and the QA reviewer's
structural pass enforces — a small set of heuristics. They're chosen because
they (a) are testable on a static `DeckPlan` and (b) correlate with research
on workplace compliance training effectiveness.

| Heuristic                                       | Where it lives                                             | Rationale                                                                 |
|-------------------------------------------------|------------------------------------------------------------|---------------------------------------------------------------------------|
| 8–12 slides per module                          | designer prompt; QA: `slides < 8 ⇒ LOOP:`                  | Long enough to develop a topic; short enough for one sitting (microlearning). |
| Slide 2 lists explicit learning objectives      | designer prompt; QA: `learning_objectives empty ⇒ LOOP:`    | Adult-learning research: stating objectives up front improves retention.  |
| ≥ 1 quiz per 5 slides                           | designer prompt; QA: `quiz_count < n//5 ⇒ LOOP:`           | Spaced retrieval practice; quizzes are the most reliable retention lever. |
| ≥ 1 scenario per module                         | designer prompt; QA: `no scenario ⇒ LOOP:`                 | Scenario-based learning transfers better to real decisions than rules.    |
| Mix of content kinds (≥ 5 of 9)                 | designer prompt (soft); rubric scores `content_variety`     | Varied modalities reduce monotony, accommodate different learners.        |
| Every factual claim has a citation              | designer prompt; QA: `0 citations ⇒ LOOP:`                  | Compliance content is auditable; uncited claims are unauditable.          |
| Visual designer adds image prompts only         | persona system prompt                                       | Separation of pedagogy from visuals; either can iterate without breaking the other. |
| QA loop only fires on `LOOP:`-prefixed findings | router in `graph/pipeline.py`                               | Loops on every nit are runaway-cost bugs; the prefix makes the contract explicit. |
| Loop cap (`MAX_REVIEW_LOOPS = 2`)               | `graph/pipeline.py`                                         | Bounded reflexion; raise only with eval evidence.                         |

## What we deliberately don't enforce

- **Slide-level word counts** — varies legitimately by content kind.
- **Specific colour palette** — the renderer picks one; templating can override.
- **Single learning style** — explicitly *avoid* picking VARK/etc. styles, which
  meta-analyses don't support.
- **Tone / register** — that's the persona's job, not a rule.

## How to evolve a heuristic

1. Propose it here with a one-sentence rationale.
2. Add it to the designer's system prompt in `personas.yaml`.
3. If it's testable on a static `DeckPlan`, add a check to
   `agents/qa.structural_findings` that emits a `LOOP:` finding when violated.
4. Add a metric to `evals.score_deck` so case-study results pick it up.
5. Re-run `scripts/run_case_study.py` and commit `docs/case_study/results.md`.
