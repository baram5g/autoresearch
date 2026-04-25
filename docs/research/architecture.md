# Architecture

The pipeline is a LangGraph `StateGraph[GraphState]`:

```
START → researcher → designer → visual → qa ─▶ render → END
                       ▲                 │
                       └───── loop (≤2) ─┘   when review_findings start with "LOOP:"
```

Conventions:

- **State ownership.** Each node returns ONLY the keys it owns. Lists use the
  `_merge_lists` reducer (append-only). Never mutate another node's slot.
- **Loop signalling.** QA appends strings prefixed with `LOOP:` to
  `review_findings` to request another designer pass. Other findings are
  informational and do not trigger a loop.
- **Loop cap.** `MAX_REVIEW_LOOPS = 2` in `graph/pipeline.py`. Bump deliberately.
- **Agents are persona-bound.** Topology lives in `graph/`; prompts in
  `agents/personas.yaml`. Don't put orchestration logic in agents.
