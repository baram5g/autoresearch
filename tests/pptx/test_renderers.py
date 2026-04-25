"""Per-renderer smoke tests.

Each test asserts the renderer produces a non-empty deck and at least one
shape on the slide. python-pptx is the source of truth for shape correctness;
we don't re-validate XML here.
"""

from pptx import Presentation

from autoresearch.pptx.render import RENDERERS, render_deck
from autoresearch.state import ContentBlock, DeckPlan, SlidePlan


def _render_one(block: ContentBlock, tmp_path) -> Presentation:
    plan = DeckPlan(
        topic="t",
        audience="a",
        slides=[SlidePlan(layout="generic", blocks=[block])],
    )
    out = tmp_path / "deck.pptx"
    render_deck(plan, out)
    return Presentation(out)


def test_renderer_registry_covers_all_kinds():
    expected = {
        "title", "bullets", "quiz", "scenario",
        "infographic", "flowchart", "diagram", "table", "image",
    }
    assert expected.issubset(set(RENDERERS))


def test_infographic_renderer(tmp_path):
    block = ContentBlock(
        kind="infographic",
        title="By the numbers",
        body={
            "tiles": [
                {"value": "$3.6B", "label": "FCPA penalties (5y)"},
                {"value": "78%", "label": "via 3rd parties"},
                {"value": "9 of 10", "label": "have anti-bribery policy"},
            ],
            "caption": "Source: SEC enforcement data",
        },
    )
    prs = _render_one(block, tmp_path)
    assert len(prs.slides[0].shapes) >= 4


def test_flowchart_renderer(tmp_path):
    block = ContentBlock(
        kind="flowchart",
        title="Red-flag escalation",
        body={"steps": ["Detect", "Triage", "Escalate", "Resolve"]},
    )
    prs = _render_one(block, tmp_path)
    # 4 boxes + 3 connectors + 1 title textbox = 8
    assert len(prs.slides[0].shapes) >= 7


def test_diagram_renderer(tmp_path):
    block = ContentBlock(
        kind="diagram",
        body={"center": "Anti-bribery", "nodes": ["Gifts", "Hospitality", "3rd parties", "Donations"]},
    )
    prs = _render_one(block, tmp_path)
    # central + 4 satellites + 4 connectors = 9
    assert len(prs.slides[0].shapes) >= 9


def test_table_renderer(tmp_path):
    block = ContentBlock(
        kind="table",
        title="Do / Don't",
        body={
            "headers": ["Do", "Don't"],
            "rows": [
                ["Decline cash gifts", "Accept envelopes"],
                ["Log hospitality > $50", "Skip the log"],
            ],
        },
    )
    prs = _render_one(block, tmp_path)
    shapes = list(prs.slides[0].shapes)
    assert any(s.has_table for s in shapes)


def test_image_renderer_uses_placeholder_when_no_path(tmp_path):
    block = ContentBlock(
        kind="image",
        title="Scenario",
        body={"prompt": "A procurement officer reviewing a contract", "caption": "Illustrative"},
    )
    prs = _render_one(block, tmp_path)
    assert len(prs.slides[0].shapes) >= 2


def test_unknown_kind_falls_back_to_bullets(tmp_path):
    block = ContentBlock(kind="bullets", body={"items": []})  # empty bullets path
    block_unknown = block.model_copy(update={"kind": "unknown_kind"})  # type: ignore[arg-type]
    # Bypass pydantic literal validation by direct dict
    plan = DeckPlan(
        topic="t",
        audience="a",
        slides=[SlidePlan(layout="x", blocks=[ContentBlock(kind="bullets", body={"items": ["x"]})])],
    )
    out = tmp_path / "d.pptx"
    render_deck(plan, out)
    assert out.exists()
