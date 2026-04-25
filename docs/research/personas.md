# Personas

A **persona** in this codebase is a declarative spec — *not* a Python class —
that captures everything an agent needs to do its job *and nothing it doesn't*.
The Python `Agent` class is a thin adapter that loads a persona by name and
exposes it as a LangGraph node.

## Why declarative

Three forces push prompt + tool policy *out* of source code:

1. **Reviewability.** Reviewing a YAML diff for a prompt is straightforward;
   reviewing a Python diff that interleaves prompt edits with control flow is
   not.
2. **Auditability.** A compliance reviewer can read `personas.yaml` and tell
   you exactly what each agent is allowed to do, *without reading Python*.
3. **Hot iteration.** Most failed runs are prompt issues, not topology issues.
   Keeping prompts in YAML lets you iterate without touching the graph.

## The four fields a persona must answer

| Field           | Question it answers                                     |
|-----------------|---------------------------------------------------------|
| `role`          | What's their job title? (one short noun phrase)         |
| `system_prompt` | What do they do, and what shape is their output?        |
| `allowed_tools` | What's the *minimum* set of tools they need?            |
| (implicit) state slot | Which `GraphState` key do they own?               |

The state slot is implicit because it's enforced in `agents/base.py` and the
graph topology, not in YAML — but the persona's `system_prompt` should
reference its slot by name so the LLM and the human reviewer agree on
ownership.

## Slot ownership table (current pipeline)

| Persona                  | Owns                                                           |
|--------------------------|----------------------------------------------------------------|
| `researcher`             | `research_notes` (append-only, `_merge_lists` reducer)         |
| `instructional_designer` | `deck_plan` (replace; the QA loop may cause re-emission)        |
| `visual_designer`        | layout/visual fields *inside* `deck_plan.slides[*].blocks` only |
| `qa_reviewer`            | `review_findings` (append-only); signals loops with `LOOP:`     |

Violating ownership is a correctness bug, not a style nit: it breaks reducer
semantics and test fakes that assume each node returns only its slot.

## Persona pitfalls (and how we mitigate them)

| Pitfall                | What it looks like                                  | Mitigation                                                                 |
|------------------------|-----------------------------------------------------|----------------------------------------------------------------------------|
| **Persona drift**      | "I'm not just a researcher, I'm also kind of a designer" | Schema-validated structured output: if it isn't `list[str]` of notes, it's rejected. |
| **Capability leakage** | Designer somehow gets the search tool               | `allowed_tools` is the source of truth; tool gateway enforces.             |
| **Prompt bloat**       | 1k-token system prompts that contradict themselves   | Hard length cap on `system_prompt` in YAML lint (planned).                 |
| **Manager-itis**       | One persona that "coordinates" — really just adds a hop | Coordination is a graph concern; refuse to add coordinator personas.    |
| **Underspecified output shape** | Designer sometimes returns markdown, sometimes JSON | Pydantic-bound structured output on every persona-LLM call. |

## How other frameworks model personas

| Framework  | Persona shape                                                      | Trade-off vs ours                                                     |
|------------|--------------------------------------------------------------------|-----------------------------------------------------------------------|
| LangGraph  | None — DIY (we layered YAML on top)                                 | Maximum control, more code to write.                                  |
| CrewAI     | `Agent(role, goal, backstory, tools, llm)`                         | Ergonomic; opinionated prompt scaffolding may fight tight schemas.    |
| AutoGen    | `AssistantAgent(name, system_message, tools, model_client)`        | Lightweight; chat-shaped, less structured than CrewAI.                |

The CrewAI shape is the closest to ours. We chose YAML so prompts, roles, and
tool policy can be reviewed in one place without Python knowledge.

## Adding a persona — checklist

1. Add a YAML entry under `agents/personas.yaml` with `role`, `system_prompt`
   (≤ 800 tokens), `allowed_tools` (minimum set).
2. Pick its state slot in `state.GraphState`. If it appends, give the slot a
   reducer. Document the slot in the table above.
3. Subclass `Agent` (set `persona_name`), implement `run` so it returns *only*
   its slot.
4. Wire it into `graph/pipeline.py` — define edges, not behaviour.
5. Add a fake-agent test in `tests/agents/` that asserts the persona's output
   matches its declared schema.
