"""Tool protocols + fake implementations for tests.

Runtime tools are bound to MCP servers (``fetch``, ``filesystem``,
``azure-image``) but the agent code talks to *protocols* declared here so
tests stay hermetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class WebSearchHit:
    title: str
    url: str
    snippet: str


class WebSearch(Protocol):
    def search(self, query: str, *, k: int = 5) -> list[WebSearchHit]: ...


class FetchURL(Protocol):
    def fetch(self, url: str) -> str: ...


class ImagePromptStore(Protocol):
    def remember(self, slide_index: int, prompt: str) -> None: ...


class FakeWebSearch:
    def __init__(self, scripted: dict[str, list[WebSearchHit]] | None = None) -> None:
        self.scripted = scripted or {}
        self.queries: list[str] = []

    def search(self, query: str, *, k: int = 5) -> list[WebSearchHit]:
        self.queries.append(query)
        return self.scripted.get(query, [])[:k]


class FakeFetchURL:
    def __init__(self, scripted: dict[str, str] | None = None) -> None:
        self.scripted = scripted or {}
        self.urls: list[str] = []

    def fetch(self, url: str) -> str:
        self.urls.append(url)
        return self.scripted.get(url, "")


class InMemoryImagePromptStore:
    def __init__(self) -> None:
        self.prompts: dict[int, str] = {}

    def remember(self, slide_index: int, prompt: str) -> None:
        self.prompts[slide_index] = prompt
