"""Narratologist — deterministic structural reviewer for the deck arc.

Checks (lenient — only fire when the fix is unambiguous):

- First slide is a ``title`` slide.
- For decks with ≥ 6 slides: at least one ``scenario`` or ``quiz`` block in
  the middle third (the "confrontation" beat).
- For decks with ≥ 6 slides: the last 3 slides include either a ``quiz``
  block or a bullets block whose items look action-oriented (verb-leading).

Findings are prefixed ``LOOP:`` because each issue is a designer-fixable
narrative defect.
"""

from __future__ import annotations

import re

from ..state import DeckPlan

_VERB_LEADING = re.compile(r"^[A-Z][a-z]{1,11}\b")


def _has_action_bullet(plan: DeckPlan, indices: range) -> bool:
    for i in indices:
        if i < 0 or i >= len(plan.slides):
            continue
        for b in plan.slides[i].blocks:
            if b.kind == "bullets":
                items = (b.body or {}).get("items", []) or []
                for it in items:
                    if isinstance(it, str) and _VERB_LEADING.match(it.strip()):
                        return True
    return False


def _has_kind(plan: DeckPlan, indices: range, kinds: set[str]) -> bool:
    for i in indices:
        if i < 0 or i >= len(plan.slides):
            continue
        if any(b.kind in kinds for b in plan.slides[i].blocks):
            return True
    return False


def narratologist_findings(plan: DeckPlan) -> list[str]:
    findings: list[str] = []
    n = len(plan.slides)
    if n == 0:
        return findings

    first_kinds = {b.kind for b in plan.slides[0].blocks}
    if "title" not in first_kinds:
        findings.append("LOOP: slide 0 is not a title slide; open with a hook.")

    if n < 6:
        return findings

    mid_lo, mid_hi = n // 3, (2 * n) // 3
    if not _has_kind(plan, range(mid_lo, mid_hi), {"scenario", "quiz"}):
        findings.append(
            "LOOP: middle third lacks scenario/quiz; confrontation beat is missing."
        )

    end = range(n - 3, n)
    if not (_has_kind(plan, end, {"quiz"}) or _has_action_bullet(plan, end)):
        findings.append(
            "LOOP: last 3 slides lack a quiz or action checklist; resolution is weak."
        )
    return findings
