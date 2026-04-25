"""Instructional designer: turns research notes into a DeckPlan."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..state import ContentBlock, DeckPlan, GraphState, SlidePlan
from .base import LLMAgent


class DesignerOutput(BaseModel):
    learning_objectives: list[str] = Field(default_factory=list)
    slides: list[SlidePlan] = Field(default_factory=list)


class InstructionalDesignerAgent(LLMAgent):
    persona_name = "instructional_designer"
    output_schema = DesignerOutput

    def build_user_prompt(self, state: GraphState) -> str:
        topic = state["topic"]
        audience = state.get("audience", "")
        notes = "\n".join(state.get("research_notes", []) or []) or "(no notes)"
        findings = state.get("review_findings", []) or []
        loop_findings = [f for f in findings if f.startswith("LOOP:")]
        revision = (
            "\nQA requested revisions:\n" + "\n".join(loop_findings) if loop_findings else ""
        )
        return (
            f"Topic: {topic}\nAudience: {audience}\n\n"
            f"Research notes (cite by [Nk]):\n{notes}\n"
            f"{revision}\n\n"
            "Produce a DeckPlan obeying these constraints:\n"
            "- 8–12 slides total.\n"
            "- Slide 1: title slide. Slide 2: learning objectives.\n"
            "- ≥1 quiz block per 5 slides.\n"
            "- ≥1 scenario block per module.\n"
            "- Mix content kinds: bullets, infographic, flowchart, diagram, "
            "table, image, quiz, scenario.\n"
            "- Every block that makes a factual claim must include a citation."
        )

    def merge(self, state: GraphState, output: DesignerOutput) -> dict:
        plan = DeckPlan(
            topic=state["topic"],
            audience=state.get("audience", ""),
            learning_objectives=output.learning_objectives,
            slides=output.slides,
        )
        return {"deck_plan": plan}


# Convenience for composing a deck from raw blocks (used in case-study seeds).
def slide(layout: str, *blocks: ContentBlock, notes: str = "") -> SlidePlan:
    return SlidePlan(layout=layout, blocks=list(blocks), speaker_notes=notes)
