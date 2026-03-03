"""Tests for the persona system."""

import pytest

from lol_commentary.live.persona import (
    ExcitementModifiers,
    Persona,
    PersonaRole,
    PERSONAS,
    get_persona,
    get_fill_prompt,
)


class TestPersona:
    def test_default_kenshi_exists(self):
        kenshi = get_persona("kenshi")
        assert kenshi.id == "kenshi"
        assert kenshi.name == "ケンシ"
        assert kenshi.role == PersonaRole.SOLO

    def test_kenshi_has_system_prompt(self):
        kenshi = get_persona("kenshi")
        assert "ケンシ" in kenshi.system_prompt
        assert "解説スタイル" in kenshi.system_prompt

    def test_get_persona_unknown_raises(self):
        with pytest.raises(KeyError):
            get_persona("nonexistent")

    def test_excitement_mapping_low(self):
        kenshi = get_persona("kenshi")
        assert kenshi.get_excitement(0.0) == "low"
        assert kenshi.get_excitement(0.2) == "low"
        assert kenshi.get_excitement(0.29) == "low"

    def test_excitement_mapping_mid(self):
        kenshi = get_persona("kenshi")
        assert kenshi.get_excitement(0.3) == "mid"
        assert kenshi.get_excitement(0.5) == "mid"
        assert kenshi.get_excitement(0.59) == "mid"

    def test_excitement_mapping_high(self):
        kenshi = get_persona("kenshi")
        assert kenshi.get_excitement(0.6) == "high"
        assert kenshi.get_excitement(0.7) == "high"
        assert kenshi.get_excitement(0.79) == "high"

    def test_excitement_mapping_hype(self):
        kenshi = get_persona("kenshi")
        assert kenshi.get_excitement(0.8) == "hype"
        assert kenshi.get_excitement(1.0) == "hype"

    def test_excitement_modifier_returns_string(self):
        kenshi = get_persona("kenshi")
        modifier = kenshi.get_excitement_modifier(0.9)
        assert isinstance(modifier, str)
        assert len(modifier) > 0

    def test_personas_registry_not_empty(self):
        assert len(PERSONAS) > 0
        assert "kenshi" in PERSONAS

    def test_get_fill_prompt(self):
        prompt = get_fill_prompt("kenshi")
        assert isinstance(prompt, str)
        assert "ケンシ" in prompt

    def test_get_fill_prompt_unknown_returns_default(self):
        prompt = get_fill_prompt("nonexistent")
        assert isinstance(prompt, str)

    def test_custom_persona(self):
        persona = Persona(
            id="test",
            name="テスト",
            role=PersonaRole.ANALYST,
            avatar="test.png",
            system_prompt="テスト用プロンプト",
        )
        assert persona.id == "test"
        assert persona.role == PersonaRole.ANALYST
        assert persona.get_excitement(0.5) == "mid"

    def test_excitement_modifiers_dataclass(self):
        mods = ExcitementModifiers()
        assert hasattr(mods, "low")
        assert hasattr(mods, "mid")
        assert hasattr(mods, "high")
        assert hasattr(mods, "hype")

    def test_persona_is_frozen(self):
        kenshi = get_persona("kenshi")
        with pytest.raises(AttributeError):
            kenshi.name = "changed"
