# karpathy/autoresearch — methodology notes

Source: <https://github.com/karpathy/autoresearch>
(@karpathy, March 2026; teaser tweet.)

## What it is (in one paragraph)

A self-driving experimentation harness for LLM pre-training. The agent owns a
**single editable file** (`train.py`) and runs **fixed-budget experiments**
(5 minutes wall-clock) against a pinned eval (`val_bpb`, lower is better,
vocab-size-independent). After every run the agent decides keep / discard,
appends a row to `results.tsv`, advances or rewinds the branch, and loops
until the human interrupts. The whole "research org" is a Markdown file
(`program.md`) — the agent's skill. The framework is intentionally tiny
(`prepare.py` + `train.py` + `program.md`).

## Design choices that matter

| Choice | Why |
|---|---|
| **One file edited, one file read-only** | Keeps diffs reviewable; eval can't drift. |
| **Fixed-budget, wall-clock training** | Architectural changes are directly comparable; ~12 experiments/hour is enough to make overnight loops productive. |
| **Vocab-size-independent metric (`val_bpb`)** | Architectural search can change tokenizer / vocab without breaking comparability. |
| **Append-only `results.tsv`** | Five columns: commit, metric, memory, status, description. Status ∈ {keep, discard, crash}. |
| **Branch per run (`autoresearch/<tag>`)** | Bisectable history; `git reset --hard` is the rollback primitive. |
| **`program.md` as agent program** | The "research-org code" is prose. You iterate on the prose to make experiments better, not the framework. |
| **NEVER STOP rule** | The agent doesn't ask "should I keep going?" — autonomy is the point. |
| **Simplicity criterion** | Equal score with a smaller diff = win. Encourages pruning. |

## Mapping onto our PPT harness

| karpathy/autoresearch | Our PPT harness |
|---|---|
| `train.py` (editable) | `agents/personas.yaml` + `seeds.py` (the policy surface) |
| `prepare.py` (read-only) | `graph/`, `evals.py`, `judge.py`, `pptx/render.py` |
| `evaluate_bpb` (ground truth, low=good) | `judge_deck.total` (high=good); tie-break with `score_deck` |
| Pinned val shard | `EVAL_TOPICS` list in `autoresearch_iter.py` |
| 5-minute fixed budget | One full graph invocation per topic in `EVAL_TOPICS` |
| `results.tsv` (5 cols) | `results.tsv` (commit, mean_judge, mean_evals, per_topic_judge, status, description) |
| `program.md` | `auto_loop.md` |
| `analysis.ipynb` | `scripts/autoresearch_analyze.py` |
| `git reset --hard` rollback | Same. |

## Why we needed a *separate* `judge.py`

`evals.score_deck` doubles as the QA gate (slides ≥ 8, ≥ 1 quiz / 5 slides,
etc.). Once the upgraded pipeline clears the gate it scores 0.97-0.98 — no
headroom, so an auto-research loop has nothing to drive. We added
`judge_deck` with five axes that *aren't* gated:

- `narrative_flow` (no repeated / sticky leading words across adjacent slides)
- `block_distribution_entropy` (Shannon entropy of block kinds)
- `citation_per_factual_block`
- `objective_alignment_per_slide` (every slide must hit ≥ 1 LO keyword)
- `audience_specificity` (every slide must echo audience-specific tokens)

Baseline scores **0.40**, upgraded scores **0.75**. The agent's job is to
push that upward without breaking tests or the QA gate.

## How a hypothetical overnight run would look

The agent picks one of the obvious weaknesses revealed by
`python scripts/autoresearch_analyze.py` — for example
`audience_specificity = 0.22` on the upgraded baseline — and tries:

1. **Designer-prompt edit**: "Every slide title must include either the
   audience or a token from the audience field." Re-run. Compare.
2. **Persona swap**: tighten the Designer system prompt to require
   `learning_objectives` keywords in each slide title.
3. **Seed-script tightening**: modify `upgraded_client` to embed the audience
   token into more slide titles, reflecting what a real LLM should produce
   under a tighter prompt.
4. **Block-kind balance**: add a "mix at least 5 distinct kinds" instruction.
5. **Citation specificity**: require URL-bearing citations on factual blocks.

Each is one commit, one runner invocation, one `results.tsv` row.

## Ideas for our pipeline (full list)

These are the concrete improvements unlocked by adopting the methodology.
Each is implementable as a single experiment in the auto-loop.

### Quality (judge axes the loop will drive up)

1. **Audience-locked titles**: tighten Designer prompt so every slide title
   includes one audience-specific token. Drives `audience_specificity`.
2. **LO-tagged slides**: extend `SlidePlan` with an optional
   `learning_objective_id` field; designer must tag each slide. Drives
   `objective_alignment_per_slide`.
3. **Citation specificity** (new judge axis): require URLs / DOIs on factual
   blocks; reject `"internal-policy.pdf"` placeholders.
4. **Narrative arc check** (new judge axis): use the LLM-as-judge to score
   "does slide N follow from N-1?" on a 0-1 scale.
5. **Reading-level match** (new judge axis): compute Flesch-Kincaid against
   audience-implied target.
6. **Cognitive-load cap**: penalise > 6 bullets/slide or > 18-word bullets.
7. **Anti-redundancy**: penalise n-gram overlap across slides.

### Design (visual quality)

8. **Layout templates**: a `layout` field already exists; add 3 themed
   layouts (title, content, section-break) with consistent typography.
9. **Brand-token application**: load a `brand.yaml` (palette + font) and
   apply via `python-pptx` so decks are visually consistent.
10. **Block sizing rules**: enforce title-area heights, padding, alignment.
11. **Smart image placement**: visual_designer emits image *prompts*; in real
    mode hand them to the existing `azure-image` MCP server, render with
    aspect-ratio-aware placement instead of placeholder rectangles.
12. **Dark-mode variant** + a contrast-ratio judge axis (WCAG AA).

### Process (the harness itself)

13. **`auto_loop.md` already added** — point Claude/Codex at it.
14. **Branch-per-run + `results.tsv`** — already wired.
15. **LLM-as-judge** as a third (real-mode) metric, scored against an
    explicit rubric; use it as the *secondary* signal so deterministic
    judges remain the primary gate (avoid reward-hacking the LLM).
16. **Bayesian-optimisation wrapper** over the prompt-temperature /
    top-k / max-new-tokens of each persona. Each suggestion is one commit.
17. **Diff-budget**: the auto-research agent must keep total diff under N
    lines to discourage scaffolding bloat (matches karpathy's simplicity
    criterion).
18. **Cross-topic generalisation gate**: refuse to `keep` a row if any single
    topic regresses by > 0.05 even when the mean improves — protects against
    over-fitting to one prompt.
19. **Eval-set rotation**: hold one topic out as a "test" set the agent
    cannot see in `EVAL_TOPICS`; report on it weekly to detect overfitting.
20. **Cost ledger**: log token-cost per run alongside `mean_judge` so the
    loop can optimise quality / $ instead of quality alone.

### Stretch

21. **Multi-arm bandit** over personas: the agent randomly perturbs *one*
    persona per experiment; over many runs the bandit reveals which
    persona's prompt has the highest marginal value.
22. **Tournament judging**: pairwise compare two decks with an LLM judge;
    Elo-rate the kept commits — same trick used in chatbot arenas.
23. **Self-play QA**: spawn a second QA persona with adversarial prompt;
    only `keep` if the deck survives both.

## Limits / risks

- **Reward hacking**: deterministic judges are gameable; e.g. you can
  trivially raise `audience_specificity` by stuffing the audience token into
  every title. Mitigations: (a) keep the LLM judge as a *secondary*
  oracle, (b) the cross-topic generalisation gate above, (c) a manual
  spot-check ratio (e.g. agent writes a one-line *rationale* for each KEEP;
  human reviews 10 % offline).
- **Unbudgeted compute**: unlike karpathy's 5-min wall-clock cap, our
  pipeline runs near-instantly in demo mode but in real mode could call
  many LLM tokens. The cost ledger (#20) makes this visible.
- **Eval drift**: `judge.py` is part of the read-only set, but if we ever
  *do* edit it, all prior `results.tsv` rows become incomparable. Treat
  judge changes as an "epoch boundary" and start a new TSV.
