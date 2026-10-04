import pytest
from ufl_bench.utils.numeric import parse_numeric_value, compare_numeric


def test_parse_numeric_value():
    assert parse_numeric_value("150 000 soʻm") == 150000.0
    assert parse_numeric_value("1 250 000.50 UZS") == 1250000.50
    assert parse_numeric_value("12,5%") == 12.5
    assert parse_numeric_value("-42.5") == -42.5
    assert parse_numeric_value("3 450 000 сўм") == 3450000.0
    assert parse_numeric_value(100) == 100.0
    assert parse_numeric_value("invalid") is None


def test_compare_numeric():
    assert compare_numeric("150 000 soʻm", 150000)
    assert compare_numeric("12.5001", "12.5", rel_tol=1e-3)
    assert not compare_numeric("150 000", "200 000")
    assert compare_numeric("3 450 000 сўм", "3450000")
