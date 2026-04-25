# Building a harness from scratch

This note is a recipe for the *minimum viable harness* you'd need to replace
LangGraph for our use case, plus a mapping showing what we already have in
`src/autoresearch/`. The point isn't to actually replace LangGraph — it's to
make the abstractions concrete so we can reason about them and so the
research notes have something to point at.

A harness is the answer to six questions. Build one piece at a time.

## 1. Typed shared state

```python
from typing import Annotated, TypedDict

def merge_lists(a: list, b: list) -> list:
    return [*a, *b]

class State(TypedDict, total=False):
    topic: str
    notes: Annotated[list[str], merge_lists]
    plan: dict | None
    findings: Annotated[list[str], merge_lists]
```

**Rules**:

- Every key has a *single owner*. Writes from non-owners are rejected.
- List-shaped slots have an explicit reducer. Default to *append-only*.
- Scalars are last-write-wins; that's fine if only one node writes.

In our repo: `state.GraphState` + `_merge_lists`.

## 2. Node = pure-ish callable

```python
Node = Callable[[State], dict]   # returns ONLY the slot(s) it owns
```

Two properties make nodes testable:

- **Pure-ish**: deterministic given state + injected clients (LLM, HTTP).
- **Slot-scoped**: returns just its keys; the harness merges via reducers.

Anti-property: a node that mutates `state` in place. Don't allow it; the merge
contract depends on returns.

## 3. Scheduler

The scheduler decides what runs next. Three primitives cover everything:

```python
graph.add_edge(a, b)                          # static
graph.add_conditional_edges(a, route, mapping) # dynamic
graph.add_send(a, items)                       # fan-out (map)
```

Implementation sketch:

```python
class Graph:
    def __init__(self, state_cls):
        self.state_cls = state_cls
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[str | Callable]] = defaultdict(list)

    def invoke(self, init: dict) -> dict:
        state = init
        frontier = ["START"]
        while frontier:
            cur = frontier.pop(0)
            if cur == "END":
                continue
            if cur != "START":
                update = self.nodes[cur](state)
                state = self._merge(state, update)
            for edge in self.edges[cur]:
                nxt = edge(state) if callable(edge) else edge
                if nxt:
                    frontier.append(nxt)
        return state
```

**Loop discipline**: every back-edge needs a counter. The simplest
implementation puts the counter in state under a `_meta` slot the scheduler
owns.

## 4. Tool gateway

Tools are functions; the gateway is what *says yes* to a call.

```python
class ToolGateway:
    def __init__(self, registry: dict[str, Tool], allowlist: dict[str, set[str]]):
        self.registry = registry
        self.allowlist = allowlist  # persona -> {tool_name, ...}

    def call(self, persona: str, name: str, **kwargs):
        if name not in self.allowlist.get(persona, set()):
            raise PermissionError(f"{persona} not allowed to call {name}")
        tool = self.registry[name]
        args = tool.schema.model_validate(kwargs)  # Pydantic validation
        return tool.run(args)
```

**Two non-obvious requirements**:

- Validate args *with the tool's schema* before calling. The LLM will produce
  malformed args; failing here turns a runtime crash into a typed error the
  agent can recover from.
- Uniform error contract: tools should return `{ok: bool, value | error}`,
  not raise. This is what lets you replay traces deterministically.

## 5. Structured output

Wrap the LLM call so the agent receives a *typed object*, not a string.

```python
def call_llm_structured(prompt, schema: type[BaseModel], retries=2):
    for _ in range(retries):
        raw = llm.invoke(prompt + f"\nReturn JSON matching: {schema.model_json_schema()}")
        try:
            return schema.model_validate_json(raw.content)
        except ValidationError as e:
            prompt += f"\nPrevious output failed validation: {e}. Retry."
    raise StructuredOutputError(...)
```

This is the single biggest reliability lever. Native function-calling /
structured-outputs APIs are strictly better than ad-hoc JSON-in-string when
the provider supports them.

## 6. Observability

Two layers:

- **Tracing**: every node entry/exit, every tool call, every LLM call. OTel
  spans with attributes (persona, tool name, token counts).
- **Replay fixtures**: capture `(state_in, llm_response, tool_responses) →
  state_out` for known runs. Store as JSON. Tests load fixtures and replace
  the LLM/tool gateway with a deterministic player.

In our repo: tests already use the `fake_agent` fixture for node-level
replay. Tracing hook is planned.

## Mapping to our POC

| Concern        | This note                              | Our code                                          |
|----------------|----------------------------------------|---------------------------------------------------|
| State          | `TypedDict` + reducers                 | `state.GraphState`, `_merge_lists`                |
| Node           | `Callable[[State], dict]`              | `agents/base.Agent.__call__`                      |
| Scheduler      | `Graph`/edges                          | `graph/pipeline.build_graph` (LangGraph)          |
| Tool gateway   | `ToolGateway` w/ allowlist + Pydantic  | `personas.yaml: allowed_tools` + `tools/*` (gateway TODO) |
| Structured out | `call_llm_structured`                  | Pydantic models in `state.py` (binding TODO in `LLMAgent`) |
| Observability  | OTel + replay fixtures                 | `fake_agent` fixture; OTel hook planned           |

## When to actually build your own

Almost never. Reach for raw only if:

- The framework's runtime overhead is the bottleneck (rare; it's almost
  always the LLM call).
- You need a control-flow primitive the framework genuinely doesn't have.
- You're shipping the harness *as the product* and the framework's footprint
  is part of your dependency surface (e.g., embedded use).

For everything else, picking LangGraph (or CrewAI / AutoGen — see
`frameworks.md`) and *adding the pieces above on top* is the right move.
