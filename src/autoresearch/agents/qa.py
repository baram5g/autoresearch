"""QA reviewer: audits the DeckPlan and emits findings.

Findings prefixed ``LOOP:`` request another designer pass; other findings are
informational. Combines a static structural pass (no LLM call needed) with an
LLM-driven content audit, so the structural floor is enforced even if the LLM
client is misbehaving.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..state import DeckPlan, GraphState
from .base import LLMAgent


class QAOutput(BaseModel):
    findings: list[str] = Field(
        default_factory=list,
        description=(
            "Audit findings. Prefix with 'LOOP: ' iff a designer rerun would fix "
            "the issue. Otherwise return informational findings without prefix."
        ),
    )


def structural_findings(plan: DeckPlan) -> list[str]:
    """Cheap, deterministic checks that justify a designer rerun."""
    issues: list[str] = []
    n = len(plan.slides)
    if n < 8:
        issues.append(f"LOOP: deck has {n} slides; require at least 8.")
    kinds = [b.kind for s in plan.slides for b in s.blocks]
    if kinds.count("quiz") < max(1, n // 5):
        issues.append("LOOP: insufficient quiz coverage (need ≥1 per 5 slides).")
    if "scenario" not in kinds:
        issues.append("LOOP: no scenario block; add at least one.")
    if not plan.learning_objectives:
        issues.append("LOOP: missing learning_objectives.")
    # Citation density: at least one citation across all blocks.
    citation_total = sum(len(b.citations) for s in plan.slides for b in s.blocks)
    if citation_total == 0:
        issues.append("LOOP: no citations anywhere; cite at least factual claims.")
    return issues


class QAReviewerAgent(LLMAgent):
    persona_name = "qa_reviewer"
    output_schema = QAOutput

    def build_user_prompt(self, state: GraphState) -> str:
        plan = state.get("deck_plan")
        if plan is None:
            return "No deck plan yet."
        kinds = [b.kind for s in plan.slides for b in s.blocks]
        return (
            f"Topic: {state['topic']}\nAudience: {state.get('audience', '')}\n"
            f"Slide count: {len(plan.slides)}\nContent kinds: {kinds}\n"
            f"Objectives: {plan.learning_objectives}\n\n"
            "Audit for: factual accuracy of claims, regulatory alignment with the topic, "
            "and pedagogical soundness. Emit findings; prefix 'LOOP: ' iff a rerun "
            "would fix it."
        )

    def run(self, state: GraphState) -> dict:
        plan = state.get("deck_plan")
        passes = state.get("qa_passes", 0)
        structural = structural_findings(plan) if plan is not None else []
        # If the structural pass already says "needs rerun", skip the LLM call —
        # the designer hasn't earned an audit yet.
        if any(f.startswith("LOOP:") for f in structural):
            return {"review_findings": structural, "qa_passes": passes + 1}
        out = self.client.call_structured(
            persona=self.persona.name,
            system_prompt=self.persona.system_prompt,
            user_prompt=self.build_user_prompt(state),
            schema=self.output_schema,
        )
        return {
            "review_findings": [*structural, *out.findings],
            "qa_passes": passes + 1,
        }

    def merge(self, state: GraphState, output: QAOutput) -> dict:  # pragma: no cover - unused
        return {"review_findings": list(output.findings)}
