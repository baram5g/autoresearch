from autoresearch.graph import build_graph
from autoresearch.state import DeckPlan


def test_pipeline_routes_to_render_when_no_findings(fake_agent):
    graph = build_graph(
        {
            "researcher": fake_agent({"research_notes": ["n1"]}),
            "designer": fake_agent({"deck_plan": DeckPlan(topic="t", audience="a")}),
            "visual": fake_agent({}),
            "qa": fake_agent({"review_findings": []}),
            "render": fake_agent({"output_path": "/tmp/x.pptx"}),
        }
    )
    final = graph.invoke({"topic": "t", "audience": "a"})
    assert final["output_path"] == "/tmp/x.pptx"


def test_pipeline_loops_back_to_designer_on_findings(fake_agent):
    calls = {"designer": 0, "qa": 0}

    def designer(_state):
        calls["designer"] += 1
        return {"deck_plan": DeckPlan(topic="t", audience="a")}

    def qa(state):
        calls["qa"] += 1
        # Always emit a LOOP finding; the cap should stop us at 2 loops.
        return {
            "review_findings": ["LOOP: tighten quiz"],
            "qa_passes": state.get("qa_passes", 0) + 1,
        }

    graph = build_graph(
        {
            "researcher": fake_agent({"research_notes": []}),
            "designer": designer,
            "visual": fake_agent({}),
            "qa": qa,
            "render": fake_agent({"output_path": "/tmp/x.pptx"}),
        }
    )
    final = graph.invoke({"topic": "t", "audience": "a"})
    # Initial designer + 2 loops = 3 designer runs, 3 QA runs, then render.
    assert calls["designer"] == 3
    assert calls["qa"] == 3
    assert final["output_path"] == "/tmp/x.pptx"


def test_pipeline_does_not_loop_on_non_loop_findings(fake_agent):
    calls = {"designer": 0}

    def designer(_state):
        calls["designer"] += 1
        return {"deck_plan": DeckPlan(topic="t", audience="a")}

    def qa(state):
        return {
            "review_findings": ["nit: caption length"],  # no LOOP: prefix
            "qa_passes": state.get("qa_passes", 0) + 1,
        }

    graph = build_graph(
        {
            "researcher": fake_agent({"research_notes": []}),
            "designer": designer,
            "visual": fake_agent({}),
            "qa": qa,
            "render": fake_agent({"output_path": "/tmp/x.pptx"}),
        }
    )
    graph.invoke({"topic": "t", "audience": "a"})
    assert calls["designer"] == 1
