from __future__ import annotations

from emissor.utils.formatters import format_brl, format_usd


class TestFormatBrl:
    def test_simple(self):
        assert format_brl("1000") == "R$ 1.000,00"

    def test_with_decimals(self):
        assert format_brl("19684.93") == "R$ 19.684,93"

    def test_small(self):
        assert format_brl("5.5") == "R$ 5,50"

    def test_zero(self):
        assert format_brl("0") == "R$ 0,00"

    def test_large(self):
        assert format_brl("1234567.89") == "R$ 1.234.567,89"


class TestFormatUsd:
    def test_simple(self):
        assert format_usd("3640") == "US$ 3,640.00"

    def test_with_decimals(self):
        assert format_usd("3640.50") == "US$ 3,640.50"

    def test_small(self):
        assert format_usd("5.5") == "US$ 5.50"

    def test_zero(self):
        assert format_usd("0") == "US$ 0.00"
