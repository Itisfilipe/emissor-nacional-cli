from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import yaml

import emissor.config as config_mod


class TestResolveDir:
    def test_from_env_var(self, monkeypatch, tmp_path):
        monkeypatch.setenv("EMISSOR_CONFIG_DIR", str(tmp_path))
        result = config_mod._resolve_dir("EMISSOR_CONFIG_DIR", "config", kind="config")
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
        result = config_mod._resolve_dir("EMISSOR_CONFIG_DIR", "config", kind="config")
        assert result == config_dir

    def test_platformdirs_fallback_config(self, monkeypatch, tmp_path):
        monkeypatch.delenv("EMISSOR_CONFIG_DIR", raising=False)
        fake = tmp_path / "nowhere" / "src" / "emissor"
        fake.mkdir(parents=True)
        monkeypatch.setattr(config_mod, "__file__", str(fake / "config.py"))
        result = config_mod._resolve_dir("EMISSOR_CONFIG_DIR", "config", kind="config")
        assert "emissor-nacional" in str(result)

    def test_platformdirs_fallback_data(self, monkeypatch, tmp_path):
        monkeypatch.delenv("EMISSOR_DATA_DIR", raising=False)
        fake = tmp_path / "nowhere" / "src" / "emissor"
        fake.mkdir(parents=True)
        monkeypatch.setattr(config_mod, "__file__", str(fake / "config.py"))
        result = config_mod._resolve_dir("EMISSOR_DATA_DIR", "data", kind="data")
        assert "emissor-nacional" in str(result)


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
        with (
            patch.object(config_mod, "_get_keyring_password", return_value=None),
            pytest.raises(KeyError),
        ):
            config_mod.get_cert_password()

    def test_get_cert_password_keyring_fallback(self, monkeypatch):
        monkeypatch.delenv("CERT_PFX_PASSWORD", raising=False)
        with patch.object(config_mod, "_get_keyring_password", return_value="from-keyring"):
            assert config_mod.get_cert_password() == "from-keyring"

    def test_get_cert_password_env_takes_priority(self, monkeypatch):
        monkeypatch.setenv("CERT_PFX_PASSWORD", "from-env")
        with patch.object(config_mod, "_get_keyring_password", return_value="from-keyring"):
            assert config_mod.get_cert_password() == "from-env"


class TestKeyringHelpers:
    def test_get_keyring_password_success(self):
        mock_kr = MagicMock()
        mock_kr.get_password.return_value = "stored-pw"
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            result = config_mod._get_keyring_password()
        assert result == "stored-pw"

    def test_get_keyring_password_not_stored(self):
        mock_kr = MagicMock()
        mock_kr.get_password.return_value = None
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            result = config_mod._get_keyring_password()
        assert result is None

    def test_get_keyring_password_exception(self):
        mock_kr = MagicMock()
        mock_kr.get_password.side_effect = RuntimeError("no backend")
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            result = config_mod._get_keyring_password()
        assert result is None

    def test_set_keyring_password_success(self):
        mock_kr = MagicMock()
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            assert config_mod._set_keyring_password("pw123") is True
        mock_kr.set_password.assert_called_once_with(
            config_mod.KEYRING_SERVICE, config_mod.KEYRING_USERNAME, "pw123"
        )

    def test_set_keyring_password_failure(self):
        mock_kr = MagicMock()
        mock_kr.set_password.side_effect = RuntimeError("locked")
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            assert config_mod._set_keyring_password("pw") is False

    def test_delete_keyring_password_success(self):
        mock_kr = MagicMock()
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            assert config_mod._delete_keyring_password() is True
        mock_kr.delete_password.assert_called_once()

    def test_delete_keyring_password_failure(self):
        mock_kr = MagicMock()
        mock_kr.delete_password.side_effect = RuntimeError("not found")
        with patch.dict("sys.modules", {"keyring": mock_kr}):
            assert config_mod._delete_keyring_password() is False


class TestDotenvMultiLocation:
    def test_config_dir_dotenv_loaded(self, monkeypatch, tmp_path):
        """Env vars from config dir .env are picked up by get_cert_path."""
        config_dir = tmp_path / "cfg"
        config_dir.mkdir()
        env_file = config_dir / ".env"
        env_file.write_text("CERT_PFX_PATH=/from/config/dir.pfx\n")
        monkeypatch.delenv("CERT_PFX_PATH", raising=False)

        # Simulate what config.py does at module load
        from dotenv import load_dotenv

        load_dotenv(env_file)

        assert config_mod.get_cert_path() == "/from/config/dir.pfx"

    def test_cwd_dotenv_overrides_config_dir(self, monkeypatch, tmp_path):
        """CWD .env has priority over config dir .env."""
        monkeypatch.delenv("CERT_PFX_PATH", raising=False)

        from dotenv import load_dotenv

        # Load "cwd" .env first
        cwd_env = tmp_path / "cwd" / ".env"
        cwd_env.parent.mkdir()
        cwd_env.write_text("CERT_PFX_PATH=/from/cwd.pfx\n")
        load_dotenv(cwd_env)

        # Load config dir .env second (won't override)
        cfg_env = tmp_path / "cfg" / ".env"
        cfg_env.parent.mkdir()
        cfg_env.write_text("CERT_PFX_PATH=/from/config.pfx\n")
        load_dotenv(cfg_env)

        assert config_mod.get_cert_path() == "/from/cwd.pfx"

    def test_resolve_config_dir_for_dotenv_env_var(self, monkeypatch, tmp_path):
        monkeypatch.setenv("EMISSOR_CONFIG_DIR", str(tmp_path))
        result = config_mod._resolve_config_dir_for_dotenv()
        assert result == tmp_path

    def test_resolve_config_dir_for_dotenv_dev_layout(self, monkeypatch, tmp_path):
        monkeypatch.delenv("EMISSOR_CONFIG_DIR", raising=False)
        fake_root = tmp_path / "src" / "emissor"
        fake_root.mkdir(parents=True)
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        monkeypatch.setattr(config_mod, "__file__", str(fake_root / "config.py"))
        result = config_mod._resolve_config_dir_for_dotenv()
        assert result == config_dir

    def test_resolve_config_dir_for_dotenv_none_when_missing(self, monkeypatch, tmp_path):
        monkeypatch.delenv("EMISSOR_CONFIG_DIR", raising=False)
        fake = tmp_path / "nowhere" / "src" / "emissor"
        fake.mkdir(parents=True)
        monkeypatch.setattr(config_mod, "__file__", str(fake / "config.py"))
        # platformdirs dir won't exist, so returns None
        with patch("emissor.config.platformdirs.user_config_dir", return_value=str(fake / "pd")):
            result = config_mod._resolve_config_dir_for_dotenv()
        assert result is None


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
        monkeypatch.setattr(config_mod, "get_config_dir", lambda: config_dir)
        result = config_mod.load_emitter()
        assert result["cnpj"] == emitter_dict["cnpj"]

    def test_load_emitter_missing(self, monkeypatch, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.setattr(config_mod, "get_config_dir", lambda: empty)
        with pytest.raises(FileNotFoundError):
            config_mod.load_emitter()

    def test_load_client_missing(self, monkeypatch, tmp_path):
        cfg = tmp_path / "config"
        cfg.mkdir()
        (cfg / "clients").mkdir()
        monkeypatch.setattr(config_mod, "get_config_dir", lambda: cfg)
        with pytest.raises(FileNotFoundError):
            config_mod.load_client("nonexistent")
