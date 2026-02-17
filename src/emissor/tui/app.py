from __future__ import annotations

from textual.app import App


class EmissorApp(App):
    """Emissor Nacional TUI application."""

    CSS_PATH = "app.tcss"
    TITLE = "Emissor Nacional"
    ENABLE_COMMAND_PALETTE = False

    BINDINGS: list = []

    def __init__(self, env: str = "homologacao"):
        super().__init__()
        self.env = env

    def on_mount(self) -> None:
        from emissor.config import migrate_data_layout
        from emissor.tui.screens.dashboard import DashboardScreen

        migrate_data_layout()
        self.push_screen(DashboardScreen())
