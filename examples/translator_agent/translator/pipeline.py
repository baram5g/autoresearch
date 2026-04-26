"""Pipeline: translate → reflect → (maybe) edit.

The pipeline returns a ``Trace`` object so callers can inspect every
intermediate step — useful for debugging and for an autoresearch-style
quality loop later.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .agents import EditorAgent, Finding, ReflectorAgent, TranslatorAgent
from .llm import LLM, make_llm
from .personas_loader import load_persona


@dataclass
class Trace:
    source_en: str
    draft_ko: str
    findings: list[Finding] = field(default_factory=list)
    final_ko: str = ""
    edited: bool = False

    def actionable(self) -> list[Finding]:
        return [f for f in self.findings if f.severity in ("high", "med")]


def build_agents(
    llm_factory=make_llm,
) -> tuple[TranslatorAgent, ReflectorAgent, EditorAgent]:
    """Instantiate the three agents from their persona files.

    ``llm_factory`` exists so tests can inject ``FakeLLM`` keyed by model
    id without going through OpenAI/Anthropic.
    """
    t_p = load_persona("translator")
    r_p = load_persona("reflector")
    e_p = load_persona("editor")
    return (
        TranslatorAgent(t_p, llm_factory(t_p.model)),
        ReflectorAgent(r_p, llm_factory(r_p.model)),
        EditorAgent(e_p, llm_factory(e_p.model)),
    )


def translate(
    source_en: str,
    *,
    llm_factory=make_llm,
    skip_reflection: bool = False,
) -> Trace:
    translator, reflector, editor = build_agents(llm_factory)
    draft = translator.run(source_en)
    trace = Trace(source_en=source_en, draft_ko=draft, final_ko=draft)
    if skip_reflection:
        return trace
    trace.findings = reflector.run(source_en, draft)
    actionable = trace.actionable()
    if not actionable:
        return trace
    trace.final_ko = editor.run(source_en, draft, actionable)
    trace.edited = True
    return trace


def translate_with(
    source_en: str, llms: dict[str, LLM], *, skip_reflection: bool = False
) -> Trace:
    """Convenience: pass a ``{model_id: LLM}`` mapping directly."""
    return translate(
        source_en,
        llm_factory=lambda model: llms[model],
        skip_reflection=skip_reflection,
    )
