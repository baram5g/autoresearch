"""Seeded fake clients for demos and the case study.

Provides ``baseline_client`` (sparse, 1 slide, no variety — what a naive
single-prompt pipeline produces) and ``upgraded_client`` (rich, 9 slides,
mixed kinds, citations — what the harness-upgraded pipeline produces).

Both use the same FakeLLMClient + scripted Pydantic responses so the
case-study runner is hermetic and deterministic.
"""

from __future__ import annotations

from autoresearch.agents.designer import DesignerOutput
from autoresearch.agents.qa import QAOutput
from autoresearch.agents.researcher import ResearcherOutput
from autoresearch.agents.visual_designer import ImagePrompt, VisualDesignerOutput
from autoresearch.llm import FakeLLMClient
from autoresearch.state import ContentBlock, SlidePlan
from autoresearch.tools.protocols import FakeWebSearch, WebSearchHit


def baseline_client(topic: str, audience: str) -> tuple[FakeLLMClient, FakeWebSearch]:
    """Naive pre-harness output: one slide, bullets only, no citations."""
    client = FakeLLMClient()
    client.script(
        "researcher",
        [ResearcherOutput(notes=[f"Generic notes about {topic}."])],
    )
    client.script(
        "instructional_designer",
        [
            DesignerOutput(
                learning_objectives=[],
                slides=[
                    SlidePlan(
                        layout="bullets",
                        blocks=[
                            ContentBlock(kind="title", title=f"{topic}"),
                            ContentBlock(
                                kind="bullets",
                                body={
                                    "items": [
                                        f"Overview of {topic}",
                                        "Key risks",
                                        "What to do",
                                    ]
                                },
                            ),
                        ],
                    )
                ],
            )
        ],
    )
    client.script("visual_designer", [VisualDesignerOutput(image_prompts=[])])
    client.script("qa_reviewer", [QAOutput(findings=[])])  # never reached: structural floor
    # Plus retries for any LOOP loops the structural floor will trigger.
    for _ in range(5):
        client.script(
            "instructional_designer",
            [
                DesignerOutput(
                    learning_objectives=[],
                    slides=[
                        SlidePlan(
                            layout="bullets",
                            blocks=[
                                ContentBlock(kind="title", title=f"{topic}"),
                                ContentBlock(
                                    kind="bullets",
                                    body={"items": [f"Overview of {topic}"]},
                                ),
                            ],
                        )
                    ],
                )
            ],
        )
        client.script("visual_designer", [VisualDesignerOutput(image_prompts=[])])
    search = FakeWebSearch()
    return client, search


def upgraded_client(topic: str, audience: str) -> tuple[FakeLLMClient, FakeWebSearch]:
    """Harness-upgraded output: 9 slides, mixed kinds, citations, learning objectives."""
    client = FakeLLMClient()
    client.script(
        "researcher",
        [
            ResearcherOutput(
                notes=[
                    f"[N1] Regulatory framing for {topic} in 2025 (https://example.com/reg).",
                    "[N2] 78% of related cases route via 3rd parties (https://example.com/oecd).",
                    "[N3] Standard escalation flow: detect → triage → escalate → resolve (https://example.com/iso).",
                    f"[N4] Audience-specific risks for {audience} include gifts, hospitality, donations (https://example.com/policy).",
                    "[N5] $3.6B in US enforcement penalties over the last 5 years (https://example.com/sec).",
                ]
            )
        ],
    )
    objectives = [
        f"Identify red flags relevant to {topic}",
        f"Apply the {audience} gift and hospitality policy",
        "Escalate concerns through the correct channel",
    ]
    slides = [
        SlidePlan(layout="title", blocks=[
            ContentBlock(kind="title", title=f"{topic} for {audience}"),
        ]),
        SlidePlan(layout="bullets", blocks=[
            ContentBlock(
                kind="bullets",
                title="Learning objectives",
                body={"items": objectives},
                citations=["[N1]"],
            ),
        ], speaker_notes=" ".join(objectives)),
        SlidePlan(layout="infographic", blocks=[
            ContentBlock(
                kind="infographic",
                title="By the numbers",
                body={
                    "tiles": [
                        {"value": "$3.6B", "label": "5y enforcement penalties"},
                        {"value": "78%", "label": "via 3rd parties"},
                        {"value": "9 / 10", "label": "have a written policy"},
                    ],
                    "caption": "Sources: [N5] [N2]",
                },
                citations=["[N5]", "[N2]"],
            ),
        ]),
        SlidePlan(layout="flowchart", blocks=[
            ContentBlock(
                kind="flowchart",
                title="Escalation workflow",
                body={"steps": ["Detect", "Triage", "Escalate", "Resolve"]},
                citations=["[N3]"],
            ),
        ]),
        SlidePlan(layout="table", blocks=[
            ContentBlock(
                kind="table",
                title="Do / Don't",
                body={
                    "headers": ["Do", "Don't"],
                    "rows": [
                        ["Decline cash gifts", "Accept envelopes"],
                        ["Log hospitality > $50", "Skip the log"],
                        ["Ask compliance early", "Improvise on grey areas"],
                    ],
                },
                citations=["[N4]"],
            ),
        ]),
        SlidePlan(layout="quiz", blocks=[
            ContentBlock(
                kind="quiz",
                title="Check your understanding",
                body={
                    "question": "Which of these is a red flag?",
                    "options": [
                        "An unusually high commission to a local agent",
                        "A signed master services agreement",
                        "An audit log of approved gifts",
                    ],
                    "answer": "A",
                },
                citations=["[N4]"],
            ),
        ]),
        SlidePlan(layout="scenario", blocks=[
            ContentBlock(
                kind="scenario",
                title="Apply it",
                body={
                    "scenario": (
                        f"A long-standing {audience.split()[0] if audience else 'partner'} "
                        "offers a fully paid family trip to celebrate a contract renewal."
                    ),
                    "question": "What do you do?",
                    "choices": [
                        "Accept; it's a relationship-builder.",
                        "Decline and log the offer.",
                        "Escalate to compliance.",
                    ],
                    "debrief": "Decline and log; consult compliance if pressured.",
                },
                citations=["[N4]"],
            ),
        ], speaker_notes="Apply the gift policy in a realistic scenario."),
        SlidePlan(layout="image", blocks=[
            ContentBlock(
                kind="image",
                title="A real situation",
                body={"prompt": ""},
                citations=[],
            ),
        ]),
        SlidePlan(layout="diagram", blocks=[
            ContentBlock(
                kind="diagram",
                title="Risk surface",
                body={
                    "center": topic.split()[0] if topic else "Risk",
                    "nodes": ["Gifts", "Hospitality", "3rd parties", "Donations"],
                },
                citations=["[N4]"],
            ),
        ]),
    ]
    client.script("instructional_designer", [
        DesignerOutput(learning_objectives=objectives, slides=slides),
    ])
    client.script("visual_designer", [
        VisualDesignerOutput(image_prompts=[
            ImagePrompt(slide_index=7, prompt=f"A {audience} reviewing a contract while declining a gift, modern office, neutral palette"),
        ]),
    ])
    client.script("qa_reviewer", [QAOutput(findings=["Citations resolve; pedagogy sound."])])

    search = FakeWebSearch({
        f"{topic} compliance training latest trends": [
            WebSearchHit("Trends 2025", "https://example.com/trends", "Microlearning, scenario-first"),
            WebSearchHit("OECD report", "https://example.com/oecd", "78% via 3rd parties"),
        ]
    })
    return client, search
