"""Build the production pipeline from an LLMClient + tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..agents.designer import InstructionalDesignerAgent
from ..agents.qa import QAReviewerAgent
from ..agents.researcher import ResearcherAgent
from ..agents.visual_designer import VisualDesignerAgent
from ..llm import LLMClient
from ..pptx import render_deck
from ..state import GraphState
from ..tools import ImagePromptStore, InMemoryImagePromptStore, WebSearch
from ..tools.protocols import FakeWebSearch
from ..tracing import traced
from .pipeline import build_graph


def build_pipeline(
    *,
    client: LLMClient,
    out_path: Path | str,
    search: WebSearch | None = None,
    prompt_store: ImagePromptStore | None = None,
) -> Any:
    """Wire persona-bound LLM agents and the renderer into the graph."""
    search = search or FakeWebSearch()
    prompt_store = prompt_store or InMemoryImagePromptStore()

    researcher = ResearcherAgent(client, search=search)
    designer = InstructionalDesignerAgent(client)
    visual = VisualDesignerAgent(client, prompt_store=prompt_store)
    qa = QAReviewerAgent(client)

    def render(state: GraphState) -> dict:
        plan = state["deck_plan"]
        path = render_deck(plan, out_path)
        return {"output_path": str(path)}

    return build_graph(
        {
            "researcher": traced("researcher", researcher),
            "designer": traced("designer", designer),
            "visual": traced("visual", visual),
            "qa": traced("qa", qa),
            "render": traced("render", render),
        }
    )
