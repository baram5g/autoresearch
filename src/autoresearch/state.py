"""Shared LangGraph state schema.

The state is the single source of truth that flows between every agent node in
``autoresearch.graph``. Agents read prior fields and append to their own slot;
they must NOT mutate slots owned by other agents (see docs/research/architecture.md).
"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field

ContentBlockKind = Literal[
    "title",
    "bullets",
    "quiz",
    "scenario",
    "infographic",
    "flowchart",
    "diagram",
    "table",
    "image",
]


class ContentBlock(BaseModel):
    """One renderable unit consumed by ``autoresearch.pptx``."""

    kind: ContentBlockKind
    title: str | None = None
    body: dict = Field(default_factory=dict)
    citations: list[str] = Field(default_factory=list)


class SlidePlan(BaseModel):
    layout: str
    blocks: list[ContentBlock]
    speaker_notes: str = ""


class DeckPlan(BaseModel):
    topic: str
    audience: str
    learning_objectives: list[str] = Field(default_factory=list)
    slides: list[SlidePlan] = Field(default_factory=list)


def _merge_lists(left: list, right: list) -> list:
    """LangGraph reducer: nodes append; we concatenate."""
    return [*left, *right]


class GraphState(TypedDict, total=False):
    topic: str
    audience: str
    research_notes: Annotated[list[str], _merge_lists]
    deck_plan: DeckPlan
    review_findings: list[str]
    qa_passes: int
    output_path: str
