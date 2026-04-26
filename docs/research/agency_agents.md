# msitarzewski/agency-agents — methodology notes

Source: <https://github.com/msitarzewski/agency-agents>

## What it is (in one paragraph)

A curated **library of ~150+ AI agent personality files** organised by department
(engineering, design, marketing, sales, product, academic, project-management,
finance, paid-media, support, …). Each agent is a single Markdown file with
YAML frontmatter (`name`, `description`, `color`, `emoji`, `vibe`) followed by a
consistent template: **Identity & Memory · Core Mission · Critical Rules ·
Capabilities · Workflow · Communication Style · Success Metrics ·
Deliverable Templates**. There is no graph, no eval, no runtime — the framework
is just **prose** and an installer (`scripts/install.sh`) that copies persona
files into the agent location for Claude Code, GitHub Copilot, Cursor, Aider,
Windsurf, Gemini CLI, Antigravity, OpenCode, OpenClaw, Kimi Code. The value is
the **content** of the personas, not any orchestration layer.

## Why it complements karpathy/autoresearch

The two repositories sit at opposite ends of the harness stack:

| | karpathy/autoresearch | msitarzewski/agency-agents |
|---|---|---|
| What it gives you | Loop, metric, `keep`/`discard` discipline | Rich persona prompts |
| Editable surface | `train.py` (the policy) | The persona file itself |
| Failure mode it solves | Wandering experiments | Generic "you are a helpful assistant" prompts |
| Maps to our project | `auto_loop.md`, `judge.py`, `iter.py` | `agents/personas.yaml` content |

karpathy gave us the **search procedure**; agency-agents gives us the **prior**
to start the search from. Pairing them is the natural next step.

## How agency-agents files are structured (template we'll adopt)

```markdown
---
name: <Persona name>
description: <One-sentence pitch>
color: <hex or named>
emoji: <single emoji>
vibe: <Tagline>
---

# <Persona> Agent

## 🧠 Your Identity & Memory
…
## 🎯 Your Core Mission
…
## 🚨 Critical Rules You Must Follow
…
## 📋 Your Core Capabilities
…
## 🔄 Your Workflow Process
…
## 💭 Your Communication Style
…
## 🎯 Your Success Metrics
…
```

## Mapping into our PPT harness

Our current `agents/personas.yaml` declares only `system_prompt`,
`allowed_tools`, and `output_kind` per persona. That's the bare minimum to run.
Adopting the agency-agents template gives us four things our current files
lack:

1. **Critical Rules** — short, imperative, easy to lint against.
2. **Workflow Process** — explicit step-by-step that the LLM can follow.
3. **Success Metrics** — every persona declares what "good" looks like, which
   maps **one-to-one onto our `judge.py` axes**. Each persona becomes its own
   judge contributor.
4. **Deliverable Templates** — concrete output skeletons. Reduces format drift
   and shrinks the user-prompt the Designer/QA build at runtime.

## Personas already in the library that map to our project

| agency-agents persona | Maps onto / inspires | Notes |
|---|---|---|
| `design/visual-storyteller` | Our **Designer** | story arc B/M/E, emotional journey, visual pacing — directly the missing pieces in our current Designer. |
| `design/image-prompt-engineer` | Our **Visual Designer** | structured prompt layers (subject / environment / lighting / camera / style); pairs with the `azure-image` MCP server. |
| `design/brand-guardian` | **NEW persona** | enforces palette + typography + voice consistency from a `brand.yaml`. |
| `design/inclusive-visuals-specialist` | New QA pass | adds WCAG-AA contrast, alt-text, inclusive imagery requirements. |
| `design/ui-designer` | Layout templates | informs `pptx/render.py` layout system. |
| `academic/narratologist` | New QA reviewer pass | scores narrative arc (controlling idea, want/need/lie/transformation per slide-block). |
| `academic/psychologist` | Cognitive-load axis | informs bullets-per-slide, words-per-bullet rules. |
| `engineering/technical-writer` | Researcher's note formatter | tightens citation specificity and copy quality. |
| `engineering/code-reviewer` | Already aligned | matches our deterministic-then-LLM QA pattern. |

## What this unlocks for our pipeline

### Content quality
1. **Agency-style Designer** — rewrites `personas.yaml::designer` using the
   visual-storyteller template. Story arc becomes a hard requirement: every
   deck must have setup / conflict / resolution slide-groups.
2. **Narratologist QA pass** — adds a second QA reviewer that scores against
   Propp / Campbell / Todorov frameworks and emits `LOOP:` findings when the
   deck lacks a controlling idea or pays off no setup.
3. **Cognitive-load enforcement** — psychologist persona adds rules: ≤ 6
   bullets/slide, ≤ 12 words/bullet, ≥ 1 visual per 2 textual blocks.
4. **Tighter copy via Technical Writer** — pre-render pass that rewrites
   bullets to remove hedge words and require active voice.

### Visual / design quality
5. **Image Prompt Engineer rewrites our visual_designer prompts** — every
   image block gets a 5-layer prompt (subject / environment / lighting /
   camera / style + reference photographer). Drop-in win for the existing
   `azure-image` MCP.
6. **Brand Guardian as render-time linter** — load `brand.yaml` (palette,
   fonts, logo placement); reject decks that violate.
7. **Inclusive Visuals Specialist** as a new judge axis:
   `inclusive_imagery_specificity` — image prompts must include explicit
   demographic / ability descriptors and alt-text.
8. **UI Designer's layout grid** → 3 named layouts (`title`, `content`,
   `section_break`) with consistent typography & padding in `pptx/render.py`.

### Process / harness mechanics
9. **Per-persona success metrics → judge axes**: rewrite `judge.py` so each
   axis has a named owning persona, mirroring agency-agents' "Success Metrics"
   convention. Lets the auto-research loop attribute wins to specific
   personas.
10. **Persona library directory** — convert
    `src/autoresearch/agents/personas.yaml` into
    `src/autoresearch/agents/personas/<role>.md` (frontmatter + sections),
    matching agency-agents on disk. Loader compiles the markdown into the
    runtime `Persona` dataclass.
11. **Installer script** — adapt `scripts/install.sh` from agency-agents so
    our personas can also be used standalone in Claude Code / Copilot / Cursor
    when the user wants to author decks interactively without the harness.
12. **Persona swap experiments** — the auto-loop's editable surface becomes
    "switch the active Designer between v1, v2, v3 persona files"; each is
    one commit, one `iter.py` run, one `results.tsv` row. Persona-as-knob.
13. **Multi-persona ensemble for QA** — run Narratologist + UI Designer +
    Inclusive-Visuals in parallel; each emits findings; deck must satisfy
    all three before render. Cheap parallelism since structured calls are
    independent.
14. **Reference photographer / brand voice library** — pull the genre-specific
    prompt patterns from `image-prompt-engineer.md` into a `references.yaml`
    that all visual blocks consult.

### Stretch
15. **Whimsy Injector pass** — the agency-agents whimsy persona adds delight
    at boundaries; for training decks this maps to: one micro-narrative or
    callback per scenario block, pun-allowed in section breaks but never in
    quizzes/citations.
16. **Cross-departmental review** — borrow Marketing's `copywriter` for
    title polish and Project-Management's `chief-of-staff` for module
    sequencing. Same ensemble pattern as #13.
17. **Persona-personality auto-research** — combine with karpathy's loop:
    edit only `vibe` and `Critical Rules` in a persona file, measure
    `mean_judge`, keep/discard. Highest information-density edit surface.

## Limits / risks

- **Persona bloat**: agency-agents' value is breadth, but our pipeline only
  benefits from a handful. Adopt selectively; do not import 150 files.
- **Style drift**: rich persona prose can leak into deck prose if the
  Designer isn't constrained to its output schema. Already guarded by our
  Pydantic schemas; keep them.
- **No runtime to copy**: we cannot directly reuse code; the value is purely
  the persona content + on-disk template + install pattern.

## Concrete next-step checklist (in priority order)

1. ✅ Add 3 adapted persona files (this commit): Designer-as-visual-storyteller,
   Visual-Designer-as-image-prompt-engineer, Brand-Guardian.
2. Convert `personas.yaml` to per-file format under `agents/personas/*.md`.
3. Add `inclusive_imagery_specificity` judge axis (extends `judge.py`).
4. Wire visual_designer prompts to the `azure-image` MCP server.
5. Add Narratologist as a parallel QA reviewer.
6. Adopt agency-agents' `install.sh` pattern for standalone use.
