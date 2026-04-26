"""Hermetic demo of the translator multi-agent pipeline.

Runs without any API keys by injecting FakeLLMs that play out a
realistic translate → reflect → edit conversation.

Run from inside ``examples/translator_agent``::

    python demo.py
"""

from __future__ import annotations

import json

from translator.llm import FakeLLM
from translator.personas_loader import load_persona
from translator.pipeline import translate_with

SOURCE = (
    "Time flies like an arrow; fruit flies like a banana. "
    "We shipped the LLM harness on Friday and the team is over the moon."
)

DRAFT = (
    "시간은 화살처럼 날아가고, 과일파리는 바나나를 좋아한다. "
    "우리는 금요일에 LLM 하니스를 출시했고 팀은 매우 기쁘다."
)

CRITIQUE = json.dumps(
    [
        {
            "issue": "'fruit flies like a banana'를 직역해서 의미가 어색함",
            "suggestion": "관용구임을 살려 '과일파리는 바나나를 좋아한다' 정도로 두되 존댓말 통일",
            "severity": "med",
        },
        {
            "issue": "존댓말과 반말이 섞임 ('날아가고' / '출시했고' 반말체)",
            "suggestion": "전체를 존댓말로 통일하세요 (해요체 또는 합쇼체)",
            "severity": "high",
        },
        {
            "issue": "'over the moon' 직역이 평이함",
            "suggestion": "'매우 기뻐하고 있습니다' 또는 '뛸 듯이 기뻐했습니다'로 자연스럽게",
            "severity": "low",
        },
    ],
    ensure_ascii=False,
)

FINAL = (
    "시간은 화살처럼 날아가고, 과일파리는 바나나를 좋아합니다. "
    "저희는 금요일에 LLM 하니스를 출시했고, 팀은 뛸 듯이 기뻐했습니다."
)


def main() -> None:
    t_p = load_persona("translator")
    r_p = load_persona("reflector")
    e_p = load_persona("editor")

    shared = FakeLLM(
        "shared",
        responses={
            "Translate the following English text": DRAFT,
            "Review this draft Korean translation": CRITIQUE,
            "Produce the final Korean translation": FINAL,
        },
        default="UNROUTED",
    )
    llms = {t_p.model: shared, r_p.model: shared, e_p.model: shared}

    trace = translate_with(SOURCE, llms)

    print("=== source (en) ===")
    print(trace.source_en)
    print("\n=== draft (ko) — translator ===")
    print(trace.draft_ko)
    print("\n=== findings — reflector ===")
    for f in trace.findings:
        print(f"  [{f.severity}] {f.issue} → {f.suggestion}")
    print(f"\n=== final (ko) — editor (edited={trace.edited}) ===")
    print(trace.final_ko)


if __name__ == "__main__":
    main()
