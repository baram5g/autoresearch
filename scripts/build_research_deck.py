"""Render a meta-deck that summarises the research and shows how the harness
improved generated PPT quality. Eats our own dogfood: uses the same DeckPlan /
ContentBlock schema and renderers as the production pipeline."""

from __future__ import annotations

from pathlib import Path

from autoresearch.evals import score_deck
from autoresearch.graph import build_pipeline
from autoresearch.pptx.render import render_deck
from autoresearch.seeds import baseline_client, upgraded_client
from autoresearch.state import ContentBlock, DeckPlan, SlidePlan


def _run(seed_fn, topic: str, audience: str, out: Path):
    client, search = seed_fn(topic, audience)
    graph = build_pipeline(client=client, out_path=out, search=search)
    final = graph.invoke({"topic": topic, "audience": audience})
    return score_deck(final["deck_plan"])


def _build_plan() -> DeckPlan:
    topic = "Anti-bribery for procurement partners"
    audience = "External procurement partners"
    tmp = Path("/tmp")
    b = _run(baseline_client, topic, audience, tmp / "_b.pptx")
    u = _run(upgraded_client, topic, audience, tmp / "_u.pptx")

    slides: list[SlidePlan] = []

    slides.append(
        SlidePlan(
            layout="title",
            blocks=[
                ContentBlock(
                    kind="title",
                    title="Agent Harnesses for Better Training Decks",
                ),
                ContentBlock(
                    kind="bullets",
                    body={
                        "items": [
                            "What an agent harness is and why it matters",
                            "How we restructured a single-LLM PPT generator",
                            "Measured quality gain: 0.06 → 0.98 on a 5-axis rubric",
                        ]
                    },
                ),
            ],
            speaker_notes="Frame: research synthesis + a concrete before/after.",
        )
    )

    slides.append(
        SlidePlan(
            layout="content",
            blocks=[
                ContentBlock(
                    kind="title", title="What is an agent harness?"
                ),
                ContentBlock(
                    kind="bullets",
                    body={
                        "items": [
                            "Orchestration layer around LLM calls: state, routing, tools, retries.",
                            "Splits one ambiguous prompt into role-bound personas with typed I/O.",
                            "Adds a critic/QA loop so weak output can be revised before render.",
                            "Makes runs observable: per-node tracing and structured eval.",
                        ]
                    },
                    citations=["docs/research/concepts.md"],
                ),
            ],
        )
    )

    slides.append(
        SlidePlan(
            layout="content",
            blocks=[
                ContentBlock(
                    kind="title",
                    title="Frameworks surveyed",
                ),
                ContentBlock(
                    kind="table",
                    body={
                        "headers": ["Framework", "Model", "Best for"],
                        "rows": [
                            ["LangGraph", "Typed state graph", "Deterministic loops + tracing"],
                            ["CrewAI", "Role-based crews", "Fast prototyping of teams"],
                            ["AutoGen", "Conversational agents", "Open-ended back-and-forth"],
                            ["Haystack/DSPy", "Pipelines/programs", "Retrieval, optimisation"],
                        ],
                    },
                    citations=["docs/research/frameworks.md"],
                ),
            ],
            speaker_notes="We picked LangGraph: typed state, explicit edges, easy to test.",
        )
    )

    slides.append(
        SlidePlan(
            layout="content",
            blocks=[
                ContentBlock(
                    kind="title", title="Personas in the pipeline"
                ),
                ContentBlock(
                    kind="diagram",
                    body={
                        "center": "GraphState",
                        "nodes": [
                            "Researcher",
                            "Designer",
                            "Visual Designer",
                            "QA Reviewer",
                            "Renderer",
                        ],
                    },
                    citations=["docs/research/personas.md"],
                ),
            ],
        )
    )

    slides.append(
        SlidePlan(
            layout="content",
            blocks=[
                ContentBlock(
                    kind="title", title="Orchestration: graph topology"
                ),
                ContentBlock(
                    kind="flowchart",
                    body={
                        "steps": [
                            "Researcher",
                            "Designer",
                            "Visual",
                            "QA",
                            "Render",
                        ]
                    },
                    citations=["docs/research/orchestration.md"],
                ),
                ContentBlock(
                    kind="bullets",
                    body={
                        "items": [
                            "QA emits 'LOOP:' findings → router re-enters Designer.",
                            "Capped at MAX_REVIEW_LOOPS=2 to bound cost.",
                            "qa_passes counter prevents infinite loops on stuck content.",
                        ]
                    },
                ),
            ],
        )
    )

    slides.append(
        SlidePlan(
            layout="content",
            blocks=[
                ContentBlock(
                    kind="title", title="Heuristics encoded as a structural gate"
                ),
                ContentBlock(
                    kind="bullets",
                    body={
                        "items": [
                            "≥ 8 slides per deck",
                            "Non-empty learning_objectives",
                            "≥ 1 quiz block per 5 slides",
                            "≥ 1 scenario block per deck",
                            "≥ 1 citation across the deck",
                        ]
                    },
                    citations=["docs/case_study/heuristics.md"],
                ),
            ],
            speaker_notes=(
                "The structural QA pass is deterministic and runs before any LLM "
                "audit, so the loop trigger doesn't depend on a stochastic critic."
            ),
        )
    )

    slides.append(
        SlidePlan(
            layout="content",
            blocks=[
                ContentBlock(
                    kind="title", title="Measured impact: rubric scores"
                ),
                ContentBlock(
                    kind="infographic",
                    body={
                        "tiles": [
                            {"value": f"{b.total:.2f}", "label": "Baseline"},
                            {"value": f"{u.total:.2f}", "label": "Harness"},
                            {
                                "value": f"+{(u.total - b.total):.2f}",
                                "label": "Delta",
                            },
                        ],
                        "caption": (
                            "5-axis rubric: structure, learning, variety, "
                            "citations, hazards."
                        ),
                    },
                    citations=["docs/case_study/results.md"],
                ),
            ],
        )
    )

    slides.append(
        SlidePlan(
            layout="content",
            blocks=[
                ContentBlock(
                    kind="title", title="Per-axis comparison"
                ),
                ContentBlock(
                    kind="table",
                    body={
                        "headers": ["Axis", "Baseline", "Harness"],
                        "rows": [
                            ["Objective coverage", f"{b.objective_coverage:.2f}", f"{u.objective_coverage:.2f}"],
                            ["Content variety", f"{b.content_variety:.2f}", f"{u.content_variety:.2f}"],
                            ["Citation density", f"{b.citation_density:.2f}", f"{u.citation_density:.2f}"],
                            ["Quiz density", f"{b.quiz_density:.2f}", f"{u.quiz_density:.2f}"],
                            ["Scenario presence", f"{b.scenario_presence:.2f}", f"{u.scenario_presence:.2f}"],
                            ["Total", f"{b.total:.2f}", f"{u.total:.2f}"],
                        ],
                    },
                    citations=["docs/case_study/results.md"],
                ),
            ],
        )
    )

    slides.append(
        SlidePlan(
            layout="content",
            blocks=[
                ContentBlock(
                    kind="title", title="Knowledge check"
                ),
                ContentBlock(
                    kind="quiz",
                    body={
                        "question": "Which finding causes the QA→Designer loop to fire?",
                        "options": [
                            "Any string in review_findings",
                            "Only findings starting with 'LOOP:'",
                            "Only findings starting with 'WARN:'",
                            "Whatever the LLM critic says, always",
                        ],
                        "answer": "B",
                    },
                ),
            ],
        )
    )

    slides.append(
        SlidePlan(
            layout="content",
            blocks=[
                ContentBlock(
                    kind="title", title="Scenario: a sparse first draft"
                ),
                ContentBlock(
                    kind="scenario",
                    body={
                        "scenario": (
                            "Designer emits a 3-slide deck with no quiz, no scenario, "
                            "and no citations."
                        ),
                        "question": "What does the harness do next?",
                        "choices": [
                            "Render it anyway and ship.",
                            "Structural QA emits LOOP findings; Designer re-runs with feedback.",
                            "Researcher is invoked again.",
                        ],
                        "debrief": (
                            "B. The structural pass alone is enough to trigger a "
                            "rerun — no LLM critic needed for floor-level violations."
                        ),
                    },
                ),
            ],
        )
    )

    slides.append(
        SlidePlan(
            layout="content",
            blocks=[
                ContentBlock(
                    kind="title", title="Takeaways"
                ),
                ContentBlock(
                    kind="bullets",
                    body={
                        "items": [
                            "Decompose by persona, not by prompt section.",
                            "Make heuristics a deterministic gate, not vibes in a prompt.",
                            "Score every run — regressions are silent without a rubric.",
                            "Keep the critic loop bounded; cost grows linearly with passes.",
                            "Seed fakes for hermetic case studies; reserve real LLM for prod.",
                        ]
                    },
                    citations=[
                        "docs/research/building_a_harness.md",
                        "docs/research/using_a_harness.md",
                    ],
                ),
            ],
        )
    )

    return DeckPlan(
        topic="Agent harnesses for partner-training PPT generation",
        audience="Engineering + L&D stakeholders",
        learning_objectives=[
            "Define an agent harness in your own words",
            "Identify the four personas in our pipeline and what each owns",
            "Explain how QA findings drive a bounded design loop",
            "Read the 5-axis rubric and interpret a score delta",
        ],
        slides=slides,
    )


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "examples" / "harness_research_overview.pptx"
    plan = _build_plan()
    score = score_deck(plan)
    render_deck(plan, out)
    print(f"Wrote {out} ({out.stat().st_size} bytes)")
    print(f"Self-rubric: total={score.total:.2f}  ({score})")


if __name__ == "__main__":
    main()
