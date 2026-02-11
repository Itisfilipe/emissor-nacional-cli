from __future__ import annotations

import pytest

from emissor.utils.validators import validate_date, validate_monetary


class TestValidateMonetary:
    def test_valid(self):
        assert validate_monetary("19684.93") == "19684.93"

    def test_preserves_two_decimal_places(self):
        assert validate_monetary("100.00") == "100.00"

    def test_pads_to_two_decimals(self):
        assert validate_monetary("1000.1") == "1000.10"

    def test_integer_gets_decimals(self):
        assert validate_monetary("500") == "500.00"

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="invalido"):
            validate_monetary("NaN")

    def test_infinity_raises(self):
        with pytest.raises(ValueError, match="invalido"):
            validate_monetary("Infinity")

    def test_non_numeric_raises(self):
        with pytest.raises(ValueError, match="invalido"):
            validate_monetary("abc")

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="positivo"):
            validate_monetary("0")

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="positivo"):
            validate_monetary("-5")

    def test_small_value(self):
        assert validate_monetary("0.01") == "0.01"

    def test_large_value(self):
        assert validate_monetary("999999.99") == "999999.99"


class TestValidateDate:
    def test_valid(self):
        assert validate_date("2025-12-30") == "2025-12-30"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="invalida"):
            validate_date("not-a-date")

    def test_invalid_month(self):
        with pytest.raises(ValueError, match="invalida"):
            validate_date("2025-13-01")

    def test_leap_year(self):
        assert validate_date("2024-02-29") == "2024-02-29"
