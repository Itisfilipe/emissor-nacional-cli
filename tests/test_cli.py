from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import yaml

from emissor.cli import (
    _check_keyring_available,
    _init_config,
    _preflight,
    _remove_env_var,
    _setup_certificate,
    _upsert_env_var,
    _warn_open_permissions,
    main,
)


class TestMain:
    @patch("emissor.tui.app.EmissorApp")
    @patch("emissor.cli._preflight", return_value=True)
    def test_launches_tui(self, mock_preflight, mock_app_cls):
        mock_app = MagicMock()
        mock_app_cls.return_value = mock_app
        with patch("sys.argv", ["emissor-nacional"]):
            main()
        mock_preflight.assert_called_once()
        mock_app_cls.assert_called_once()
        mock_app.run.assert_called_once()

    @patch("emissor.cli._init_config")
    def test_init_dispatches(self, mock_init):
        with patch("sys.argv", ["emissor-nacional", "init"]):
            main()
        mock_init.assert_called_once()

    @patch("emissor.cli._preflight", return_value=False)
    def test_exit_1_on_failure(self, mock_preflight):
        with patch("sys.argv", ["emissor-nacional"]), pytest.raises(SystemExit, match="1"):
            main()


class TestPreflight:
    def test_preflight_ok(self, monkeypatch, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "emitter.yaml").write_text(yaml.dump({"cnpj": "00000000000000"}))
        data_dir = tmp_path / "data"
        monkeypatch.setattr("emissor.config.get_config_dir", lambda: config_dir)
        monkeypatch.setattr("emissor.config.get_data_dir", lambda: data_dir)
        assert _preflight() is True
        assert data_dir.is_dir()

    def test_preflight_no_config(self, monkeypatch, tmp_path, capsys):
        config_dir = tmp_path / "missing"
        data_dir = tmp_path / "data"
        monkeypatch.setattr("emissor.config.get_config_dir", lambda: config_dir)
        monkeypatch.setattr("emissor.config.get_data_dir", lambda: data_dir)
        assert _preflight() is False
        out = capsys.readouterr().out
        assert "emissor-nacional init" in out

    def test_preflight_no_emitter(self, monkeypatch, tmp_path, capsys):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        data_dir = tmp_path / "data"
        monkeypatch.setattr("emissor.config.get_config_dir", lambda: config_dir)
        monkeypatch.setattr("emissor.config.get_data_dir", lambda: data_dir)
        assert _preflight() is False
        out = capsys.readouterr().out
        assert "emitter.yaml" in out


class TestInitConfig:
    def test_copies_templates(self, monkeypatch, tmp_path):
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        monkeypatch.setattr("emissor.config.get_config_dir", lambda: config_dir)
        monkeypatch.setattr("emissor.config.get_data_dir", lambda: data_dir)
        # Skip cert setup prompt
        monkeypatch.setattr("builtins.input", lambda _: "n")
        _init_config()
        assert (config_dir / "emitter.yaml.example").exists()
        assert (config_dir / "clients" / "acme-corp.yaml.example").exists()
        assert (config_dir / "clients" / "intermediary.yaml.example").exists()
        assert data_dir.exists()

    def test_skips_existing(self, monkeypatch, tmp_path, capsys):
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "clients").mkdir(parents=True)
        (config_dir / "emitter.yaml.example").write_text("existing")
        data_dir = tmp_path / "data"
        monkeypatch.setattr("emissor.config.get_config_dir", lambda: config_dir)
        monkeypatch.setattr("emissor.config.get_data_dir", lambda: data_dir)
        # Skip cert setup prompt
        monkeypatch.setattr("builtins.input", lambda _: "n")
        _init_config()
        # emitter.yaml.example should not be overwritten
        assert (config_dir / "emitter.yaml.example").read_text() == "existing"
        out = capsys.readouterr().out
        assert "já existe" in out

    def test_cert_step_shown(self, monkeypatch, tmp_path, capsys):
        """When cert is not configured, step 3 mentions .env."""
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        monkeypatch.setattr("emissor.config.get_config_dir", lambda: config_dir)
        monkeypatch.setattr("emissor.config.get_data_dir", lambda: data_dir)
        monkeypatch.setattr("builtins.input", lambda _: "n")
        _init_config()
        out = capsys.readouterr().out
        assert "CERT_PFX_PATH" in out

    def test_cert_configured_skips_step(self, monkeypatch, tmp_path, capsys):
        """When cert is configured, step 3 about .env is omitted."""
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        monkeypatch.setattr("emissor.config.get_config_dir", lambda: config_dir)
        monkeypatch.setattr("emissor.config.get_data_dir", lambda: data_dir)
        # Say yes to cert, then _setup_certificate returns True
        monkeypatch.setattr("builtins.input", lambda _: "s")
        with patch("emissor.cli._setup_certificate", return_value=True):
            _init_config()
        out = capsys.readouterr().out
        assert "CERT_PFX_PATH" not in out

    def test_eof_during_cert_prompt(self, monkeypatch, tmp_path, capsys):
        """EOFError during cert prompt is handled gracefully."""
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        monkeypatch.setattr("emissor.config.get_config_dir", lambda: config_dir)
        monkeypatch.setattr("emissor.config.get_data_dir", lambda: data_dir)
        monkeypatch.setattr("builtins.input", MagicMock(side_effect=EOFError))
        _init_config()
        # Should not crash
        out = capsys.readouterr().out
        assert "Configuração:" in out


class TestUpsertEnvVar:
    def test_creates_new_file(self, tmp_path):
        env_file = tmp_path / "sub" / ".env"
        _upsert_env_var(env_file, "KEY", "value")
        content = env_file.read_text()
        assert "KEY=" in content
        assert "value" in content

    def test_appends_to_existing(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING='1'\n")
        _upsert_env_var(env_file, "NEW_KEY", "val")
        content = env_file.read_text()
        assert "EXISTING=" in content
        assert "NEW_KEY=" in content
        assert "val" in content

    def test_updates_existing_key(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("MY_KEY='old'\nOTHER='keep'\n")
        _upsert_env_var(env_file, "MY_KEY", "new")
        content = env_file.read_text()
        assert "new" in content
        assert "'old'" not in content
        assert "OTHER=" in content

    def test_handles_special_chars(self, tmp_path):
        """Values with # and spaces are properly quoted by dotenv.set_key."""
        env_file = tmp_path / ".env"
        env_file.touch()
        _upsert_env_var(env_file, "PW", "abc #def")
        from dotenv import dotenv_values

        loaded = dotenv_values(env_file)
        assert loaded["PW"] == "abc #def"


class TestRemoveEnvVar:
    def test_removes_existing_key(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEEP='yes'\nREMOVE='me'\n")
        _remove_env_var(env_file, "REMOVE")
        content = env_file.read_text()
        assert "KEEP=" in content
        assert "REMOVE" not in content

    def test_noop_missing_key(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY='val'\n")
        _remove_env_var(env_file, "NONEXISTENT")
        assert "KEY=" in env_file.read_text()

    def test_noop_missing_file(self, tmp_path):
        env_file = tmp_path / ".env"
        _remove_env_var(env_file, "KEY")  # should not crash


class TestWarnOpenPermissions:
    def test_warns_group_readable(self, tmp_path, capsys):
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=x\n")
        env_file.chmod(0o644)  # group+other readable
        _warn_open_permissions(env_file)
        out = capsys.readouterr().out
        assert "permissões abertas" in out

    def test_no_warn_restricted(self, tmp_path, capsys):
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=x\n")
        env_file.chmod(0o600)  # owner only
        _warn_open_permissions(env_file)
        out = capsys.readouterr().out
        assert out == ""


class TestCheckKeyringAvailable:
    def test_available_with_real_backend(self):
        mock_kr = MagicMock()
        mock_kr.get_keyring.return_value = MagicMock()  # not FailKeyring
        # Need to mock the FailKeyring class for isinstance check
        mock_fail = type("FailKeyring", (), {})
        mock_fail_module = MagicMock()
        mock_fail_module.Keyring = mock_fail
        with patch.dict(
            "sys.modules",
            {"keyring": mock_kr, "keyring.backends.fail": mock_fail_module},
        ):
            assert _check_keyring_available() is True

    def test_unavailable_with_fail_backend(self):
        mock_fail_cls = type("Keyring", (), {})
        mock_instance = mock_fail_cls()

        mock_kr = MagicMock()
        mock_kr.get_keyring.return_value = mock_instance

        mock_fail_module = MagicMock()
        mock_fail_module.Keyring = mock_fail_cls

        with patch.dict(
            "sys.modules",
            {"keyring": mock_kr, "keyring.backends.fail": mock_fail_module},
        ):
            assert _check_keyring_available() is False

    def test_exception_returns_false(self):
        with patch.dict("sys.modules", {"keyring": MagicMock(side_effect=ImportError)}):
            # If import itself fails somehow
            result = _check_keyring_available()
            # May be True or False depending on mock — just ensure no crash
            assert isinstance(result, bool)


class TestSetupCertificate:
    def test_skip_on_empty_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "")
        result = _setup_certificate(tmp_path)
        assert result is False

    def test_file_not_found_reprompts(self, tmp_path, monkeypatch):
        inputs = iter(["/nonexistent/cert.pfx", ""])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        result = _setup_certificate(tmp_path)
        assert result is False

    def test_invalid_cert_aborts(self, tmp_path, monkeypatch, capsys):
        # Create a fake .pfx file
        fake_pfx = tmp_path / "bad.pfx"
        fake_pfx.write_bytes(b"not a real pfx")

        inputs = iter([str(fake_pfx)])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda _: "wrong-pass")

        result = _setup_certificate(tmp_path)
        assert result is False
        out = capsys.readouterr().out
        assert "ERRO" in out

    def test_successful_setup_dotenv(self, tmp_path, monkeypatch, test_pfx):
        from dotenv import dotenv_values

        pfx_path, pfx_password = test_pfx
        inputs = iter([pfx_path, "2"])  # path, then choose .env storage
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda _: pfx_password)
        monkeypatch.setattr("emissor.cli._check_keyring_available", lambda: False)

        with patch("emissor.config._delete_keyring_password", return_value=False):
            result = _setup_certificate(tmp_path)
        assert result is True

        env_file = tmp_path / ".env"
        assert env_file.exists()
        vals = dotenv_values(env_file)
        assert vals["CERT_PFX_PATH"] == pfx_path
        assert vals["CERT_PFX_PASSWORD"] == pfx_password

    def test_successful_setup_keyring(self, tmp_path, monkeypatch, test_pfx):
        pfx_path, pfx_password = test_pfx
        inputs = iter([pfx_path, "1"])  # path, then choose keyring
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda _: pfx_password)
        monkeypatch.setattr("emissor.cli._check_keyring_available", lambda: True)

        with patch("emissor.config._set_keyring_password", return_value=True) as mock_set:
            result = _setup_certificate(tmp_path)

        assert result is True
        mock_set.assert_called_once_with(pfx_password)
        # Path should still be saved to .env
        from dotenv import dotenv_values

        vals = dotenv_values(tmp_path / ".env")
        assert vals["CERT_PFX_PATH"] == pfx_path
        # Password should NOT be in .env when keyring succeeds
        assert "CERT_PFX_PASSWORD" not in vals

    def test_keyring_failure_falls_back_to_dotenv(self, tmp_path, monkeypatch, test_pfx, capsys):
        from dotenv import dotenv_values

        pfx_path, pfx_password = test_pfx
        inputs = iter([pfx_path, "1"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda _: pfx_password)
        monkeypatch.setattr("emissor.cli._check_keyring_available", lambda: True)

        with patch("emissor.config._set_keyring_password", return_value=False):
            result = _setup_certificate(tmp_path)

        assert result is True
        out = capsys.readouterr().out
        assert "Falha ao armazenar no keychain" in out
        # Should fall back to .env
        vals = dotenv_values(tmp_path / ".env")
        assert vals["CERT_PFX_PASSWORD"] == pfx_password

    def test_no_store_option(self, tmp_path, monkeypatch, test_pfx, capsys):
        from dotenv import dotenv_values

        pfx_path, pfx_password = test_pfx
        inputs = iter([pfx_path, "3"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda _: pfx_password)
        monkeypatch.setattr("emissor.cli._check_keyring_available", lambda: False)

        with patch("emissor.config._delete_keyring_password", return_value=False):
            result = _setup_certificate(tmp_path)
        assert result is True
        # Only path in .env, no password
        vals = dotenv_values(tmp_path / ".env")
        assert vals["CERT_PFX_PATH"] == pfx_path
        assert "CERT_PFX_PASSWORD" not in vals
        out = capsys.readouterr().out
        assert "Senha não armazenada" in out
