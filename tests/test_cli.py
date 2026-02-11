from __future__ import annotations

from unittest.mock import MagicMock, patch

from emissor.cli import main


class TestMain:
    @patch("emissor.tui.app.EmissorApp")
    def test_launches_tui(self, mock_app_cls):
        mock_app = MagicMock()
        mock_app_cls.return_value = mock_app
        main()
        mock_app_cls.assert_called_once()
        mock_app.run.assert_called_once()
