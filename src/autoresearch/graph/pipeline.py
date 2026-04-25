"""Graph topology for the compliance-training pipeline."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from ..state import GraphState

MAX_REVIEW_LOOPS = 2


def build_graph(nodes: dict[str, Any]) -> Any:
    """Wire persona agents + renderer into the orchestration graph.

    ``nodes`` keys: ``researcher``, ``designer``, ``visual``, ``qa``, ``render``.

    QA → designer back-edge fires when (a) the latest QA pass emitted at least
    one finding prefixed ``LOOP:`` and (b) ``qa_passes < MAX_REVIEW_LOOPS``.
    Non-``LOOP:`` findings never trigger re-entry; the cap is hard.
    """
    g: StateGraph = StateGraph(GraphState)
    for name, fn in nodes.items():
        g.add_node(name, fn)

    g.add_edge(START, "researcher")
    g.add_edge("researcher", "designer")
    g.add_edge("designer", "visual")
    g.add_edge("visual", "qa")

    def _route_after_qa(state: GraphState) -> str:
        findings = state.get("review_findings", []) or []
        passes = state.get("qa_passes", 0)
        has_loop = any(f.startswith("LOOP:") for f in findings)
        # Allow up to MAX_REVIEW_LOOPS designer reruns. With increment-after-pass
        # semantics, the inequality is `<=`: passes==1 means one QA pass has run,
        # so up to MAX_REVIEW_LOOPS reruns are still permitted.
        if has_loop and passes <= MAX_REVIEW_LOOPS:
            return "designer"
        return "render"

    g.add_conditional_edges("qa", _route_after_qa, {"designer": "designer", "render": "render"})
    g.add_edge("render", END)
    return g.compile()
