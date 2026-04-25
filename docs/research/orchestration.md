# Orchestration patterns

Six patterns cover almost every multi-agent flow you'll need. This note
catalogues them, says when each fits, and shows how to encode each in
LangGraph specifically — referencing primitives we already use in
`graph/pipeline.py`.

## 1. Linear pipeline

```
A → B → C → D
```

Each node consumes the previous output and produces the next. Our current
pipeline is essentially this with a single back-edge for QA loops.

**When**: Ordered phases with clear hand-offs (research → plan → render).
**When NOT**: Any node legitimately needs to re-run another upstream node
based on what it learned — that's plan-and-execute or supervisor/worker.

```python
g.add_edge(START, "researcher")
g.add_edge("researcher", "designer")
g.add_edge("designer", "render")
g.add_edge("render", END)
```

## 2. Plan-and-execute

```
Planner ─emits steps─▶ Executor (loops over steps) ─▶ Aggregator
```

A planner LLM emits a structured plan; a worker iterates over plan items,
sometimes branching tools per item.

**When**: The number / nature of sub-tasks is data-dependent (e.g., one slide
per learning objective, where the count of objectives is decided at runtime).
**When NOT**: Sub-tasks are fixed — over-engineered.

In LangGraph: planner writes `plan: list[Step]` to state, executor uses a
fan-out via `Send` API or a loop edge over the list.

## 3. Supervisor / worker (orchestrator + workers)

```
            ┌─▶ Worker A
Supervisor ─┼─▶ Worker B   (supervisor decides who runs each turn)
            └─▶ Worker C
```

A supervisor LLM picks the next worker by name; workers are domain experts.

**When**: Heterogeneous workers, dynamic routing, the order isn't fixed.
**When NOT**: A static graph already captures the order — don't pay for an
extra LLM call to re-derive it.

In LangGraph: a node that returns the *name* of the next node, used in
`add_conditional_edges`. AutoGen's `SelectorGroupChat` is a managed version of
this.

## 4. Debate / multi-perspective

```
Agent₁ ─┐
Agent₂ ─┼─▶ Judge ─▶ Output
Agent₃ ─┘
```

N agents independently produce candidates; a judge synthesises or picks.

**When**: Diversity of reasoning improves quality (e.g., generating distinct
quiz questions, or stress-testing a scenario from multiple compliance angles).
**When NOT**: There's a clear right answer — debate adds cost without lift.

In LangGraph: parallel fan-out via `Send` with the same downstream judge
node.

## 5. Reflexion / evaluator-optimiser

```
Generator → Evaluator ─if bad─▶ Generator (with feedback) ─▶ ...
                       └if ok─▶ Output
```

A second LLM critiques the first; the first revises. **This is what our
QA→designer loop is.**

**When**: Output quality benefits from a different *role* (not the same
prompt) judging it. Pedagogical review, fact-checking, regulatory alignment.
**When NOT**: The critic is identical to the generator — you're just paying
for two passes; collapse to one with a "self-check" rubric.

In LangGraph: conditional edge from evaluator back to generator; **always cap
the loop** (we use `MAX_REVIEW_LOOPS = 2`). Loop signal contract matters —
we use `LOOP:` prefix on `review_findings` so non-actionable findings don't
trigger re-entry.

## 6. Map-reduce

```
Splitter ─▶ Worker (×N in parallel) ─▶ Reducer
```

Split a large task into independent sub-tasks, run in parallel, combine.

**When**: Per-slide enrichment, per-citation verification, per-objective quiz
generation. Embarrassingly parallel work.
**When NOT**: Sub-tasks share state or have ordering constraints.

In LangGraph: `Send` API to fan out, a list-reducer state slot to gather,
single reducer node to finalise.

## Composition notes

These patterns compose. Our likely end-state for the deck pipeline:

```
researcher (linear)
  └▶ designer (plan-and-execute over slides; map-reduce per slide)
        └▶ visual designer (per-slide map; pure layout)
              └▶ qa (reflexion loop; cap = 2)
                    └▶ render (linear)
```

Two patterns layered (plan-and-execute *inside* designer; reflexion *around*
designer) is normal. Three or more starts to be a smell — reach for a
supervisor instead of nesting deeper.

## Anti-patterns

- **Loop without a cap.** Every re-entry must be bounded. Bugs that ship are
  almost always unbounded reflexion loops.
- **Supervisor that always picks the same order.** If the supervisor's
  decisions are deterministic, replace it with a static edge.
- **Debate as a default.** Parallel agents are 3× cost; only pay for it where
  diversity is shown to lift the eval metric.
- **Hidden state mutation across patterns.** Each pattern relies on state-slot
  ownership; if a worker writes to the supervisor's slot you lose the
  reasoning that justified the topology.

## Encoding cheatsheet (LangGraph)

| Pattern              | Primitives                                         |
|----------------------|----------------------------------------------------|
| Linear pipeline      | `add_edge`                                         |
| Plan-and-execute     | `Send` over a `list[Step]` + reducer state slot    |
| Supervisor/worker    | Node returning next-node name + `add_conditional_edges` |
| Debate               | `Send` fan-out; judge node                         |
| Reflexion            | `add_conditional_edges` back-edge + loop counter   |
| Map-reduce           | `Send` fan-out + list-reducer slot + reducer node  |
