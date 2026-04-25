"""Lightweight tracing hook.

Opt-in via the ``AUTORESEARCH_TRACE`` env var (any truthy value). Wraps each
graph node with a context manager that prints node name + elapsed ms to
stderr. Drop-in replaceable with OTel ``tracer.start_as_current_span`` once
we're ready to ship real spans.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

TRACE = os.environ.get("AUTORESEARCH_TRACE", "").lower() in {"1", "true", "yes", "on"}


@contextmanager
def trace(name: str):
    if not TRACE:
        yield
        return
    t0 = time.perf_counter()
    try:
        yield
    finally:
        ms = (time.perf_counter() - t0) * 1000
        print(f"[trace] {name} {ms:.1f}ms", file=sys.stderr)


def traced(name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args, **kwargs):
        with trace(name):
            return fn(*args, **kwargs)

    return wrapper
