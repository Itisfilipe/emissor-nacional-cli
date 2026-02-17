from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmScreen(ModalScreen[bool]):
    """Simple yes/no confirmation dialog for dangerous actions."""

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
        background: $surface 80%;
    }
    #confirm-dialog {
        width: 60;
        height: auto;
        max-height: 16;
        background: $surface;
        border: thick $error;
        padding: 1 2;
    }
    #confirm-message {
        margin-bottom: 1;
    }
    #confirm-dialog .button-bar {
        height: 3;
        margin-top: 1;
        layout: horizontal;
        align-horizontal: right;
    }
    #confirm-dialog .button-bar Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancelar"),
        Binding("q", "cancel", show=False),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(self._message, id="confirm-message")
            with Horizontal(classes="button-bar"):
                yield Button("\u2715 Cancelar", id="btn-cancel")
                yield Button("\u25b6 Confirmar", id="btn-confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-confirm")

    def action_cancel(self) -> None:
        self.dismiss(False)
