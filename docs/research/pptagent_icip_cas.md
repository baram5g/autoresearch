# PPTAgent / DeepPresenter (icip-cas) — harness review

Source: <https://github.com/icip-cas/PPTAgent>. Two stacks ship in the same
repo: the original **PPTAgent** core (EMNLP 2025 paper) under `pptagent/`,
and a newer **DeepPresenter** product surface (ACL 2026 paper) under
`deeppresenter/`. The repo's own `AGENTS.md` is explicit that
`deeppresenter/` is the primary product and `pptagent/` is the legacy core
plus the `pptagent-mcp` server. This review reads both with a harness lens.

## What it actually is

Not a prompt zoo and not a single prompt. PPTAgent is a real *two-stage*
pipeline:

1. **Presentation analysis (Stage I)** — `pptagent/induct.py::SlideInducter`
   ingests a *real* `.pptx` template, splits slides into functional vs
   content slides via an LLM, image-embeds the rendered slide JPGs, clusters
   them per `(layout_name, content_type)`, picks a representative template
   per cluster, and asks the vision model to *name* the cluster. Then
   `schema_extractor` derives a per-cluster JSON schema (element names,
   default quantities, suggested character counts).
2. **Generation (Stage II)** — `pptagent/pptgen.py` runs `planner →
   layout_selector → editor → coder` per slide. The `coder` (`roles/agent.yaml`)
   does **not** emit slide JSON — it emits an **API call sequence**
   (`replace_span`, `clone_paragraph`, `del_image`, `replace_image`, …)
   against an HTML representation of the chosen template slide. Render is
   deterministic; the LLM never writes geometry.

Evaluation is a separate harness, **PPTEval** (`pptagent/ppteval.py`),
which scores rendered slides on three axes — **content**, **style**,
**coherence** — through *vision-model description → language-model scoring*
prompts. The whole eval set is cached on disk per slide image.

## Harness architecture (concise)

| Layer                 | Where                              | Style                                     |
| --------------------- | ---------------------------------- | ----------------------------------------- |
| Persona + template    | `pptagent/roles/*.yaml`            | YAML: `system_prompt`, Jinja `template`, `jinja_args`, `use_model`, `return_json`, `run_args` |
| Agent runtime         | `pptagent/agent.py::Agent`         | Async, per-turn `Turn` history with retries, image-token accounting, `RETRY_TEMPLATE` for self-correction |
| Model multiplexing    | `pptagent/llms.py` + `model_utils.py` | Multiple `AsyncLLM` instances keyed by tag; each role declares `use_model: language|vision` |
| Pipeline orchestrator | `pptagent/pptgen.py`               | Hand-coded `async` pipeline, **not** LangGraph; aiometer for fan-out |
| Eval harness          | `pptagent/ppteval.py`              | LLM-as-judge with rendered-slide vision descriptions, results cached as `evals.json` |
| Tool surface          | `deeppresenter/tools/`             | MCP-style: search, research, reflection, file conversion, sandbox, task management; configured via `mcp.json.example` |
| Product CLI           | `deeppresenter/cli/`               | `pptagent onboard|generate|serve|config|reset` (Typer), workspace under `~/.cache/deeppresenter` |
| HTML→PPTX             | `deeppresenter/html2pptx/`         | Node-based browser conversion (Playwright + Chromium) — not python-pptx |

## What is well built (harness perspective)

1. **Persona = config, not code.** Each role is a YAML with a schema-checked
   `prompt_args` set; `Agent.__init__` enforces strict Jinja undefined and
   asserts callers pass exactly the expected keys. This is the *right*
   shape for a harness — it matches our agency-agents-style migration
   almost beat-for-beat, with stricter argument validation than ours.
2. **Self-correcting turn protocol.** `Agent.retry` re-issues the *same*
   turn id with a `RETRY_TEMPLATE` carrying `feedback` + `traceback`,
   replays the message history, and stores the retry indexed by
   `(id, retry)`. That's a reusable contract (any caller can run a
   structured-output validator and call `agent.retry(...)` on failure)
   instead of ad-hoc prompt-rewrite logic in every site.
3. **Two-headed model routing.** Roles declare `use_model: language` or
   `use_model: vision`; the runtime picks the right `AsyncLLM` from a
   mapping. This is exactly the abstraction we need before introducing
   our own vision reviewer — no special-casing inside the pipeline.
4. **Render is deterministic; the LLM controls *edits*, not geometry.**
   The `coder` agent emits API calls against parsed PPTX shapes
   (`replace_span(p_id, span_id, idx, text)` etc.). This is the single
   most important architectural decision in the repo: it means LLM
   non-determinism cannot break layout, and it gives the harness a
   tractable surface to validate (an API-call AST) before render.
5. **Layout induction is grounded in *real* PPTX templates.** The system
   doesn't invent layouts; it clusters the user's own slides by
   image-embedding similarity within `(layout_name, content_type)` and
   reuses them. That sidesteps the "LLM-imagined geometry" failure mode
   entirely.
6. **Eval is decoupled from generation.** `ppteval.py` runs against any
   rendered `.pptx`, caches per-slide scores in `evals.json`, and reports
   averaged scores over a directory of decks. It would slot cleanly into
   a karpathy-style auto-research loop.
7. **Async fan-out with rate limits.** `aiometer.run_all(..., max_at_once,
   max_per_second)` is built into induct/content extraction. A real
   harness needs this; our LangGraph pipeline currently doesn't.
8. **The product surface admits its own seams.** `AGENTS.md` explicitly
   distinguishes `deeppresenter/` (primary) from `pptagent/` (core +
   MCP), names the entrypoints, and warns the README is partially stale.
   That kind of self-honesty is rare and very useful for an agent
   working on the codebase.

## What is weak / risky (harness perspective)

1. **Two stacks, one repo, partial overlap.** `pptagent/` and
   `deeppresenter/` both define generation concepts. `AGENTS.md` calls
   this out, but it is still cognitive overhead and a real source of
   drift. From a harness POV this is an anti-pattern — there is no
   single source of truth for "what runs in production".
2. **README ↔ code drift.** README still tells users to `python webui.py`
   even though `AGENTS.md` says paths like `webui.py` may not exist.
   This is exactly the failure mode our research notes call out:
   prose stays, code moves.
3. **Eval is LLM-only.** Every PPTEval axis is "describe with vision
   model → score with language model". There is no deterministic floor
   (cf. our `judge.py` 6-axis scoring or `qa.structural_findings`). That
   makes scores noisy across model versions and impossible to use as a
   *gating* signal — only as a *reporting* signal. For an auto-research
   loop you'd want both.
4. **No QA loop.** The pipeline goes `planner → layout_selector → editor
   → coder` and renders. There is no reviewer step that can request a
   designer rerun, no loop counter, no `LOOP:` finding contract. Our
   harness is stronger here.
5. **`Agent` mutates `self.llm.__call__` via `partial` at construction
   time** (`agent.py: self.llm.__call__ = partial(self.llm.__call__,
   **run_args)`). That re-binds the bound method on a *shared* `AsyncLLM`
   instance. If two agents share the same model and declare different
   `run_args`, the last one wins for everybody. This is the kind of
   shared-mutable-state bug that bites in concurrent harnesses.
6. **`Turn.calc_cost` references `self.out_tokens`** while everywhere
   else uses `self.output_tokens` — looks like a typo that would only
   trigger on the non-final turn path. Indicates the cost path isn't
   exercised end-to-end.
7. **Brittle file-system contract for induction.** `SlideInducter.__init__`
   asserts that the count of template images, ppt images, and
   `prs.slides` are all equal *at construction*. Useful as a guard but
   poor as a harness contract — any upstream change in rendering breaks
   construction itself, and the `use_assert=False` escape hatch is
   undocumented.
8. **Heavy runtime surface.** Playwright + Chromium + Node + Docker
   sandbox + Tavily + MinerU + a fine-tuned 9B model on HuggingFace.
   This is not a problem for the project, but from a *harness*
   perspective it makes the system hard to test hermetically — no
   equivalent of our `FakeLLMClient` + scripted seeds.
9. **No formal output schemas at the role boundary.** Most roles return
   JSON parsed by `get_json_from_response`; only some calls pass a
   `response_format=BaseModel`. Our LangGraph pipeline pins every agent
   output to a Pydantic schema by construction, which is a stronger
   contract.
10. **Persona files are prompt-only.** Unlike our agency-agents-style
    md files, the YAML role definitions are pure prompt + template —
    there's no allowed-tools list or success-metrics section. Tools live
    one layer up in `deeppresenter/tools/`. That's a defensible split,
    but it means you can't audit "what is this persona allowed to do?"
    by reading the persona.

## Side-by-side vs our autoresearch harness

| Concern                      | PPTAgent / DeepPresenter           | autoresearch (this repo)              |
| ---------------------------- | ---------------------------------- | ------------------------------------- |
| Persona format               | YAML role + Jinja template         | Per-role md + YAML frontmatter        |
| Strict prompt-arg validation | ✅ (`prompt_args` assert)          | ❌ (free-form LangGraph state read)   |
| Multi-model routing          | ✅ (`use_model` tag)               | ⚠️ Single `LLMClient`                 |
| Self-correction protocol     | ✅ (`Agent.retry` with traceback)  | ⚠️ External `LOOP:` only              |
| Async fan-out + rate limit   | ✅ (`aiometer`)                    | ❌ (sequential graph)                 |
| Output-schema enforcement    | ⚠️ Per-call optional               | ✅ Mandatory Pydantic at every node   |
| Reviewer loop                | ❌ No QA loop                      | ✅ `LOOP:` + `MAX_REVIEW_LOOPS`       |
| Deterministic eval floor     | ❌ LLM-only                        | ✅ `judge.py` + `structural_findings` |
| Layout grounded in real PPT  | ✅ Cluster-from-template           | ❌ Layout names are free-form strings |
| Render = deterministic       | ✅ API-call sequence over template | ✅ python-pptx from typed plan        |
| Hermetic test harness        | ❌ Needs Docker + Playwright       | ✅ `FakeLLMClient` + scripted seeds   |

## Verdict

**Well-built where it matters most for a *generation* harness, weak where
it matters most for an *evaluation/iteration* harness.** The strong parts
are the layout-induction-from-real-templates plus deterministic API-call
rendering — that combination is genuinely better than what we have. The
weak parts are the missing reviewer loop, the LLM-only PPTEval, the
shared-LLM mutation bug, and the two-stack duplication. From a pure
"is this a well-built agent harness?" reading: **yes for generation,
no for closing the loop.**

## Concrete takeaways for our project

The following ideas are imports we should consider; **none commit us to
a rewrite**. Ranked by leverage.

1. **`use_model` routing.** Add a `model: language|vision` field to our
   persona md frontmatter and let `LLMClient` carry a mapping. Costs
   nothing now (one model), pays back when we add a vision reviewer.
2. **Strict `prompt_args` assert.** Each persona should declare which
   state keys it consumes; the `LLMAgent` base should assert that
   `build_user_prompt` only references declared keys. Prevents the
   cross-stack drift PPTAgent's own `AGENTS.md` warns about.
3. **Self-correcting `Agent.retry` contract.** Today our pipeline can
   *loop* on a deck; it cannot *retry* a bad structured output from a
   single agent. Adopting the `retry(feedback, traceback, turn_id)`
   contract would close that gap and let us use stricter Pydantic
   schemas without crashing on first parse failure.
4. **Vision-described, deterministic-floor judge.** Keep our 6-axis
   `judge.py` as the floor; add an *optional* PPTEval-style vision pass
   that scores style + coherence on rendered slides. Combine via fixed
   weights so a missing vision model degrades gracefully to 0 weight,
   not 0 score.
5. **Layout induction from a *real* template deck.** Long-term the most
   impactful idea: ship one or two `.pptx` templates, run an
   inducter-style clustering at *install* time, and have the designer
   pick from induced layout ids instead of free-form strings. Removes
   "LLM imagined a layout we don't render" entirely.
6. **API-call edit DSL.** Even without templates, expressing the
   designer's *delta* over the previous deck as `replace_block`,
   `clone_slide`, `del_block` calls (not a full new `DeckPlan`) makes
   the auto-research loop's diffs auditable and minimises regression
   between iterations.
7. **`aiometer` (or equivalent) for fan-out.** When we add per-slide
   image generation or per-slide vision scoring, we need
   `max_at_once` / `max_per_second` to respect upstream MCP rate limits.
8. **`evals.json` per-deck cache.** Mirrors our `results.tsv` but
   per-slide; cheap to add and would let the auto-research loop avoid
   re-scoring unchanged slides.

## Anti-patterns to avoid

- **Two stacks for one product.** Resist letting the legacy `harness
  research` notes drift away from runtime. Our `docs/research/*.md` are
  ideas, not contracts; runtime `personas/*.md` are.
- **LLM-only eval as a *gate*.** Use vision-judge scores for *reporting*,
  never for `LOOP:`-style routing.
- **Shared-mutable LLM clients.** If we adopt the `use_model` mapping,
  freeze run-args at the persona level — never `partial`-bind onto a
  shared client method.

## Pointers

- `pptagent/agent.py` — agent runtime, retry protocol, token accounting.
- `pptagent/induct.py` — Stage I: layout induction from real PPTX.
- `pptagent/pptgen.py` — Stage II: planner→selector→editor→coder.
- `pptagent/ppteval.py` — vision-described LLM-as-judge eval.
- `pptagent/roles/*.yaml` — persona+template definitions worth reading.
- `pptagent/AGENTS.md` (root) — the most candid harness doc in the repo.
