from __future__ import annotations

from emissor.utils.dps_id import generate_dps_id


def test_basic_id():
    dps_id = generate_dps_id(
        cod_municipio="4205407",
        cnpj="12345678000199",
        serie="900",
        n_dps=3,
    )
    assert dps_id == "DPS420540721234567800019900900000000000000003"
    assert len(dps_id) == 45


def test_ndps_one():
    dps_id = generate_dps_id(
        cod_municipio="4205407",
        cnpj="12345678000199",
        serie="900",
        n_dps=1,
    )
    assert dps_id == "DPS420540721234567800019900900000000000000001"
    assert len(dps_id) == 45


def test_large_ndps():
    dps_id = generate_dps_id(
        cod_municipio="4205407",
        cnpj="12345678000199",
        serie="900",
        n_dps=999999999999999,
    )
    assert dps_id == "DPS420540721234567800019900900999999999999999"
    assert len(dps_id) == 45
