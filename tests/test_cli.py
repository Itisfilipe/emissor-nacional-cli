from __future__ import annotations

from unittest.mock import MagicMock, patch

from emissor.cli import main, _init_config


class TestMain:
    @patch("emissor.tui.app.EmissorApp")
    def test_launches_tui(self, mock_app_cls):
        mock_app = MagicMock()
        mock_app_cls.return_value = mock_app
        with patch("sys.argv", ["emissor-nacional"]):
            main()
        mock_app_cls.assert_called_once()
        mock_app.run.assert_called_once()

    @patch("emissor.cli._init_config")
    def test_init_dispatches(self, mock_init):
        with patch("sys.argv", ["emissor-nacional", "init"]):
            main()
        mock_init.assert_called_once()


class TestInitConfig:
    def test_copies_templates(self, monkeypatch, tmp_path):
        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"
        monkeypatch.setattr("emissor.config.get_config_dir", lambda: config_dir)
        monkeypatch.setattr("emissor.config.get_data_dir", lambda: data_dir)
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
        _init_config()
        # emitter.yaml.example should not be overwritten
        assert (config_dir / "emitter.yaml.example").read_text() == "existing"
        out = capsys.readouterr().out
        assert "já existe" in out
