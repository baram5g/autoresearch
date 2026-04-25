"""LangGraph wiring: researcher → designer → visual_designer → qa → render.

The graph is built in :func:`build_graph` and is the only place where node
order, conditional edges, and retry loops are defined. Agents themselves
are persona-bound and oblivious to topology.
"""

from .builder import build_pipeline
from .pipeline import build_graph

__all__ = ["build_graph", "build_pipeline"]
