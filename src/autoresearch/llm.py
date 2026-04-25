"""LLM client protocol + fake for tests.

The protocol is intentionally minimal: one method that returns a Pydantic
model. This keeps agent code provider-agnostic and makes test fakes a
one-liner. Real-LLM bindings (OpenAI, Anthropic, etc.) implement
``call_structured`` and are wired in ``cli.py``.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    def call_structured(
        self,
        *,
        persona: str,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
    ) -> T: ...


class FakeLLMClient:
    """Deterministic client that replays scripted Pydantic objects per persona.

    Use ``script(persona, [obj1, obj2, ...])`` to enqueue responses. Each call
    pops the next response for that persona; an empty queue raises so tests
    fail loudly instead of silently returning stale data.
    """

    def __init__(self) -> None:
        self._queues: dict[str, deque[BaseModel]] = defaultdict(deque)
        self.calls: list[dict] = []

    def script(self, persona: str, responses: list[BaseModel]) -> None:
        for r in responses:
            self._queues[persona].append(r)

    def call_structured(
        self,
        *,
        persona: str,
        system_prompt: str,
        user_prompt: str,
        schema: type[T],
    ) -> T:
        self.calls.append(
            {"persona": persona, "user_prompt": user_prompt, "schema": schema.__name__}
        )
        q = self._queues.get(persona)
        if not q:
            raise RuntimeError(f"FakeLLMClient: no scripted response for persona={persona!r}")
        nxt = q.popleft()
        if not isinstance(nxt, schema):
            raise TypeError(
                f"FakeLLMClient: scripted {type(nxt).__name__} but agent expected {schema.__name__}"
            )
        return nxt
