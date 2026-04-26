"""Agent base class and persona loader.

Personas are declarative — preferred format is one Markdown file per role under
``src/autoresearch/agents/personas/<role>.md`` with YAML frontmatter
(``role``, ``allowed_tools``) and a Markdown body that becomes the system
prompt. The legacy ``personas.yaml`` is still loaded as a fallback for any
role without a Markdown file.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from ..llm import LLMClient
from ..state import GraphState

PERSONAS_FILE = Path(__file__).with_name("personas.yaml")
PERSONAS_DIR = Path(__file__).with_name("personas")


@dataclass(frozen=True)
class Persona:
    name: str
    role: str
    system_prompt: str
    allowed_tools: tuple[str, ...]


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown file with YAML frontmatter delimited by '---' lines."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = yaml.safe_load(text[3:end]) or {}
    body = text[end + 4 :].lstrip("\n")
    return fm, body


def load_persona(name: str, path: Path = PERSONAS_FILE) -> Persona:
    md = PERSONAS_DIR / f"{name}.md"
    if md.exists():
        fm, body = _parse_frontmatter(md.read_text(encoding="utf-8"))
        return Persona(
            name=name,
            role=str(fm.get("role", name)),
            system_prompt=body,
            allowed_tools=tuple(fm.get("allowed_tools", []) or []),
        )
    data: dict[str, Any] = yaml.safe_load(path.read_text())
    spec = data[name]
    return Persona(
        name=name,
        role=spec["role"],
        system_prompt=spec["system_prompt"],
        allowed_tools=tuple(spec.get("allowed_tools", [])),
    )


class Agent:
    """Base class. Subclasses implement :meth:`run` and own one state slot."""

    persona_name: str

    def __init__(self, persona: Persona | None = None) -> None:
        self.persona = persona or load_persona(self.persona_name)

    def __call__(self, state: GraphState) -> dict:
        return self.run(state)

    def run(self, state: GraphState) -> dict:  # pragma: no cover - abstract
        raise NotImplementedError


class LLMAgent(Agent):
    """Persona-bound agent that produces structured output via an LLMClient.

    Subclasses set ``output_schema`` (a Pydantic model the agent emits) and
    implement :meth:`build_user_prompt` + :meth:`merge`. The base handles
    persona binding, structured-output validation, and slot-only return.
    """

    output_schema: type[BaseModel]

    def __init__(self, client: LLMClient, persona: Persona | None = None) -> None:
        super().__init__(persona)
        self.client = client

    def build_user_prompt(self, state: GraphState) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    def merge(self, state: GraphState, output: BaseModel) -> dict:  # pragma: no cover - abstract
        raise NotImplementedError

    def run(self, state: GraphState) -> dict:
        out = self.client.call_structured(
            persona=self.persona.name,
            system_prompt=self.persona.system_prompt,
            user_prompt=self.build_user_prompt(state),
            schema=self.output_schema,
        )
        return self.merge(state, out)


AgentNode = Callable[[GraphState], dict]
