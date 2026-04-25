"""Tool wrappers exposed to agents.

Tools must be pure-ish: deterministic given inputs + injected clients, and
side-effect-free outside of network/disk I/O explicitly noted in the docstring.
This keeps agent nodes replayable in tests via fakes.
"""

from .protocols import (
    FakeFetchURL,
    FakeWebSearch,
    FetchURL,
    ImagePromptStore,
    InMemoryImagePromptStore,
    WebSearch,
    WebSearchHit,
)

__all__ = [
    "FakeFetchURL",
    "FakeWebSearch",
    "FetchURL",
    "ImagePromptStore",
    "InMemoryImagePromptStore",
    "WebSearch",
    "WebSearchHit",
]
