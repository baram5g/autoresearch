import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from translator.llm import FakeLLM  # noqa: E402
from translator.personas_loader import load_persona  # noqa: E402
from translator.pipeline import translate_with  # noqa: E402


def _make_llms(translator_out: str, reflector_out: str, editor_out: str):
    """Build a {model_id: FakeLLM} mapping that works even when two agents
    share the same model id — by routing on prompt content, not model.
    """
    t_p = load_persona("translator")
    r_p = load_persona("reflector")
    e_p = load_persona("editor")
    shared = FakeLLM(
        "shared",
        responses={
            "Translate the following English text": translator_out,
            "Review this draft Korean translation": reflector_out,
            "Produce the final Korean translation": editor_out,
        },
        default="UNROUTED",
    )
    return {t_p.model: shared, r_p.model: shared, e_p.model: shared}


def test_no_findings_skips_editor():
    llms = _make_llms("초안 번역", "[]", "WILL_NOT_BE_CALLED")
    trace = translate_with("Hello.", llms)
    assert trace.draft_ko == "초안 번역"
    assert trace.findings == []
    assert trace.final_ko == "초안 번역"
    assert trace.edited is False


def test_low_only_findings_skip_editor():
    critique = json.dumps([{"issue": "x", "suggestion": "y", "severity": "low"}])
    llms = _make_llms("초안", critique, "WILL_NOT_BE_CALLED")
    trace = translate_with("Hi.", llms)
    assert len(trace.findings) == 1
    assert trace.actionable() == []
    assert trace.edited is False
    assert trace.final_ko == "초안"


def test_high_finding_invokes_editor():
    critique = json.dumps(
        [{"issue": "오역", "suggestion": "수정안", "severity": "high"}]
    )
    llms = _make_llms("초안", critique, "최종본")
    trace = translate_with("Hello.", llms)
    assert trace.edited is True
    assert trace.final_ko == "최종본"


def test_skip_reflection_returns_draft():
    llms = _make_llms("초안", "WILL_NOT_BE_CALLED", "WILL_NOT_BE_CALLED")
    trace = translate_with("Hello.", llms, skip_reflection=True)
    assert trace.final_ko == "초안"
    assert trace.findings == []
    assert trace.edited is False


def test_reflector_handles_code_fenced_json():
    fenced = "```json\n[{\"issue\":\"i\",\"suggestion\":\"s\",\"severity\":\"med\"}]\n```"
    llms = _make_llms("draft", fenced, "final")
    trace = translate_with("x", llms)
    assert len(trace.findings) == 1
    assert trace.findings[0].severity == "med"
    assert trace.edited is True


def test_reflector_tolerates_garbage_returns_no_findings():
    llms = _make_llms("draft", "this is not json at all", "final")
    trace = translate_with("x", llms)
    assert trace.findings == []
    assert trace.edited is False
    assert trace.final_ko == "draft"


def test_personas_load_with_required_fields():
    for name in ("translator", "reflector", "editor"):
        p = load_persona(name)
        assert p.model
        assert p.system_prompt.strip()
        assert p.role
