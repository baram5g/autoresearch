"""LLM-free deck judge with **headroom beyond the QA structural gate**.

`evals.score_deck` measures the same heuristics the QA agent uses to gate
designs, so once a deck clears QA those numbers saturate. This module adds
metrics with non-trivial ceilings — the kind of metric you want for an
autonomous-research loop (cf. ``docs/research/karpathy_autoresearch.md``):

- **narrative_flow** — penalises repeated slide titles and adjacent slides
  whose titles share a leading word.
- **block_distribution_entropy** — Shannon entropy of block kinds across the
  deck, normalised to 1.0. Rewards genuine variety, not just "≥ 1 of N kinds".
- **citation_per_factual_block** — fraction of bullets/infographic/table/diagram
  blocks that carry at least one citation.
- **objective_alignment_per_slide** — fraction of slides whose title/notes hit
  any keyword from any learning objective.
- **audience_specificity** — fraction of slides whose notes or titles mention an
  audience-specific term (heuristic via shared tokens with the audience field).

Pure function. No LLM. No network."""

from __future__ import annotations

import math
import re
from collections import Counter

from pydantic import BaseModel

from .state import DeckPlan

_FACTUAL_KINDS = {"bullets", "infographic", "table", "diagram", "flowchart"}
_INCLUSIVE_TOKENS = {
    "diverse", "inclusive", "multiethnic", "multi-ethnic", "multigenerational",
    "wheelchair", "hijab", "various", "mixed", "ages", "ethnicities",
    "gender-balanced", "neurodiverse", "global", "international",
}
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "at",
    "with", "by", "from", "as", "is", "be", "this", "that", "these", "those",
    "we", "you", "they", "it",
}


class DeckJudgement(BaseModel):
    narrative_flow: float
    block_distribution_entropy: float
    citation_per_factual_block: float
    objective_alignment_per_slide: float
    audience_specificity: float
    inclusive_imagery_specificity: float
    total: float

    def as_table(self) -> str:
        rows = [
            ("Narrative flow", self.narrative_flow),
            ("Block-distribution entropy", self.block_distribution_entropy),
            ("Citation per factual block", self.citation_per_factual_block),
            ("Objective alignment / slide", self.objective_alignment_per_slide),
            ("Audience specificity", self.audience_specificity),
            ("Inclusive imagery specificity", self.inclusive_imagery_specificity),
            ("Total", self.total),
        ]
        return "\n".join(f"  {name:<32} {v:.2f}" for name, v in rows)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS}


def _slide_titles(plan: DeckPlan) -> list[str]:
    out = []
    for s in plan.slides:
        title = next((b.title for b in s.blocks if b.kind == "title"), None)
        out.append((title or s.blocks[0].title or "").strip())
    return out


def judge_deck(plan: DeckPlan) -> DeckJudgement:
    n_slides = max(len(plan.slides), 1)
    titles = _slide_titles(plan)

    # 1. Narrative flow: 1.0 if titles are unique AND no two consecutive titles
    #    share a leading word; lose 1/n per violation.
    repeat_penalty = (len(titles) - len(set(t.lower() for t in titles))) / n_slides
    leading = [t.lower().split()[0] if t else "" for t in titles]
    adj_penalty = sum(
        1 for a, b in zip(leading, leading[1:], strict=False) if a and a == b
    ) / max(n_slides - 1, 1)
    narrative_flow = max(0.0, 1.0 - repeat_penalty - adj_penalty)

    # 2. Block-distribution entropy across kinds (excluding 'title' so the
    #    mandatory title block doesn't dominate).
    kinds = [b.kind for s in plan.slides for b in s.blocks if b.kind != "title"]
    if kinds:
        counts = Counter(kinds)
        n = sum(counts.values())
        h = -sum((c / n) * math.log2(c / n) for c in counts.values())
        # Normalise: max entropy with k distinct kinds is log2(k); we cap at log2(8)
        block_distribution_entropy = min(h / math.log2(8), 1.0)
    else:
        block_distribution_entropy = 0.0

    # 3. Citation per factual block.
    factual = [
        b for s in plan.slides for b in s.blocks if b.kind in _FACTUAL_KINDS
    ]
    if factual:
        with_cite = sum(1 for b in factual if b.citations)
        citation_per_factual_block = with_cite / len(factual)
    else:
        citation_per_factual_block = 0.0

    # 4. Objective alignment per slide.
    if plan.learning_objectives:
        lo_tokens = set().union(*(_tokens(o) for o in plan.learning_objectives))
        aligned = 0
        for s in plan.slides:
            text = " ".join(
                (b.title or "") for b in s.blocks
            ) + " " + (s.speaker_notes or "")
            if _tokens(text) & lo_tokens:
                aligned += 1
        objective_alignment_per_slide = aligned / n_slides
    else:
        objective_alignment_per_slide = 0.0

    # 5. Audience specificity: share tokens with the audience field.
    aud_tokens = _tokens(plan.audience or "")
    if aud_tokens:
        hits = 0
        for s in plan.slides:
            text = " ".join(
                (b.title or "") for b in s.blocks
            ) + " " + (s.speaker_notes or "")
            if _tokens(text) & aud_tokens:
                hits += 1
        audience_specificity = hits / n_slides
    else:
        audience_specificity = 0.0

    # 6. Inclusive imagery specificity: per-image-block check that the prompt
    #    is non-trivially long, contains an inclusive descriptor, and has
    #    alt-text. Decks with no image blocks score 1.0 (no penalty).
    image_blocks = [
        b for s in plan.slides for b in s.blocks if b.kind == "image"
    ]
    if image_blocks:
        good = 0
        for b in image_blocks:
            body = b.body or {}
            prompt = str(body.get("prompt", "") or "")
            alt = str(body.get("alt", "") or "")
            tokens = _tokens(prompt)
            if (
                len(prompt.split()) >= 12
                and (tokens & _INCLUSIVE_TOKENS)
                and alt.strip()
            ):
                good += 1
        inclusive_imagery_specificity = good / len(image_blocks)
    else:
        inclusive_imagery_specificity = 1.0

    total = (
        0.20 * narrative_flow
        + 0.18 * block_distribution_entropy
        + 0.18 * citation_per_factual_block
        + 0.18 * objective_alignment_per_slide
        + 0.13 * audience_specificity
        + 0.13 * inclusive_imagery_specificity
    )
    return DeckJudgement(
        narrative_flow=narrative_flow,
        block_distribution_entropy=block_distribution_entropy,
        citation_per_factual_block=citation_per_factual_block,
        objective_alignment_per_slide=objective_alignment_per_slide,
        audience_specificity=audience_specificity,
        inclusive_imagery_specificity=inclusive_imagery_specificity,
        total=total,
    )
