from autoresearch.evals import score_deck
from autoresearch.state import ContentBlock, DeckPlan, SlidePlan


def test_empty_deck_scores_low():
    s = score_deck(DeckPlan(topic="t", audience="a"))
    assert s.total < 0.1


def test_deck_with_variety_scores_higher():
    plan = DeckPlan(
        topic="t",
        audience="a",
        learning_objectives=["Identify red flags"],
        slides=[
            SlidePlan(layout="x", blocks=[
                ContentBlock(kind="title", title="Identify red flags"),
            ], speaker_notes="Identify red flags in procurement."),
            SlidePlan(layout="x", blocks=[ContentBlock(kind="quiz", body={"question": "q?"})]),
            SlidePlan(layout="x", blocks=[ContentBlock(kind="scenario", body={"scenario": "s"})]),
            SlidePlan(layout="x", blocks=[ContentBlock(kind="infographic",
                                                     body={"tiles": []}, citations=["[N1]"])]),
            SlidePlan(layout="x", blocks=[ContentBlock(kind="flowchart", body={"steps": []})]),
        ],
    )
    s = score_deck(plan)
    assert s.scenario_presence == 1.0
    assert s.quiz_density == 1.0
    assert s.objective_coverage > 0.0
    assert s.citation_density > 0.0
    assert s.total > 0.5
