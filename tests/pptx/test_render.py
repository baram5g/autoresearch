from autoresearch.pptx import render_deck
from autoresearch.state import ContentBlock, DeckPlan, SlidePlan


def test_render_deck_writes_pptx(tmp_path):
    plan = DeckPlan(
        topic="Anti-bribery",
        audience="partners",
        slides=[
            SlidePlan(
                layout="title",
                blocks=[
                    ContentBlock(kind="title", title="Anti-bribery 101"),
                    ContentBlock(kind="bullets", body={"items": ["Define bribery", "Red flags"]}),
                ],
            ),
            SlidePlan(
                layout="quiz",
                blocks=[
                    ContentBlock(
                        kind="quiz",
                        body={
                            "question": "Which is a red flag?",
                            "options": ["Cash gift", "Signed NDA", "Audit log"],
                        },
                    )
                ],
            ),
        ],
    )
    out = tmp_path / "deck.pptx"
    result = render_deck(plan, out)
    assert result.exists() and result.stat().st_size > 0
