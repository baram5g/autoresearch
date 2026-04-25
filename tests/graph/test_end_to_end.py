"""End-to-end pipeline test with scripted FakeLLMClient.

Demonstrates: persona-bound LLMAgents → real graph topology → render → eval
score, all hermetically (no network, no real LLM).
"""

from __future__ import annotations

from autoresearch.agents.designer import DesignerOutput
from autoresearch.agents.qa import QAOutput
from autoresearch.agents.researcher import ResearcherOutput
from autoresearch.agents.visual_designer import ImagePrompt, VisualDesignerOutput
from autoresearch.evals import score_deck
from autoresearch.graph import build_pipeline
from autoresearch.llm import FakeLLMClient
from autoresearch.state import ContentBlock, SlidePlan
from autoresearch.tools.protocols import FakeWebSearch, WebSearchHit


def _good_deck_slides() -> list[SlidePlan]:
    return [
        SlidePlan(layout="title", blocks=[
            ContentBlock(kind="title", title="Anti-bribery for procurement partners"),
        ]),
        SlidePlan(layout="bullets", blocks=[
            ContentBlock(kind="bullets", title="Learning objectives", body={
                "items": ["Identify red flags", "Apply the gift policy", "Escalate concerns"],
            }, citations=["[N1]"]),
        ]),
        SlidePlan(layout="infographic", blocks=[
            ContentBlock(kind="infographic", title="By the numbers", body={
                "tiles": [
                    {"value": "$3.6B", "label": "FCPA penalties (5y)"},
                    {"value": "78%", "label": "via 3rd parties"},
                    {"value": "9/10", "label": "have a policy"},
                ],
                "caption": "Sources [N1][N2]",
            }, citations=["[N1]", "[N2]"]),
        ]),
        SlidePlan(layout="flowchart", blocks=[
            ContentBlock(kind="flowchart", title="Escalation",
                         body={"steps": ["Detect", "Triage", "Escalate", "Resolve"]},
                         citations=["[N3]"]),
        ]),
        SlidePlan(layout="table", blocks=[
            ContentBlock(kind="table", title="Do / Don't", body={
                "headers": ["Do", "Don't"],
                "rows": [["Decline cash", "Accept envelopes"], ["Log gifts > $50", "Skip the log"]],
            }, citations=["[N4]"]),
        ]),
        SlidePlan(layout="quiz", blocks=[
            ContentBlock(kind="quiz", title="Check", body={
                "question": "Which is a red flag?",
                "options": ["Cash gift", "Signed NDA", "Audit log"],
                "answer": "A",
            }),
        ]),
        SlidePlan(layout="scenario", blocks=[
            ContentBlock(kind="scenario", title="Apply",
                         body={"scenario": "A vendor offers a vacation.",
                               "question": "What do you do?",
                               "choices": ["Accept", "Decline + log", "Ignore"],
                               "debrief": "Decline and log."},
                         citations=["[N4]"]),
        ]),
        SlidePlan(layout="image", blocks=[
            ContentBlock(kind="image", title="Real case",
                         body={"prompt": "procurement officer reviewing contract"}),
        ]),
        SlidePlan(layout="diagram", blocks=[
            ContentBlock(kind="diagram", title="Risk areas",
                         body={"center": "Anti-bribery",
                               "nodes": ["Gifts", "Hospitality", "3rd parties", "Donations"]}),
        ]),
    ]


def test_pipeline_end_to_end_produces_scored_deck(tmp_path):
    client = FakeLLMClient()
    client.script("researcher", [
        ResearcherOutput(notes=[
            "[N1] FCPA penalties exceeded $3.6B over 5y (https://example.com/sec)",
            "[N2] 78% of bribery cases route via 3rd parties (https://example.com/oecd)",
            "[N3] Standard escalation: detect→triage→escalate→resolve (https://example.com/iso)",
            "[N4] Gift policies typically cap at $50 unlogged (https://example.com/policy)",
        ]),
    ])
    client.script("instructional_designer", [
        DesignerOutput(
            learning_objectives=[
                "Identify bribery red flags",
                "Apply the gift policy",
                "Escalate concerns",
            ],
            slides=_good_deck_slides(),
        ),
    ])
    client.script("visual_designer", [
        VisualDesignerOutput(image_prompts=[
            ImagePrompt(slide_index=7, prompt="A procurement officer reviewing a contract"),
        ]),
    ])
    client.script("qa_reviewer", [
        QAOutput(findings=["Looks good."]),
    ])

    search = FakeWebSearch({
        "Anti-bribery procurement compliance training latest trends": [
            WebSearchHit("FCPA stats", "https://example.com/sec", "5y enforcement"),
        ]
    })

    out = tmp_path / "deck.pptx"
    graph = build_pipeline(client=client, out_path=out, search=search)
    final = graph.invoke({"topic": "Anti-bribery procurement", "audience": "partners"})

    assert final["output_path"] == str(out)
    assert out.exists() and out.stat().st_size > 0
    score = score_deck(final["deck_plan"])
    assert score.total > 0.7
    assert score.scenario_presence == 1.0
    assert score.content_variety > 0.7
