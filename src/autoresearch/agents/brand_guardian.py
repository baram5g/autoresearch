"""Brand Guardian — deterministic, optional brand-compliance reviewer.

Loads ``brand.yaml`` from the configured path (env ``BRAND_YAML`` or
``./brand.yaml``) when present, and emits findings against the deck plan.
When no ``brand.yaml`` is reachable the function returns ``[]`` — i.e. the
reviewer is a no-op for projects that haven't opted in.

Recognised keys in ``brand.yaml``::

    banned_phrases: ["world-class", "revolutionary"]
    voice:
      forbid_hedge: ["maybe", "kind of"]
    image_alt_required: true

Findings prefixed ``LOOP:`` indicate that a designer rerun could fix them
(e.g. wording in a slide title) — others are informational.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from ..state import DeckPlan


def _resolve_brand_path(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.exists() else None
    env = os.environ.get("BRAND_YAML")
    if env:
        p = Path(env)
        return p if p.exists() else None
    cwd = Path.cwd() / "brand.yaml"
    return cwd if cwd.exists() else None


def _slide_text(plan: DeckPlan) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for i, s in enumerate(plan.slides):
        chunks: list[str] = []
        for b in s.blocks:
            if b.title:
                chunks.append(b.title)
            body = b.body or {}
            if isinstance(body, dict):
                for v in body.values():
                    if isinstance(v, str):
                        chunks.append(v)
                    elif isinstance(v, list):
                        chunks.extend(x for x in v if isinstance(x, str))
        if s.speaker_notes:
            chunks.append(s.speaker_notes)
        out.append((i, " ".join(chunks)))
    return out


def brand_guardian_findings(
    plan: DeckPlan, brand_yaml_path: Path | None = None
) -> list[str]:
    path = _resolve_brand_path(brand_yaml_path)
    if path is None:
        return []
    try:
        cfg: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []

    findings: list[str] = []
    banned = [str(p).lower() for p in cfg.get("banned_phrases", []) or []]
    hedges = [
        str(p).lower()
        for p in (cfg.get("voice", {}) or {}).get("forbid_hedge", []) or []
    ]
    alt_required = bool(cfg.get("image_alt_required", False))

    for i, text in _slide_text(plan):
        low = text.lower()
        for phrase in banned:
            if phrase and phrase in low:
                findings.append(
                    f"LOOP: slide {i} contains banned phrase '{phrase}'."
                )
        for hedge in hedges:
            if hedge and hedge in low:
                findings.append(
                    f"LOOP: slide {i} uses hedge phrase '{hedge}'; tighten the voice."
                )

    if alt_required:
        for i, s in enumerate(plan.slides):
            for b in s.blocks:
                if b.kind == "image":
                    body = b.body or {}
                    if not (isinstance(body, dict) and str(body.get("alt", "")).strip()):
                        findings.append(
                            f"LOOP: slide {i} image block is missing alt-text."
                        )
    return findings
