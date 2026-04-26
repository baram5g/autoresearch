from autoresearch.agents.qa import structural_findings
from autoresearch.state import ContentBlock, DeckPlan, SlidePlan


def test_structural_findings_flags_short_deck():
    plan = DeckPlan(topic="t", audience="a")
    findings = structural_findings(plan)
    assert any(f.startswith("LOOP:") and "slides" in f for f in findings)
    assert any("learning_objectives" in f for f in findings)


def test_structural_findings_passes_well_formed_deck():
    blocks_per_slide = [
        [ContentBlock(kind="title", title="t")],
        [ContentBlock(kind="bullets", body={"items": ["x"]}, citations=["[N1]"])],
        [ContentBlock(kind="quiz", body={"question": "q?"})],
        [ContentBlock(kind="scenario", body={"scenario": "s"})],
        [ContentBlock(kind="bullets", body={"items": ["y"]})],
        [ContentBlock(kind="bullets", body={"items": ["z"]})],
        [ContentBlock(kind="bullets", body={"items": ["Document the decision"]})],
        [ContentBlock(kind="bullets", body={"items": ["Escalate concerns"]})],
    ]
    plan = DeckPlan(
        topic="t",
        audience="a",
        learning_objectives=["o1"],
        slides=[SlidePlan(layout="x", blocks=b) for b in blocks_per_slide],
    )
    findings = structural_findings(plan)
    loops = [f for f in findings if f.startswith("LOOP:")]
    assert loops == []
