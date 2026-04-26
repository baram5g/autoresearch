"""Multi-provider LLM wrapper.

A persona declares ``model: <id>`` in its YAML frontmatter. The string
prefix selects the provider:

- ``gpt-*``      → OpenAI (requires ``OPENAI_API_KEY``)
- ``claude-*``   → Anthropic (requires ``ANTHROPIC_API_KEY``)
- ``fake:*``     → FakeLLM driven by a scripted dict, for tests/demo

The OpenAI and Anthropic SDKs are imported lazily so the package is
usable in hermetic mode (FakeLLM only) without those dependencies.
"""

from __future__ import annotations

import os
from typing import Protocol


class LLM(Protocol):
    model: str

    def call(self, system: str, user: str) -> str: ...


class OpenAILLM:
    def __init__(self, model: str) -> None:
        from openai import OpenAI  # lazy import

        self.model = model
        self._client = OpenAI()

    def call(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""


class AnthropicLLM:
    def __init__(self, model: str) -> None:
        from anthropic import Anthropic  # lazy import

        self.model = model
        self._client = Anthropic()

    def call(self, system: str, user: str) -> str:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )


class FakeLLM:
    """Deterministic LLM for tests and offline demos.

    ``responses`` maps a *substring of the user prompt* to the response
    that should be returned when that substring is present. The first
    matching key wins. If nothing matches, returns ``default``.
    """

    def __init__(
        self,
        model: str,
        responses: dict[str, str] | None = None,
        default: str = "",
    ) -> None:
        self.model = model
        self.responses = responses or {}
        self.default = default
        self.calls: list[tuple[str, str]] = []

    def call(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        for needle, reply in self.responses.items():
            if needle in user:
                return reply
        return self.default


def make_llm(model: str) -> LLM:
    if model.startswith("fake:"):
        return FakeLLM(model)
    if model.startswith(("gpt-", "o1-", "o3-")):
        return OpenAILLM(model)
    if model.startswith("claude-"):
        return AnthropicLLM(model)
    raise ValueError(f"Unknown model family for {model!r}")


def has_api_keys() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY")) and bool(
        os.environ.get("ANTHROPIC_API_KEY")
    )
