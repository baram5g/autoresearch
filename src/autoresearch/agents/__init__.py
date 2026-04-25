"""Persona-bound agents.

Each agent is a callable ``(GraphState) -> dict`` returning ONLY the keys it
owns. Personas (system prompt + tool whitelist + output schema) live in
``personas.yaml`` and are loaded by :func:`load_persona`.
"""

from .base import Agent, LLMAgent, Persona, load_persona

__all__ = ["Agent", "LLMAgent", "Persona", "load_persona"]
