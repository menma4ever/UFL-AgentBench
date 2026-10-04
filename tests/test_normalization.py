import pytest
from ufl_bench.utils.normalization import (
    normalize_uzbek_orthography,
    detect_script,
    validate_orthography,
    quasi_normalize_text,
    is_cyrillic,
)


def test_normalize_uzbek_orthography():
    # Straight quote in o' and g'
    raw = "O'zbekiston, go'zal, to'g'ri, ma'lumot, e'tibor, san'at"
    norm = normalize_uzbek_orthography(raw)
    assert "Oʻzbekiston" in norm
    assert "goʻzal" in norm
    assert "toʻgʻri" in norm
    assert "maʼlumot" in norm
    assert "eʼtibor" in norm
    assert "sanʼat" in norm

    # Prohibited quotes check
    issues = validate_orthography(norm)
    assert len(issues) == 0


def test_detect_script():
    latn_text = "Toshkent shahridagi eng yirik bozor qaysi?"
    cyrl_text = "Тошкент шаҳридаги энг йирик бозор қайси?"
    
    script, bcp47 = detect_script(latn_text)
    assert script == "Latn"
    assert bcp47 == "uz-Latn"
    assert not is_cyrillic(latn_text)

    script, bcp47 = detect_script(cyrl_text)
    assert script == "Cyrl"
    assert bcp47 == "uz-Cyrl"
    assert is_cyrillic(cyrl_text)


def test_quasi_normalize_text():
    raw = "  «Toshkent shahri!»  "
    norm = quasi_normalize_text(raw)
    assert "toshkent" in norm

    # Number with currency
    curr = "  150 000 so'm.  "
    norm_curr = quasi_normalize_text(curr)
    assert "150 000 soʻm" == norm_curr
