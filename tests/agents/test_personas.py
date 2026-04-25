from autoresearch.agents import load_persona


def test_load_persona_researcher():
    p = load_persona("researcher")
    assert p.role.lower().startswith("compliance")
    assert "web_search" in p.allowed_tools
