from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


def _unique_path(path: Path) -> Path:
    """Return a non-conflicting path by appending _1, _2, etc. if needed."""
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    counter = 1
    candidate = parent / f"{stem}_{counter}{suffix}"
    while candidate.exists():
        counter += 1
        candidate = parent / f"{stem}_{counter}{suffix}"
    return candidate


class DownloadPdfScreen(ModalScreen):
    """Download DANFSE PDF for an NFS-e."""

    BINDINGS = [
        Binding("escape", "go_back", "Voltar"),
    ]

    def __init__(self, chave: str = "") -> None:
        super().__init__()
        self._initial_chave = chave

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            with Horizontal(id="modal-title-bar"):
                yield Static("Baixar PDF (DANFSE)", id="header-bar")
                yield Button("\u2715", id="btn-modal-close")
            yield Label("Chave de acesso", classes="form-label")
            yield Input(
                value=self._initial_chave,
                placeholder="Chave de acesso da NFS-e",
                id="chave-input",
            )
            yield Label("Caminho de saída", classes="form-label")
            default_output = f"{self._initial_chave}.pdf" if self._initial_chave else ""
            yield Input(value=default_output, placeholder="output.pdf", id="output-input")
            yield Label("", id="error-label")
            yield Label("", id="status-label")
            with Horizontal(classes="button-bar"):
                yield Button("\u2715 Fechar", id="btn-voltar", variant="error")
                yield Button("\u2913 Baixar", id="btn-baixar", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#chave-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_download()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-baixar":
                self._do_download()
            case "btn-voltar" | "btn-modal-close":
                self.app.pop_screen()

    def _do_download(self) -> None:
        chave = self.query_one("#chave-input", Input).value.strip()
        output = self.query_one("#output-input", Input).value.strip()

        if not chave:
            self.query_one("#error-label", Label).update("Informe a chave de acesso")
            return
        if not output:
            output = f"{chave}.pdf"

        self.query_one("#error-label", Label).update("")
        self.query_one("#status-label", Label).update("Baixando…")
        self.notify("Baixando PDF…", severity="information", timeout=3)
        self._run_download(chave, output)

    @work(thread=True)
    def _run_download(self, chave: str, output: str) -> None:
        try:
            from emissor.config import get_cert_password, get_cert_path
            from emissor.services.adn_client import download_danfse

            env = self.app.env  # type: ignore[attr-defined]
            content = download_danfse(chave, get_cert_path(), get_cert_password(), env)
            final_path = _unique_path(Path(output))
            final_path.write_bytes(content)
            self.app.call_from_thread(self._show_success, str(final_path))
        except Exception as e:
            self.app.call_from_thread(self._show_error, str(e))

    def _show_success(self, path: str) -> None:
        self.query_one("#status-label", Label).update(f"PDF salvo em: {path}")
        self.query_one("#error-label", Label).update("")
        self.notify(f"PDF salvo em: {path}", timeout=5)

    def _show_error(self, msg: str) -> None:
        self.query_one("#status-label", Label).update("")
        self.query_one("#error-label", Label).update(f"Erro: {msg}")
        self.notify(f"Erro: {msg}", severity="error", timeout=5)

    def action_go_back(self) -> None:
        self.app.pop_screen()
