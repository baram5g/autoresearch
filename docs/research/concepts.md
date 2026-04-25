# Concepts: what is an AI agent harness?

## TL;DR

An **agent harness** is the runtime that wraps one or more LLM-based agents and
turns them from a free-running chat loop into a *controllable, observable,
testable* system. The agent is the policy; the harness is everything around it
that decides *when it runs, what it can see, what it can do, how its output is
validated, and how the whole thing recovers when something goes wrong*.

A single `while not done: response = llm.invoke(history)` loop is **not** a
harness. It becomes one when you start having explicit answers to: *Whose turn
is it next? What tools is it allowed to call right now? What state changes are
allowed? What happens on failure?*

## Anatomy

A useful harness has six concerns. Frameworks differ on which they centralise
vs. leave to user code, but the concerns themselves are universal.

| Concern        | What it owns                                                                         | In our POC                                  |
|----------------|--------------------------------------------------------------------------------------|---------------------------------------------|
| **State**      | Typed shared blackboard; ownership rules; reducers for concurrent writes             | `state.GraphState` (TypedDict + reducers)   |
| **Scheduler**  | Which node runs next; conditional branching; loops with caps                         | `graph/pipeline.py` (StateGraph + edges)    |
| **Tool gateway** | Allowlist per agent; arg validation; uniform error contract                        | `agents/personas.yaml: allowed_tools` + `tools/` |
| **Memory**     | Short-term (in-state) vs long-term (vector / KV); summarisation policy               | In-state only (deliberately, for the POC)   |
| **Validation** | Structured-output schemas; retries on schema failure; refusals                       | Pydantic models in `state.py`               |
| **Observability** | Traces, eval hooks, replay fixtures                                               | OTel/LangSmith hook (planned)               |

## Harness vs single-agent loop

| Property                 | Single-loop chat agent | Harness                                    |
|--------------------------|------------------------|--------------------------------------------|
| Control flow             | Implicit in prompt     | Explicit in graph / DAG / scheduler        |
| Tool authorisation       | All-or-nothing         | Per-agent / per-step allowlist             |
| State sharing            | One linear transcript  | Typed slots with ownership + reducers      |
| Failure recovery         | Re-prompt              | Conditional edges, retries, loop caps      |
| Testability              | Snapshot prompts       | Replace nodes with fakes; replay traces    |
| Multi-agent              | "Roleplay in prompt"   | First-class persona-bound nodes            |

## Why the distinction matters for compliance training

A compliance-deck pipeline is a textbook harness use case:

1. Outputs are **structured** (a slide plan with typed content blocks), not free
   text — schema validation matters.
2. Different sub-tasks need **different tools** (web search for the researcher;
   image generation for the visual designer; nothing for the instructional
   designer) — per-agent allowlists matter.
3. Some sub-tasks need to **loop** (QA → designer) but bounded — scheduler
   matters.
4. Regulators care about **traceability** of claims — observability matters.

A single chat loop with "act as X, then Y, then Z" in the system prompt fails
all four properties under any non-trivial topic.

## Vocabulary used in the rest of this repo

- **Node** — a callable `(GraphState) -> dict` registered in the StateGraph.
- **Persona** — declarative role spec (system prompt + tool allowlist + output
  schema), see `personas.md`.
- **Agent** — a node bound to a persona. Owns exactly one state slot (see
  `architecture.md`).
- **State slot** — a key in `GraphState`. List slots use the `_merge_lists`
  reducer; scalar slots are last-write-wins.
- **Loop signal** — a string in `review_findings` prefixed `LOOP:`. Anything
  else is informational and does *not* cause re-entry.

## Further reading (cited in `frameworks.md` and `building_a_harness.md`)

- LangGraph docs — graph-based agent orchestration (StateGraph, reducers,
  conditional edges).
- AutoGen Studio paper / docs — conversational multi-agent.
- CrewAI docs — role-first multi-agent abstraction.
- Anthropic, "Building effective agents" — patterns: chains, routing,
  parallelisation, orchestrator-workers, evaluator-optimiser.
- OpenAI, function calling + structured outputs — schema-validated tool use.
