"""Researcher agent: surveys the topic and emits cited research notes."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..llm import LLMClient
from ..state import GraphState
from ..tools import FakeWebSearch, WebSearch
from .base import LLMAgent, Persona


class ResearcherOutput(BaseModel):
    notes: list[str] = Field(
        ...,
        description=(
            "Research notes, each prefixed with a numeric id like '[N1] ...'. "
            "Each note ends with one or more URL citations in parentheses."
        ),
    )


class ResearcherAgent(LLMAgent):
    persona_name = "researcher"
    output_schema = ResearcherOutput

    def __init__(
        self,
        client: LLMClient,
        search: WebSearch | None = None,
        persona: Persona | None = None,
    ) -> None:
        super().__init__(client, persona)
        self.search = search or FakeWebSearch()

    def build_user_prompt(self, state: GraphState) -> str:
        topic = state["topic"]
        audience = state.get("audience", "")
        hits = self.search.search(f"{topic} compliance training latest trends", k=5)
        hit_lines = "\n".join(f"- {h.title} — {h.url}\n  {h.snippet}" for h in hits) or "(no hits)"
        return (
            f"Topic: {topic}\nAudience: {audience}\n\n"
            f"Search results to draw from:\n{hit_lines}\n\n"
            "Produce 5–10 numbered notes (`[N1]`, `[N2]`, …) with URL citations. "
            "Cover: regulatory framing, recent enforcement examples, audience-specific "
            "risks, and at least one statistic suitable for an infographic tile."
        )

    def merge(self, state: GraphState, output: ResearcherOutput) -> dict:
        return {"research_notes": list(output.notes)}
