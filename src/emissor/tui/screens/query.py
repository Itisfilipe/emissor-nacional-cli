from __future__ import annotations

import json

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, RichLog, Static


class QueryScreen(ModalScreen):
    """Query an NFS-e by chave de acesso."""

    BINDINGS = [
        Binding("escape", "go_back", "Voltar"),
    ]

    def __init__(self, chave: str = "") -> None:
        super().__init__()
        self._initial_chave = chave

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            with Horizontal(id="modal-title-bar"):
                yield Static("Consultar NFS-e", id="header-bar")
                yield Button("\u2715", id="btn-modal-close")
            yield Label("Chave de acesso", classes="form-label")
            yield Input(
                value=self._initial_chave,
                placeholder="Chave de acesso da NFS-e",
                id="chave-input",
            )
            yield Label("", id="error-label")
            yield RichLog(id="query-result", wrap=True, markup=True)
            with Horizontal(classes="button-bar"):
                yield Button("\u2715 Fechar", id="btn-voltar", variant="error")
                yield Button("\u25b6 Consultar", id="btn-consultar", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-consultar":
                self._do_query()
            case "btn-voltar" | "btn-modal-close":
                self.app.pop_screen()

    def _do_query(self) -> None:
        chave = self.query_one("#chave-input", Input).value.strip()
        if not chave:
            self.query_one("#error-label", Label).update("Informe a chave de acesso")
            return
        self.query_one("#error-label", Label).update("")
        self.query_one("#query-result", RichLog).clear()
        self.notify("Consultando NFS-e…", severity="information", timeout=3)
        self._run_query(chave)

    @work(thread=True)
    def _run_query(self, chave: str) -> None:
        try:
            from emissor.config import get_cert_password, get_cert_path
            from emissor.services.adn_client import query_nfse

            env = self.app.env  # type: ignore[attr-defined]
            result = query_nfse(chave, get_cert_path(), get_cert_password(), env)
            text = json.dumps(result, indent=2, ensure_ascii=False)
            self.app.call_from_thread(self._show_result, text)
        except Exception as e:
            self.app.call_from_thread(self._show_error, str(e))

    def _show_result(self, text: str) -> None:
        log = self.query_one("#query-result", RichLog)
        log.write(text)
        self.notify("Consulta concluída", timeout=3)

    def _show_error(self, msg: str) -> None:
        self.query_one("#error-label", Label).update(f"Erro: {msg}")
        self.notify(f"Erro: {msg}", severity="error", timeout=5)

    def action_go_back(self) -> None:
        self.app.pop_screen()
