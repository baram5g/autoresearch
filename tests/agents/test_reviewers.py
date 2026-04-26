from autoresearch.agents.brand_guardian import brand_guardian_findings
from autoresearch.agents.narratologist import narratologist_findings
from autoresearch.state import ContentBlock, DeckPlan, SlidePlan


def _deck(slides):
    return DeckPlan(
        topic="t",
        audience="a",
        learning_objectives=["o"],
        slides=slides,
    )


def test_brand_guardian_no_yaml_returns_empty(tmp_path, monkeypatch):
    monkeypatch.delenv("BRAND_YAML", raising=False)
    monkeypatch.chdir(tmp_path)
    plan = _deck([SlidePlan(layout="t", blocks=[ContentBlock(kind="title", title="x")])])
    assert brand_guardian_findings(plan) == []


def test_brand_guardian_flags_banned_phrase(tmp_path, monkeypatch):
    brand = tmp_path / "brand.yaml"
    brand.write_text("banned_phrases: ['world-class']\n")
    monkeypatch.setenv("BRAND_YAML", str(brand))
    plan = _deck([
        SlidePlan(layout="t", blocks=[
            ContentBlock(kind="title", title="A world-class programme"),
        ]),
    ])
    findings = brand_guardian_findings(plan)
    assert any("world-class" in f and f.startswith("LOOP:") for f in findings)


def test_brand_guardian_flags_missing_alt_when_required(tmp_path, monkeypatch):
    brand = tmp_path / "brand.yaml"
    brand.write_text("image_alt_required: true\n")
    monkeypatch.setenv("BRAND_YAML", str(brand))
    plan = _deck([
        SlidePlan(layout="image", blocks=[
            ContentBlock(kind="image", title="x", body={"prompt": "p"}),
        ]),
    ])
    findings = brand_guardian_findings(plan)
    assert any("alt-text" in f for f in findings)


def test_narratologist_lenient_under_six_slides():
    plan = _deck([
        SlidePlan(layout="t", blocks=[ContentBlock(kind="title", title="x")]),
        SlidePlan(layout="b", blocks=[ContentBlock(kind="bullets", body={"items": ["a"]})]),
    ])
    assert narratologist_findings(plan) == []


def test_narratologist_flags_missing_resolution():
    slides = [
        SlidePlan(layout="title", blocks=[ContentBlock(kind="title", title="x")]),
        SlidePlan(layout="b", blocks=[ContentBlock(kind="bullets", body={"items": ["a"]})]),
        SlidePlan(layout="s", blocks=[ContentBlock(kind="scenario", body={"scenario": "s"})]),
        SlidePlan(layout="b", blocks=[ContentBlock(kind="bullets", body={"items": ["lowercase"]})]),
        SlidePlan(layout="b", blocks=[ContentBlock(kind="bullets", body={"items": ["nope"]})]),
        SlidePlan(layout="b", blocks=[ContentBlock(kind="bullets", body={"items": ["meh"]})]),
    ]
    findings = narratologist_findings(_deck(slides))
    assert any("resolution" in f for f in findings)


def test_narratologist_passes_with_action_checklist():
    slides = [
        SlidePlan(layout="title", blocks=[ContentBlock(kind="title", title="x")]),
        SlidePlan(layout="b", blocks=[ContentBlock(kind="bullets", body={"items": ["a"]})]),
        SlidePlan(layout="s", blocks=[ContentBlock(kind="scenario", body={"scenario": "s"})]),
        SlidePlan(layout="b", blocks=[ContentBlock(kind="bullets", body={"items": ["a"]})]),
        SlidePlan(layout="b", blocks=[ContentBlock(kind="bullets", body={"items": ["b"]})]),
        SlidePlan(layout="b", blocks=[ContentBlock(kind="bullets", body={"items": ["Decline cash gifts"]})]),
    ]
    assert narratologist_findings(_deck(slides)) == []
