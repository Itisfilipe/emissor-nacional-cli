from __future__ import annotations

import pytest
import yaml

import emissor.config as config_mod


class TestResolveDir:
    def test_from_env_var(self, monkeypatch, tmp_path):
        monkeypatch.setenv("EMISSOR_CONFIG_DIR", str(tmp_path))
        result = config_mod._resolve_dir("EMISSOR_CONFIG_DIR", "config")
        assert result == tmp_path

    def test_project_root_fallback(self, monkeypatch, tmp_path):
        monkeypatch.delenv("EMISSOR_CONFIG_DIR", raising=False)
        # Create a fake project root with config dir
        fake_root = tmp_path / "src" / "emissor"
        fake_root.mkdir(parents=True)
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Patch __file__ so project_root resolves to tmp_path
        monkeypatch.setattr(config_mod, "__file__", str(fake_root / "config.py"))
        result = config_mod._resolve_dir("EMISSOR_CONFIG_DIR", "config")
        assert result == config_dir

    def test_raises_when_no_dir_found(self, monkeypatch, tmp_path):
        monkeypatch.delenv("EMISSOR_CONFIG_DIR", raising=False)
        # Point __file__ to a path that doesn't have config subdir
        fake = tmp_path / "nowhere" / "src" / "emissor"
        fake.mkdir(parents=True)
        monkeypatch.setattr(config_mod, "__file__", str(fake / "config.py"))
        with pytest.raises(RuntimeError, match="EMISSOR_CONFIG_DIR"):
            config_mod._resolve_dir("EMISSOR_CONFIG_DIR", "config")


class TestCertEnv:
    def test_get_cert_path_returns_env(self, monkeypatch):
        monkeypatch.setenv("CERT_PFX_PATH", "/some/path.pfx")
        assert config_mod.get_cert_path() == "/some/path.pfx"

    def test_get_cert_path_raises_missing(self, monkeypatch):
        monkeypatch.delenv("CERT_PFX_PATH", raising=False)
        with pytest.raises(KeyError):
            config_mod.get_cert_path()

    def test_get_cert_password_returns_env(self, monkeypatch):
        monkeypatch.setenv("CERT_PFX_PASSWORD", "secret")
        assert config_mod.get_cert_password() == "secret"

    def test_get_cert_password_raises_missing(self, monkeypatch):
        monkeypatch.delenv("CERT_PFX_PASSWORD", raising=False)
        with pytest.raises(KeyError):
            config_mod.get_cert_password()


class TestLoadYaml:
    def test_valid(self, tmp_path):
        f = tmp_path / "test.yaml"
        f.write_text(yaml.dump({"key": "value"}))
        assert config_mod.load_yaml(f) == {"key": "value"}

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            config_mod.load_yaml(tmp_path / "missing.yaml")


class TestLoadEmitterClient:
    def test_load_emitter(self, monkeypatch, config_dir, emitter_dict):
        monkeypatch.setattr(config_mod, "CONFIG_DIR", config_dir)
        result = config_mod.load_emitter()
        assert result["cnpj"] == emitter_dict["cnpj"]

    def test_load_emitter_missing(self, monkeypatch, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.setattr(config_mod, "CONFIG_DIR", empty)
        with pytest.raises(FileNotFoundError):
            config_mod.load_emitter()

    def test_load_client_missing(self, monkeypatch, tmp_path):
        cfg = tmp_path / "config"
        cfg.mkdir()
        (cfg / "clients").mkdir()
        monkeypatch.setattr(config_mod, "CONFIG_DIR", cfg)
        with pytest.raises(FileNotFoundError):
            config_mod.load_client("nonexistent")
