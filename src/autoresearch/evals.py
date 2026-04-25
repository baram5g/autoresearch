"""Offline eval harness.

Scores a DeckPlan on five rubric axes that map to research-backed pedagogical
quality signals (see docs/case_study/heuristics.md). Pure function — no LLM,
no network — so it doubles as a CI gate.
"""

from __future__ import annotations

from pydantic import BaseModel

from .state import DeckPlan


class DeckScore(BaseModel):
    objective_coverage: float
    content_variety: float
    citation_density: float
    quiz_density: float
    scenario_presence: float
    total: float

    def as_table(self) -> str:
        rows = [
            ("Objective coverage", self.objective_coverage),
            ("Content variety", self.content_variety),
            ("Citation density", self.citation_density),
            ("Quiz density", self.quiz_density),
            ("Scenario presence", self.scenario_presence),
            ("Total", self.total),
        ]
        return "\n".join(f"  {name:<22} {v:.2f}" for name, v in rows)


_TARGET_KINDS = {
    "title", "bullets", "quiz", "scenario", "infographic",
    "flowchart", "diagram", "table", "image",
}


def score_deck(plan: DeckPlan) -> DeckScore:
    n_slides = max(len(plan.slides), 1)
    kinds = [b.kind for s in plan.slides for b in s.blocks]

    # 1. Objective coverage: fraction of objectives mentioned in any slide title/text.
    if plan.learning_objectives:
        slide_text = " ".join(
            (s.speaker_notes or "")
            + " "
            + " ".join((b.title or "") for b in s.blocks)
            for s in plan.slides
        ).lower()
        covered = sum(
            1
            for o in plan.learning_objectives
            if any(w in slide_text for w in o.lower().split()[:3])
        )
        objective_coverage = covered / len(plan.learning_objectives)
    else:
        objective_coverage = 0.0

    # 2. Content variety: distinct kinds used / target set, capped at 1.
    distinct = len(set(kinds) & _TARGET_KINDS)
    content_variety = min(distinct / 7.0, 1.0)  # 7 of 9 kinds = 1.0

    # 3. Citation density: citations per slide, normalised at 1 cite/slide.
    citations = sum(len(b.citations) for s in plan.slides for b in s.blocks)
    citation_density = min(citations / n_slides, 1.0)

    # 4. Quiz density: target = 1 quiz per 5 slides.
    target_quiz = max(1, n_slides // 5)
    actual_quiz = kinds.count("quiz")
    quiz_density = min(actual_quiz / target_quiz, 1.0)

    # 5. Scenario presence: at least one scenario.
    scenario_presence = 1.0 if "scenario" in kinds else 0.0

    total = (
        0.25 * objective_coverage
        + 0.20 * content_variety
        + 0.20 * citation_density
        + 0.20 * quiz_density
        + 0.15 * scenario_presence
    )
    return DeckScore(
        objective_coverage=objective_coverage,
        content_variety=content_variety,
        citation_density=citation_density,
        quiz_density=quiz_density,
        scenario_presence=scenario_presence,
        total=total,
    )
