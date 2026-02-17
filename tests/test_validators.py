from __future__ import annotations

import pytest

from emissor.utils.validators import (
    validate_access_key,
    validate_c_nbs,
    validate_c_pais_result,
    validate_c_trib_nac,
    validate_cst_pis_cofins,
    validate_date,
    validate_monetary,
    validate_percent,
    validate_postal_code,
    validate_tp_moeda,
)


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


class TestValidateCTribNac:
    def test_valid(self):
        assert validate_c_trib_nac("010401") == "010401"

    def test_valid_all_zeros(self):
        assert validate_c_trib_nac("000000") == "000000"

    def test_too_short(self):
        with pytest.raises(ValueError, match="6 digitos"):
            validate_c_trib_nac("01040")

    def test_too_long(self):
        with pytest.raises(ValueError, match="6 digitos"):
            validate_c_trib_nac("0104011")

    def test_non_numeric(self):
        with pytest.raises(ValueError, match="6 digitos"):
            validate_c_trib_nac("01040a")

    def test_empty(self):
        with pytest.raises(ValueError, match="6 digitos"):
            validate_c_trib_nac("")


class TestValidateCNbs:
    def test_valid(self):
        assert validate_c_nbs("123456789") == "123456789"

    def test_too_short(self):
        with pytest.raises(ValueError, match="9 digitos"):
            validate_c_nbs("12345678")

    def test_too_long(self):
        with pytest.raises(ValueError, match="9 digitos"):
            validate_c_nbs("1234567890")

    def test_non_numeric(self):
        with pytest.raises(ValueError, match="9 digitos"):
            validate_c_nbs("12345678a")


class TestValidateTpMoeda:
    def test_valid_usd(self):
        assert validate_tp_moeda("220") == "220"

    def test_valid_eur(self):
        assert validate_tp_moeda("978") == "978"

    def test_too_short(self):
        with pytest.raises(ValueError, match="3 digitos"):
            validate_tp_moeda("22")

    def test_too_long(self):
        with pytest.raises(ValueError, match="3 digitos"):
            validate_tp_moeda("2200")

    def test_non_numeric(self):
        with pytest.raises(ValueError, match="3 digitos"):
            validate_tp_moeda("abc")


class TestValidateCPaisResult:
    def test_valid_us(self):
        assert validate_c_pais_result("US") == "US"

    def test_valid_de(self):
        assert validate_c_pais_result("DE") == "DE"

    def test_lowercase(self):
        with pytest.raises(ValueError, match="2 letras maiusculas"):
            validate_c_pais_result("us")

    def test_three_chars(self):
        with pytest.raises(ValueError, match="2 letras maiusculas"):
            validate_c_pais_result("USA")

    def test_digits(self):
        with pytest.raises(ValueError, match="2 letras maiusculas"):
            validate_c_pais_result("12")


class TestValidateCstPisCofins:
    def test_valid_01(self):
        assert validate_cst_pis_cofins("01") == "01"

    def test_valid_08(self):
        assert validate_cst_pis_cofins("08") == "08"

    def test_valid_99(self):
        assert validate_cst_pis_cofins("99") == "99"

    def test_invalid_00(self):
        with pytest.raises(ValueError, match="codigo invalido"):
            validate_cst_pis_cofins("00")

    def test_non_numeric(self):
        with pytest.raises(ValueError, match="codigo invalido"):
            validate_cst_pis_cofins("ab")


class TestValidatePercent:
    def test_zero(self):
        assert validate_percent("0") == "0.00"

    def test_hundred(self):
        assert validate_percent("100") == "100.00"

    def test_normalizes_precision(self):
        assert validate_percent("15.5") == "15.50"

    def test_decimal(self):
        assert validate_percent("33.33") == "33.33"

    def test_negative(self):
        with pytest.raises(ValueError, match=r"entre 0\.00 e 100\.00"):
            validate_percent("-1")

    def test_over_hundred(self):
        with pytest.raises(ValueError, match=r"entre 0\.00 e 100\.00"):
            validate_percent("100.01")

    def test_non_numeric(self):
        with pytest.raises(ValueError, match="invalido"):
            validate_percent("abc")


class TestValidateAccessKey:
    def test_valid_50_chars(self):
        key = "A" * 50
        assert validate_access_key(key) == key

    def test_valid_alphanumeric(self):
        key = "aB3" * 16 + "xY"  # 50 chars
        assert validate_access_key(key) == key

    def test_too_short(self):
        with pytest.raises(ValueError, match="50 caracteres"):
            validate_access_key("A" * 49)

    def test_too_long(self):
        with pytest.raises(ValueError, match="50 caracteres"):
            validate_access_key("A" * 51)

    def test_special_chars(self):
        with pytest.raises(ValueError, match="50 caracteres"):
            validate_access_key("A" * 49 + "-")

    def test_empty(self):
        with pytest.raises(ValueError, match="50 caracteres"):
            validate_access_key("")


class TestValidatePostalCode:
    def test_valid_us_zip(self):
        assert validate_postal_code("10001") == "10001"

    def test_valid_us_zip_plus4(self):
        assert validate_postal_code("10001-1234") == "10001-1234"

    def test_valid_uk_postcode(self):
        assert validate_postal_code("SW1A 1AA") == "SW1A 1AA"

    def test_too_short(self):
        with pytest.raises(ValueError, match="3-10"):
            validate_postal_code("AB")

    def test_too_long(self):
        with pytest.raises(ValueError, match="3-10"):
            validate_postal_code("12345678901")

    def test_empty(self):
        with pytest.raises(ValueError, match="3-10"):
            validate_postal_code("")

    def test_special_chars(self):
        with pytest.raises(ValueError, match="3-10"):
            validate_postal_code("123#4")
