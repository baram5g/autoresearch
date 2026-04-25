"""Shared fixtures.

Convention: tests must NEVER hit the network or a real LLM. Use
``fake_agent`` to stub agent nodes and inject deterministic state slices.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest


@pytest.fixture
def fake_agent() -> Callable[[dict], Callable]:
    def _make(returns: dict) -> Callable:
        def _node(_state):
            return returns
        return _node
    return _make
