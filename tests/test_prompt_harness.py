"""Tests for SFT Production System Prompt & Uzbek Asymmetric User Style Harness."""

import pytest
from ufl_bench.utils.normalization import (
    SYSTEM_PROMPT_UZ_LATN,
    SYSTEM_PROMPT_UZ_CYRL,
    SFT_PRODUCTION_SYSTEM_PROMPT,
    USER_ASYMMETRIC_STYLE_GUIDE,
    REAL_USER_STYLE_EXAMPLES,
    FORBIDDEN_USER_PATTERNS,
    validate_user_prompt_style,
    validate_orthography,
    normalize_uzbek_orthography,
)
from ufl_bench.models.mock_model import MockModel
from ufl_bench.models.base import Message


def test_canonical_system_prompts():
    """Verify that canonical system prompts strictly adhere to Unicode U+02BB and universal assistant phrasing."""
    assert "sunʼiy" in SYSTEM_PROMPT_UZ_LATN
    assert "assistentisiz" in SYSTEM_PROMPT_UZ_LATN
    assert len(validate_orthography(SYSTEM_PROMPT_UZ_LATN)) == 0

    assert "ассистентисиз" in SYSTEM_PROMPT_UZ_CYRL
    assert "сунъий" in SYSTEM_PROMPT_UZ_CYRL


def test_sft_production_system_prompt():
    """Verify that the production system prompt (SYSTEM_BASE) conforms to all directives."""
    assert "Siz yuqori sifatli oʻzbekcha korporativ agent epizodlarini yozasiz." in SFT_PRODUCTION_SYSTEM_PROMPT
    assert "HAQIQIY FOYDALANUVCHI USLUBI" in SFT_PRODUCTION_SYSTEM_PROMPT
    assert "QUYIDAGILAR MUTLAQO TAQIQLANGAN" in SFT_PRODUCTION_SYSTEM_PROMPT
    assert "MAJBURIY YAKUN" in SFT_PRODUCTION_SYSTEM_PROMPT

    # Orthography validation
    issues = validate_orthography(SFT_PRODUCTION_SYSTEM_PROMPT)
    assert len(issues) == 0, f"Found orthography issues in production system prompt: {issues}"


def test_real_user_style_examples():
    """Verify that all real user style examples pass style validation."""
    assert len(REAL_USER_STYLE_EXAMPLES) >= 10

    for example in REAL_USER_STYLE_EXAMPLES:
        violations = validate_user_prompt_style(example)
        assert len(violations) == 0, f"Real user example '{example}' failed style validation: {violations}"


def test_validate_user_prompt_style_catches_violations():
    """Verify that forbidden bureaucratic patterns are correctly caught and flagged."""
    bad_prompts = [
        "Hurmatli yordamchi, menga bugungi ob-havoni aytib bering",
        "Men Toshkent savdo tashkilotida ishlayman",
        "Assalomu alaykum, men bosh analitik bo'lib ishlayman",
        "Salom Nodir, yangiliklar nima?",
    ]

    for bad in bad_prompts:
        violations = validate_user_prompt_style(bad)
        assert len(violations) > 0, f"Expected violation for forbidden prompt: '{bad}'"


def test_model_harness_with_asymmetric_user_prompts():
    """Verify that model harness cleanly processes asymmetric fast imperative prompts."""
    model = MockModel(mode="oracle")

    for prompt in REAL_USER_STYLE_EXAMPLES[:5]:
        resp = model.generate_single(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_UZ_LATN,
        )
        assert resp is not None
        assert isinstance(resp.content, str) or len(resp.tool_calls) > 0
