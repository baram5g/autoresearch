"""Three agents: Translator, Reflector, Editor.

Each agent owns a ``Persona`` (system prompt + model id) and an ``LLM``
client. The pipeline composes them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .llm import LLM
from .personas_loader import Persona


@dataclass
class Finding:
    issue: str
    suggestion: str
    severity: str  # "high" | "med" | "low"

    @classmethod
    def from_dict(cls, d: dict) -> Finding:
        return cls(
            issue=str(d.get("issue", "")),
            suggestion=str(d.get("suggestion", "")),
            severity=str(d.get("severity", "low")).lower(),
        )


class Agent:
    def __init__(self, persona: Persona, llm: LLM) -> None:
        self.persona = persona
        self.llm = llm

    def _call(self, user_prompt: str) -> str:
        return self.llm.call(self.persona.system_prompt, user_prompt)


class TranslatorAgent(Agent):
    def run(self, source_en: str) -> str:
        return self._call(
            f"Translate the following English text to Korean.\n\n"
            f"<source>\n{source_en}\n</source>"
        ).strip()


class ReflectorAgent(Agent):
    def run(self, source_en: str, draft_ko: str) -> list[Finding]:
        raw = self._call(
            "Review this draft Korean translation against the English source. "
            "Return a JSON array of findings as specified in your instructions.\n\n"
            f"<source language=\"en\">\n{source_en}\n</source>\n\n"
            f"<draft language=\"ko\">\n{draft_ko}\n</draft>"
        ).strip()
        return _parse_findings(raw)


class EditorAgent(Agent):
    def run(
        self, source_en: str, draft_ko: str, findings: list[Finding]
    ) -> str:
        findings_json = json.dumps(
            [f.__dict__ for f in findings], ensure_ascii=False, indent=2
        )
        return self._call(
            "Produce the final Korean translation that addresses every finding.\n\n"
            f"<source language=\"en\">\n{source_en}\n</source>\n\n"
            f"<draft language=\"ko\">\n{draft_ko}\n</draft>\n\n"
            f"<findings>\n{findings_json}\n</findings>"
        ).strip()


def _parse_findings(raw: str) -> list[Finding]:
    """Parse the reviewer output. Tolerate code fences and surrounding prose."""
    text = raw.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fences
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    # Find the first '[' and the last ']' as a fallback for chatty models.
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        items = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(items, list):
        return []
    return [Finding.from_dict(d) for d in items if isinstance(d, dict)]
