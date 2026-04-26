"""Persona loader — reuses the autoresearch frontmatter+body pattern."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PERSONAS_DIR = Path(__file__).parent / "personas"


@dataclass(frozen=True)
class Persona:
    name: str
    role: str
    model: str
    system_prompt: str


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = yaml.safe_load(text[3:end]) or {}
    body = text[end + 4 :].lstrip("\n")
    return fm, body


def load_persona(name: str) -> Persona:
    path = PERSONAS_DIR / f"{name}.md"
    fm, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    return Persona(
        name=name,
        role=str(fm.get("role", name)),
        model=str(fm["model"]),
        system_prompt=body,
    )
