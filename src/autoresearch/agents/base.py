"""Agent base class and persona loader.

Personas are declarative (YAML); agent classes are thin adapters that bind a
persona to a LangGraph node. This separation keeps prompt/tool-policy edits
out of Python source — see docs/research/personas.md.
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


@dataclass(frozen=True)
class Persona:
    name: str
    role: str
    system_prompt: str
    allowed_tools: tuple[str, ...]


def load_persona(name: str, path: Path = PERSONAS_FILE) -> Persona:
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
