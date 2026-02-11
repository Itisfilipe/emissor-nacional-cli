from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Select, Static

if TYPE_CHECKING:
    from emissor.services.emission import PreparedDPS


class NewInvoiceScreen(ModalScreen):
    """Three-phase screen: form -> preview -> result."""

    BINDINGS = [
        Binding("escape", "go_back", "Voltar"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._prepared: PreparedDPS | None = None
        self._phase = "form"
        self._result_ch_nfse: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            with Horizontal(id="modal-title-bar"):
                yield Static("Nova NFS-e", id="header-bar")
                yield Button("\u2715", id="btn-modal-close")

            # Phase 1: Form
            with Container(id="form-container"):
                yield Label("Cliente", classes="form-label")
                yield Select([], id="client-select", prompt="Selecione o cliente")
                yield Label("Valor BRL", classes="form-label")
                yield Input(placeholder="19684.93", id="valor-brl")
                yield Label("Valor USD", classes="form-label")
                yield Input(placeholder="3640.00", id="valor-usd")
                yield Label("Competência (YYYY-MM-DD)", classes="form-label")
                yield Input(placeholder="2025-12-30", id="competencia")
                yield Label("Intermediário", classes="form-label")
                yield Select([], id="intermediario-select", prompt="Nenhum")
                with Horizontal(classes="button-bar"):
                    yield Button("\u2715 Fechar", id="btn-form-voltar")
                    yield Button("\u25b6 Preparar", id="btn-preparar", variant="primary")
                yield Label("", id="error-label")

            # Phase 2: Preview
            with Container(id="preview-container"):
                yield DataTable(id="preview-table", show_header=False)
                with Horizontal(classes="button-bar"):
                    yield Button("\u2190 Voltar", id="btn-preview-voltar")
                    yield Button("\u2913 Salvar XML", id="btn-salvar", variant="warning")
                    yield Button("\u2191 Enviar para SEFIN", id="btn-enviar", variant="primary")
                yield Label("", id="status-label")

            # Phase 3: Result
            with Container(id="result-container"):
                yield Label("", id="result-info")
                with Horizontal(classes="button-bar"):
                    yield Button("\u2715 Fechar", id="btn-result-dashboard")
                    yield Button("\u2913 Baixar PDF", id="btn-result-pdf")
                    yield Button("\u25b6 Consultar", id="btn-result-consultar")

    def on_mount(self) -> None:
        self._show_phase("form")
        self._load_clients()

    def _show_phase(self, phase: str) -> None:
        self._phase = phase
        self.query_one("#form-container").display = phase == "form"
        self.query_one("#preview-container").display = phase == "preview"
        self.query_one("#result-container").display = phase == "result"
        if phase == "form":
            self.query_one("#btn-preparar", Button).disabled = False

    @work(thread=True)
    def _load_clients(self) -> None:
        try:
            from emissor.config import list_clients

            clients = list_clients()
        except Exception:
            clients = []
        self.app.call_from_thread(self._populate_selects, clients)

    def _populate_selects(self, clients: list[str]) -> None:
        options = [(c, c) for c in clients]
        self.query_one("#client-select", Select).set_options(options)
        inter_options = [("Nenhum", "__none__"), *options]
        self.query_one("#intermediario-select", Select).set_options(inter_options)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-preparar":
                self._do_prepare()
            case "btn-form-voltar" | "btn-result-dashboard" | "btn-modal-close":
                self.app.pop_screen()
            case "btn-enviar":
                self._do_submit()
            case "btn-salvar":
                self._do_save_xml()
            case "btn-preview-voltar":
                self._show_phase("form")
            case "btn-result-pdf":
                self._open_pdf()
            case "btn-result-consultar":
                self._open_query()

    def _do_prepare(self) -> None:
        from emissor.utils.validators import validate_date, validate_monetary

        error_label = self.query_one("#error-label", Label)
        error_label.update("")

        client_sel = self.query_one("#client-select", Select)
        if client_sel.value is Select.BLANK:
            error_label.update("Selecione um cliente")
            return
        client_name = str(client_sel.value)

        valor_brl = self.query_one("#valor-brl", Input).value.strip()
        valor_usd = self.query_one("#valor-usd", Input).value.strip()
        competencia = self.query_one("#competencia", Input).value.strip()

        try:
            valor_brl = validate_monetary(valor_brl)
            valor_usd = validate_monetary(valor_usd)
            competencia = validate_date(competencia)
        except ValueError as e:
            error_label.update(str(e))
            return

        inter_sel = self.query_one("#intermediario-select", Select)
        intermediario = None
        if inter_sel.value is not Select.BLANK and inter_sel.value != "__none__":
            intermediario = str(inter_sel.value)

        self.query_one("#btn-preparar", Button).disabled = True
        self.notify("Preparando NFS-e…", severity="information", timeout=3)
        self._run_prepare(client_name, valor_brl, valor_usd, competencia, intermediario)

    @work(thread=True)
    def _run_prepare(
        self,
        client_name: str,
        valor_brl: str,
        valor_usd: str,
        competencia: str,
        intermediario: str | None,
    ) -> None:
        try:
            from emissor.services.emission import prepare

            env = self.app.env  # type: ignore[attr-defined]
            prepared = prepare(
                client_name=client_name,
                valor_brl=valor_brl,
                valor_usd=valor_usd,
                competencia=competencia,
                env=env,
                intermediario=intermediario,
            )
            self._prepared = prepared
            self.app.call_from_thread(
                self._show_preview, prepared, valor_brl, valor_usd, competencia
            )
        except Exception as e:
            self.app.call_from_thread(self._set_error, f"Erro ao preparar: {e}")

    def _show_preview(self, prepared, valor_brl: str, valor_usd: str, competencia: str) -> None:
        from emissor.utils.formatters import format_brl, format_usd

        table = self.query_one("#preview-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Campo", "Valor")
        table.add_row("Prestador", f"{prepared.emitter.razao_social} ({prepared.emitter.cnpj})")
        table.add_row("Tomador", f"{prepared.client.nome} (NIF: {prepared.client.nif})")
        if prepared.intermediary:
            inter = prepared.intermediary
            table.add_row("Intermediário", f"{inter.nome} ({inter.nif})")
        table.add_row("Valor BRL", format_brl(valor_brl))
        table.add_row("Valor USD", format_usd(valor_usd))
        table.add_row("Competência", competencia)
        table.add_row("nDPS", str(prepared.n_dps))
        env = self.app.env  # type: ignore[attr-defined]
        table.add_row("Ambiente", env)

        self.query_one("#status-label", Label).update("")
        self._show_phase("preview")
        self.notify("NFS-e preparada — revise os dados antes de enviar", timeout=3)

    def _set_error(self, msg: str) -> None:
        self.query_one("#error-label", Label).update(msg)
        self.query_one("#btn-preparar", Button).disabled = False

    def _do_submit(self) -> None:
        if not self._prepared:
            return
        self._set_submit_buttons_enabled(False)
        self.notify("Enviando para SEFIN…", severity="information", timeout=5)
        self._run_submit()

    @work(thread=True)
    def _run_submit(self) -> None:
        prepared = self._prepared
        if prepared is None:
            return
        try:
            from emissor.services.emission import submit

            result = submit(prepared)
            self.app.call_from_thread(self._show_result, result)
        except Exception as e:
            self.app.call_from_thread(self._on_submit_error, f"Erro ao enviar: {e}")

    def _show_result(self, result: dict) -> None:
        resp = result.get("response") or {}
        ch_nfse = resp.get("chNFSe", "N/A")
        n_nfse = resp.get("nNFSe", "N/A")
        saved = result.get("saved_to", "")

        text = f"NFS-e emitida com sucesso!\n\nChave de acesso: {ch_nfse}\nnNFSe: {n_nfse}"
        if saved:
            text += f"\nXML salvo em: {saved}"

        self._result_ch_nfse = ch_nfse
        self.query_one("#result-info", Label).update(text)
        self._show_phase("result")
        self.notify("NFS-e emitida com sucesso!", severity="information", timeout=5)

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-label", Label).update(msg)

    def _set_submit_buttons_enabled(self, enabled: bool) -> None:
        self.query_one("#btn-enviar", Button).disabled = not enabled
        self.query_one("#btn-salvar", Button).disabled = not enabled

    def _on_submit_error(self, msg: str) -> None:
        self._set_status(msg)
        self._set_submit_buttons_enabled(True)
        self.notify(msg, severity="error", timeout=5)

    def _on_save_success(self, msg: str) -> None:
        self._set_status(msg)
        self._set_submit_buttons_enabled(True)
        self.notify(msg, severity="information", timeout=3)

    def _do_save_xml(self) -> None:
        if not self._prepared:
            return
        self._set_submit_buttons_enabled(False)
        self.notify("Salvando XML…", severity="information", timeout=3)
        self._run_save_xml()

    @work(thread=True)
    def _run_save_xml(self) -> None:
        prepared = self._prepared
        if prepared is None:
            return
        try:
            from emissor.services.emission import save_xml

            path = save_xml(prepared)
            self.app.call_from_thread(self._on_save_success, f"XML salvo em: {path}")
        except Exception as e:
            self.app.call_from_thread(self._on_submit_error, f"Erro ao salvar: {e}")

    def _open_pdf(self) -> None:
        if not self._result_ch_nfse or self._result_ch_nfse == "N/A":
            return
        from emissor.tui.screens.download_pdf import DownloadPdfScreen

        self.app.push_screen(DownloadPdfScreen(chave=self._result_ch_nfse))

    def _open_query(self) -> None:
        if not self._result_ch_nfse or self._result_ch_nfse == "N/A":
            return
        from emissor.tui.screens.query import QueryScreen

        self.app.push_screen(QueryScreen(chave=self._result_ch_nfse))

    def action_go_back(self) -> None:
        if self._phase == "preview":
            self._show_phase("form")
        else:
            self.app.pop_screen()
