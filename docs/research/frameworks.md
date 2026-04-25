# Framework comparison: LangGraph vs CrewAI vs AutoGen vs raw

This compares the three main multi-agent harness frameworks plus a "no
framework" baseline, on the axes that actually matter when you ship something.

> Versions referenced (pinned): LangGraph ≥ 0.2, CrewAI ≥ 0.60, AutoGen
> (autogen-agentchat) ≥ 0.4. Evaluate against current docs before adopting.

## At a glance

| Axis                       | LangGraph                                | CrewAI                                  | AutoGen (v0.4+)                          | Raw (your own code)                |
|----------------------------|------------------------------------------|-----------------------------------------|------------------------------------------|------------------------------------|
| **Mental model**           | Typed state graph (StateGraph)           | Crew of role-bound agents w/ tasks      | Chat-centric: agents exchange messages   | Whatever you write                 |
| **Control flow**           | Explicit nodes + conditional edges       | Sequential / hierarchical task lists    | Chat manager + group-chat patterns       | Imperative                         |
| **State**                  | First-class typed dict + reducers        | Implicit (task outputs chained)         | Message history + per-agent memory       | You define it                      |
| **Personas**               | External (your code); we use YAML        | First-class `Agent(role, goal, backstory)` | First-class `AssistantAgent`/`UserProxy`/etc. | DIY                                |
| **Tool model**             | Tools attached per-node                  | Tools attached per-Agent                | Tools registered with agent              | DIY                                |
| **Structured output**      | Pydantic via LangChain bindings          | Pydantic via task `output_pydantic`     | Pydantic via response_format             | DIY                                |
| **Loops / retries**        | Conditional edges + you cap              | Limited; planning loop available        | GroupChat termination conditions         | DIY                                |
| **Streaming**              | Token + node-event streams               | Limited                                 | Native                                   | DIY                                |
| **Observability**          | LangSmith hooks; OTel via Callbacks      | Built-in telemetry; OTel via plugins    | OTel-friendly; custom logger             | DIY                                |
| **Concurrency**            | Parallel branches via fan-out edges      | `Process.hierarchical` w/ manager       | GroupChat is sequential by default       | DIY                                |
| **Best fit**               | Deterministic pipelines with branching   | "Team of specialists" with clear roles  | Open-ended conversation among agents     | Tight latency / unusual flows      |
| **Worst fit**              | Pure chat-style multi-agent debate       | Highly branching graphs / loops         | Strict structured-output pipelines       | Anything you'll need to maintain   |

## How each models the four core concerns

### State
- **LangGraph**: `StateGraph[TypedDict]` with reducer functions per key. Nodes
  return partial updates. This is the closest to a real blackboard and is why
  we picked it — slot ownership is enforceable.
- **CrewAI**: state is the *chain of task outputs*. Cross-task sharing happens
  via `context=[other_task]` dependency wiring. Less ergonomic when many agents
  read/write overlapping fields.
- **AutoGen**: state is the *chat transcript* plus per-agent in-memory state.
  Excellent for emergent dialogue, awkward when you want a typed deck plan to
  flow through five agents without being re-parsed each hop.
- **Raw**: a Python dict and discipline. Fine for one-off scripts.

### Scheduling / control flow
- **LangGraph**: edges between nodes, including `add_conditional_edges` for
  branching. Loops are conditional edges back to a prior node. This is the
  exact primitive our QA→designer loop uses.
- **CrewAI**: `Process.sequential` (default) or `Process.hierarchical` (a
  manager LLM dispatches tasks). Loops are doable but feel grafted on.
- **AutoGen**: `GroupChat` + `GroupChatManager` decides next speaker; or
  `RoundRobinGroupChat`, `SelectorGroupChat`. Termination via `TextMentionTermination`,
  `MaxMessageTermination`, etc.
- **Raw**: write the loop. Easy to hide bugs in.

### Tool authorisation
- **LangGraph**: tools are bound to the LLM at the node. Allowlist is whatever
  you bind. We add an explicit `allowed_tools` field in our persona YAML and
  enforce it in `agents/base.py` so the policy is auditable separately from
  the LLM binding.
- **CrewAI**: `tools=[...]` on the `Agent`. Same effect.
- **AutoGen**: tools registered with the agent or via tool-using assistant.
- **Raw**: gateway function with an allowlist check.

### Persona model
- **LangGraph**: framework is agnostic — personas are *your* abstraction. This
  is good (you can encode whatever ownership rules you want) and bad (you have
  to encode them).
- **CrewAI**: most opinionated. `role`, `goal`, `backstory`, `tools` are
  first-class. Excellent default ergonomics for "team of specialists" but
  baked-in prompt scaffolding can fight you when you want tight control.
- **AutoGen**: persona ≈ system message on `AssistantAgent`. Less structure
  than CrewAI, more than LangGraph.

## Why we chose LangGraph for this POC

1. **Slot ownership is the central correctness rule** for compliance content
   (researcher cites; designer plans; QA only audits). Reducers + conditional
   edges encode this directly.
2. **Bounded loops** (QA→designer, max 2) are a one-liner.
3. **Replay/fakes for testing** are trivial because nodes are plain callables
   — no framework-managed agent identity to mock.
4. **Comparison with raw** stays close: a LangGraph compiled graph is
   essentially `dict[str, Callable] + edges`, so if we ever outgrow it, the
   migration is mechanical.

## When we'd reach for the others

- **CrewAI** if the project pivots to "team of specialists where the manager
  decides the plan dynamically and roles are stable" — e.g. a research-only
  product with no rendering pipeline.
- **AutoGen** if the value is in *agent-to-agent dialogue* — e.g. a debate or
  Socratic-tutor product. Our pipeline doesn't benefit from chat semantics.
- **Raw** for ultra-tight latency, or if the surface is small enough that the
  framework's footprint outweighs the abstraction.

## Decision rubric (use this when extending)

Pick LangGraph unless **two or more** of the following hold, in which case
re-evaluate:

- Control flow is dominated by free-form agent dialogue.
- The team of agents and their tools rarely changes shape.
- You want the framework to make persona scaffolding decisions for you.
- You don't need typed structured state across hops.
