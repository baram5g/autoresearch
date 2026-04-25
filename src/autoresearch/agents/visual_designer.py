"""Visual designer: enriches the existing DeckPlan with image prompts.

Must NOT change pedagogical structure (slide order, learning objectives,
content kinds). Only adds/updates image prompts and may set layout hints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..llm import LLMClient
from ..state import GraphState
from ..tools import ImagePromptStore, InMemoryImagePromptStore
from .base import LLMAgent, Persona


class ImagePrompt(BaseModel):
    slide_index: int = Field(..., ge=0)
    prompt: str


class VisualDesignerOutput(BaseModel):
    image_prompts: list[ImagePrompt] = Field(default_factory=list)


class VisualDesignerAgent(LLMAgent):
    persona_name = "visual_designer"
    output_schema = VisualDesignerOutput

    def __init__(
        self,
        client: LLMClient,
        prompt_store: ImagePromptStore | None = None,
        persona: Persona | None = None,
    ) -> None:
        super().__init__(client, persona)
        self.prompt_store = prompt_store or InMemoryImagePromptStore()

    def build_user_prompt(self, state: GraphState) -> str:
        plan = state.get("deck_plan")
        if plan is None:
            return "No deck plan yet."
        lines = []
        for i, s in enumerate(plan.slides):
            kinds = ", ".join(b.kind for b in s.blocks)
            lines.append(f"Slide {i}: layout={s.layout}, kinds=[{kinds}]")
        return (
            "Existing deck:\n" + "\n".join(lines) + "\n\n"
            "For every slide that contains an `image` block, propose a concise "
            "(<= 30 words) image prompt that matches the slide's pedagogical intent. "
            "Do not change slide order, kinds, or text. Index slides from 0."
        )

    def merge(self, state: GraphState, output: VisualDesignerOutput) -> dict:
        plan = state.get("deck_plan")
        if plan is None:
            return {}
        # Mutate image-block prompts in place (visual designer's only allowed mutation).
        new_plan = plan.model_copy(deep=True)
        for ip in output.image_prompts:
            if 0 <= ip.slide_index < len(new_plan.slides):
                for block in new_plan.slides[ip.slide_index].blocks:
                    if block.kind == "image":
                        block.body["prompt"] = ip.prompt
                self.prompt_store.remember(ip.slide_index, ip.prompt)
        return {"deck_plan": new_plan}
