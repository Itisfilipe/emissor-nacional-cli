from __future__ import annotations

import pytest

from emissor.models.client import Client, Intermediary
from emissor.models.emitter import Emitter

# --- Emitter ---


class TestEmitter:
    def test_from_dict(self, emitter_dict):
        e = Emitter.from_dict(emitter_dict)
        assert e.cnpj == "12345678000199"
        assert e.razao_social == "ACME SOFTWARE LTDA"
        assert e.serie == "900"

    def test_from_dict_defaults(self):
        d = {
            "cnpj": "00000000000100",
            "razao_social": "X",
            "logradouro": "X",
            "numero": "1",
            "bairro": "X",
            "cod_municipio": "1234567",
            "uf": "SP",
            "cep": "00000000",
            "fone": "11999999999",
            "email": "x@x.com",
        }
        e = Emitter.from_dict(d)
        assert e.op_simp_nac == "1"
        assert e.reg_esp_trib == "0"
        assert e.serie == "900"
        assert e.ver_aplic == "emissor-nacional_0.1.0"

    def test_from_dict_missing_required(self):
        with pytest.raises(KeyError):
            Emitter.from_dict({"razao_social": "X"})

    def test_from_dict_coerces_to_str(self):
        d = {
            "cnpj": "00000000000100",
            "razao_social": "X",
            "logradouro": "X",
            "numero": "1",
            "bairro": "X",
            "cod_municipio": "1234567",
            "uf": "SP",
            "cep": "00000000",
            "fone": "11999999999",
            "email": "x@x.com",
            "op_simp_nac": 1,
            "serie": 900,
        }
        e = Emitter.from_dict(d)
        assert e.op_simp_nac == "1"
        assert e.serie == "900"

    def test_frozen(self, emitter):
        with pytest.raises(AttributeError):
            emitter.cnpj = "other"


# --- Client ---


class TestClient:
    def test_from_dict(self, client_dict):
        c = Client.from_dict(client_dict)
        assert c.nif == "123456789"
        assert c.nome == "Acme Corp"
        assert c.pais == "US"

    def test_from_dict_defaults(self):
        d = {
            "nif": "111",
            "nome": "X",
            "logradouro": "X",
            "numero": "1",
            "cidade": "X",
            "estado": "X",
            "cep": "00000",
        }
        c = Client.from_dict(d)
        assert c.pais == "US"
        assert c.bairro == "n/a"
        assert c.mec_af_comex_p == "02"
        assert c.mec_af_comex_t == "02"

    def test_from_dict_missing_required(self):
        with pytest.raises(KeyError):
            Client.from_dict({"nome": "X"})

    def test_complemento_none_default(self, client):
        assert client.complemento is None

    def test_complemento_present(self, client_with_complement):
        assert client_with_complement.complemento == "ste 400"

    def test_frozen(self, client):
        with pytest.raises(AttributeError):
            client.nif = "other"


# --- Intermediary ---


class TestIntermediary:
    def test_from_dict(self, intermediary_dict):
        i = Intermediary.from_dict(intermediary_dict)
        assert i.nif == "9876543"
        assert i.nome == "GLOBAL PAYMENTS INC"
        assert i.pais == "US"

    def test_from_dict_defaults(self):
        d = {
            "nif": "111",
            "nome": "X",
            "logradouro": "X",
            "numero": "1",
            "cidade": "X",
            "estado": "X",
            "cep": "00000",
        }
        i = Intermediary.from_dict(d)
        assert i.pais == "US"
        assert i.bairro == "NA"

    def test_from_dict_missing_required(self):
        with pytest.raises(KeyError):
            Intermediary.from_dict({"nome": "X"})


# --- Invoice ---


class TestInvoice:
    def test_frozen(self, sample_invoice):
        with pytest.raises(AttributeError):
            sample_invoice.valor_brl = "0"
