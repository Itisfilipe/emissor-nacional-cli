from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Label,
    MaskedInput,
    OptionList,
    Select,
    Static,
)

from emissor.services.exceptions import SefinRejectError
from emissor.tui.options import (
    MD_PRESTACAO_OPTIONS,
    MDIC_OPTIONS,
    MEC_AF_COMEX_P_OPTIONS,
    MEC_AF_COMEX_T_OPTIONS,
    MOV_TEMP_BENS_OPTIONS,
    TP_RET_ISSQN_OPTIONS,
    TRIB_ISSQN_OPTIONS,
    VINC_PREST_OPTIONS,
)

if TYPE_CHECKING:
    from emissor.services.emission import PreparedDPS

logger = logging.getLogger(__name__)

# Mapping from override field name to CSS selector, split by widget type.
# Used both when populating the form from saved overrides and when collecting
# values back from the form.
_INPUT_FIELDS: dict[str, str] = {
    "x_desc_serv": "#x-desc-serv",
    "c_trib_nac": "#c-trib-nac",
    "c_nbs": "#c-nbs",
    "tp_moeda": "#tp-moeda",
    "c_pais_result": "#c-pais-result",
    "cst_pis_cofins": "#cst-pis-cofins",
    "p_tot_trib_fed": "#p-tot-trib-fed",
    "p_tot_trib_est": "#p-tot-trib-est",
    "p_tot_trib_mun": "#p-tot-trib-mun",
}
_SELECT_FIELDS: dict[str, str] = {
    "md_prestacao": "#md-prestacao",
    "vinc_prest": "#vinc-prest",
    "mec_af_comex_p": "#mec-af-comex-p",
    "mec_af_comex_t": "#mec-af-comex-t",
    "mov_temp_bens": "#mov-temp-bens",
    "mdic": "#mdic",
    "trib_issqn": "#trib-issqn",
    "tp_ret_issqn": "#tp-ret-issqn",
}

STEPS = ["pessoas", "servico", "valores", "revisao"]
STEP_LABELS = [
    "Passo 1/4 — Pessoas",
    "Passo 2/4 — Serviço",
    "Passo 3/4 — Valores",
    "Passo 4/4 — Revisão",
]


class NewInvoiceScreen(ModalScreen):
    """Four-step wizard: Pessoas -> Serviço -> Valores -> Revisão -> Result."""

    BINDINGS = [
        Binding("escape", "go_back", "Voltar"),
        Binding("q", "go_back", show=False),
    ]

    def __init__(self, prefill: dict | None = None) -> None:
        super().__init__()
        self._prepared: PreparedDPS | None = None
        self._step = 1
        self._phase = "wizard"  # "wizard" or "result"
        self._result_ch_nfse: str | None = None
        self._prefill = prefill

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            with Horizontal(id="modal-title-bar"):
                yield Static("Nova NFS-e", id="header-bar")
                yield Button("\u2715", id="btn-modal-close")

            yield Static(STEP_LABELS[0], id="step-indicator")

            # Step 1 — Pessoas
            with Container(id="step-1-pessoas"):
                yield Label("Cliente", classes="form-label")
                yield Select(
                    [],
                    id="client-select",
                    prompt="Selecione o cliente",
                    tooltip="Tomador: empresa ou pessoa que recebe o serviço",
                )
                yield Label("Intermediário", classes="form-label")
                yield Select(
                    [],
                    id="intermediario-select",
                    prompt="Nenhum",
                    tooltip="Terceiro que intermedia a prestação (opcional)",
                )
                yield Label("Competência", classes="form-label")
                yield MaskedInput(
                    template="00/00/0000",
                    id="competencia",
                    tooltip="Data da prestação do serviço (DD/MM/AAAA)",
                )
                yield Label("", id="error-label")
                with Horizontal(classes="button-bar"):
                    yield Button("\u2715 Fechar", id="btn-form-voltar", variant="error")
                    yield Button("\u25b6 Próximo", id="btn-step1-next", variant="primary")

            # Step 2 — Serviço
            with Container(id="step-2-servico"):
                yield Label("Descrição do Serviço", classes="form-label")
                yield Input(
                    id="x-desc-serv",
                    tooltip="Texto livre descrevendo o serviço prestado (xDescServ)",
                )
                yield Label("Código Tributação Nacional", classes="form-label")
                yield Input(
                    id="c-trib-nac",
                    tooltip="Código da NBS de tributação nacional (cTribNac)",
                )
                yield Label("Código NBS", classes="form-label")
                yield Input(
                    id="c-nbs",
                    tooltip="Código da Nomenclatura Brasileira de Serviços (cNBS)",
                )
                yield Label("Modalidade Prestação", classes="form-label")
                yield Select(
                    MD_PRESTACAO_OPTIONS,
                    id="md-prestacao",
                    value="4",
                    allow_blank=False,
                )
                yield Label("Vínculo Prestador", classes="form-label")
                yield Select(
                    VINC_PREST_OPTIONS,
                    id="vinc-prest",
                    value="0",
                    allow_blank=False,
                )
                yield Label("Tipo Moeda", classes="form-label")
                yield Input(
                    id="tp-moeda",
                    tooltip="Código ISO 4217 da moeda estrangeira (ex: 220=USD, 978=EUR)",
                )
                yield Label("Mecanismo AF COMEX Prestador", classes="form-label")
                yield Select(
                    MEC_AF_COMEX_P_OPTIONS,
                    id="mec-af-comex-p",
                    value="02",
                    allow_blank=False,
                )
                yield Label("Mecanismo AF COMEX Tomador", classes="form-label")
                yield Select(
                    MEC_AF_COMEX_T_OPTIONS,
                    id="mec-af-comex-t",
                    value="02",
                    allow_blank=False,
                )
                yield Label("Movimento Temporário Bens", classes="form-label")
                yield Select(
                    MOV_TEMP_BENS_OPTIONS,
                    id="mov-temp-bens",
                    value="1",
                    allow_blank=False,
                )
                yield Label("MDIC", classes="form-label")
                yield Select(
                    MDIC_OPTIONS,
                    id="mdic",
                    value="0",
                    allow_blank=False,
                )
                yield Label("País Resultado", classes="form-label")
                yield Input(
                    id="c-pais-result",
                    tooltip="Código ISO 3166-1 alfa-2 do país do resultado (ex: US, DE)",
                )
                yield Label("", id="error-label-step2")
                with Horizontal(classes="button-bar"):
                    yield Button("\u2190 Voltar", id="btn-step2-back")
                    yield Button("\u25b6 Próximo", id="btn-step2-next", variant="primary")

            # Step 3 — Valores
            with Container(id="step-3-valores"):
                yield Label("Valor BRL", classes="form-label")
                yield Input(
                    placeholder="19684.93",
                    id="valor-brl",
                    tooltip="Valor do serviço em reais (vServ)",
                )
                yield Label("Valor USD", classes="form-label")
                yield Input(
                    placeholder="3640.00",
                    id="valor-usd",
                    tooltip="Valor do serviço na moeda estrangeira (vServMoeda)",
                )
                yield Label("Tributação ISSQN", classes="form-label")
                yield Select(
                    TRIB_ISSQN_OPTIONS,
                    id="trib-issqn",
                    value="3",
                    allow_blank=False,
                )
                yield Label("Tipo Retenção ISSQN", classes="form-label")
                yield Select(
                    TP_RET_ISSQN_OPTIONS,
                    id="tp-ret-issqn",
                    value="1",
                    allow_blank=False,
                )
                yield Label("CST PIS/COFINS", classes="form-label")
                yield Input(
                    id="cst-pis-cofins",
                    placeholder="08",
                    tooltip="Código de situação tributária (ex: 01, 06, 08, 49, 99)",
                )
                yield Label("% Total Tributos Federais", classes="form-label")
                yield Input(
                    id="p-tot-trib-fed",
                    placeholder="0.00",
                    tooltip="Percentual estimado de tributos federais (Lei 12.741)",
                )
                yield Label("% Total Tributos Estaduais", classes="form-label")
                yield Input(
                    id="p-tot-trib-est",
                    placeholder="0.00",
                    tooltip="Percentual estimado de tributos estaduais (Lei 12.741)",
                )
                yield Label("% Total Tributos Municipais", classes="form-label")
                yield Input(
                    id="p-tot-trib-mun",
                    placeholder="0.00",
                    tooltip="Percentual estimado de tributos municipais (Lei 12.741)",
                )
                yield Label("", id="error-label-step3")
                with Horizontal(classes="button-bar"):
                    yield Button("\u2190 Voltar", id="btn-step3-back")
                    yield Button("\u25b6 Preparar", id="btn-preparar", variant="primary")

            # Step 4 — Revisão
            with Container(id="step-4-revisao"):
                yield DataTable(id="preview-table", show_header=False)
                yield Label("", id="status-label")
                with Horizontal(classes="button-bar"):
                    yield Button("\u2190 Voltar", id="btn-preview-voltar")
                    yield Button("\u2913 Salvar XML", id="btn-salvar", variant="warning")
                    yield Button("\u2191 Enviar para SEFIN", id="btn-enviar", variant="success")

            # Result
            with Container(id="result-container"):
                yield Label("", id="result-info")
                with Horizontal(classes="button-bar"):
                    yield Button("\u2715 Fechar", id="btn-result-dashboard", variant="error")
                    yield Button("\u2913 Baixar PDF", id="btn-result-pdf", variant="primary")
                    yield Button("\u25b6 Consultar", id="btn-result-consultar")

    def on_mount(self) -> None:
        self._show_step(1)
        self._load_clients()

    STEP_FOCUS = {
        1: "#client-select",
        2: "#x-desc-serv",
        3: "#valor-brl",
    }

    def _show_step(self, step: int) -> None:
        self._step = step
        self._phase = "wizard"
        for i, name in enumerate(STEPS, 1):
            self.query_one(f"#step-{i}-{name}").display = i == step
        self.query_one("#result-container").display = False
        self.query_one("#step-indicator").display = True
        self._update_step_indicator()
        if step == 3:
            self.query_one("#btn-preparar", Button).disabled = False
        if step in self.STEP_FOCUS:
            self.query_one(self.STEP_FOCUS[step]).focus()

    def _show_result_phase(self) -> None:
        self._phase = "result"
        for i, name in enumerate(STEPS, 1):
            self.query_one(f"#step-{i}-{name}").display = False
        self.query_one("#result-container").display = True
        self.query_one("#step-indicator").display = False

    def _update_step_indicator(self) -> None:
        self.query_one("#step-indicator", Static).update(STEP_LABELS[self._step - 1])

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
        if self._prefill:
            self._apply_prefill(clients)
        self._load_emitter_defaults()

    def _apply_prefill(self, clients: list[str]) -> None:
        pf = self._prefill
        if not pf:
            return
        slug = pf.get("client_slug", "")
        if slug and slug in clients:
            self.query_one("#client-select", Select).value = slug
        if pf.get("valor_brl"):
            self.query_one("#valor-brl", Input).value = pf["valor_brl"]
        if pf.get("valor_usd"):
            self.query_one("#valor-usd", Input).value = pf["valor_usd"]

    @work(thread=True)
    def _load_emitter_defaults(self) -> None:
        """Pre-fill Step 2 fields from emitter config."""
        try:
            from emissor.config import load_emitter
            from emissor.models.emitter import Emitter

            emitter = Emitter.from_dict(load_emitter())
            self.app.call_from_thread(self._fill_emitter_fields, emitter)
        except Exception:
            logger.debug("Failed to load emitter defaults for Step 2", exc_info=True)

    def _fill_emitter_fields(self, emitter) -> None:
        """Fill Step 2 inputs from emitter values (only if empty)."""
        field_map = {
            "#x-desc-serv": emitter.x_desc_serv,
            "#c-trib-nac": emitter.c_trib_nac,
            "#c-nbs": emitter.c_nbs,
            "#tp-moeda": emitter.tp_moeda,
            "#c-pais-result": emitter.c_pais_result,
        }
        for selector, value in field_map.items():
            inp = self.query_one(selector, Input)
            if not inp.value:
                inp.value = value

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "client-select" and event.value is not Select.BLANK:
            client_slug = str(event.value)
            self._load_client_defaults(client_slug)
            self._load_last_overrides(client_slug)

    @work(thread=True)
    def _load_client_defaults(self, client_name: str) -> None:
        """Pre-fill Step 2 COMEX fields from client config."""
        try:
            from emissor.config import load_client
            from emissor.models.client import Client

            client = Client.from_dict(load_client(client_name))
            self.app.call_from_thread(self._fill_client_fields, client)
        except Exception:
            logger.debug("Failed to load client defaults for %s", client_name, exc_info=True)

    def _fill_client_fields(self, client) -> None:
        self.query_one("#mec-af-comex-p", Select).value = client.mec_af_comex_p
        self.query_one("#mec-af-comex-t", Select).value = client.mec_af_comex_t

    @work(thread=True)
    def _load_last_overrides(self, client_slug: str) -> None:
        """Pre-fill Steps 2/3 from the last invoice for this client."""
        try:
            from emissor.utils.registry import get_last_overrides

            env = self.app.env  # type: ignore[attr-defined]
            overrides = get_last_overrides(client_slug, env)
            if overrides:
                self.app.call_from_thread(self._fill_last_overrides, overrides, client_slug)
        except Exception:
            logger.debug("Failed to load last overrides for %s", client_slug, exc_info=True)

    def _fill_last_overrides(self, overrides: dict[str, str], client_slug: str) -> None:
        """Apply override values from the last invoice to Input and Select widgets."""
        for field_name, selector in _INPUT_FIELDS.items():
            value = overrides.get(field_name)
            if value is not None:
                self.query_one(selector, Input).value = value
        for field_name, selector in _SELECT_FIELDS.items():
            value = overrides.get(field_name)
            if value is not None:
                self.query_one(selector, Select).value = value
        self.notify(
            f"Campos carregados da ultima NFS-e para {client_slug}",
            severity="information",
            timeout=3,
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            # Step 1
            case "btn-step1-next":
                self._validate_step1()
            case "btn-form-voltar" | "btn-result-dashboard" | "btn-modal-close":
                self.app.pop_screen()
            # Step 2
            case "btn-step2-back":
                self._show_step(1)
            case "btn-step2-next":
                self._validate_step2()
            # Step 3
            case "btn-step3-back":
                self._show_step(2)
            case "btn-preparar":
                self._do_prepare()
            # Step 4 (Revisão)
            case "btn-preview-voltar":
                self._show_step(3)
            case "btn-enviar":
                self._do_submit()
            case "btn-salvar":
                self._do_save_xml()
            # Result
            case "btn-result-pdf":
                self._open_pdf()
            case "btn-result-consultar":
                self._open_query()

    def _validate_step1(self) -> None:
        from datetime import datetime

        from emissor.utils.validators import validate_date

        error_label = self.query_one("#error-label", Label)
        error_label.update("")
        errors: list[str] = []

        client_sel = self.query_one("#client-select", Select)
        if client_sel.value is Select.BLANK:
            errors.append("Cliente: selecione um cliente")

        competencia_raw = self.query_one("#competencia", MaskedInput).value.strip()
        try:
            dt = datetime.strptime(competencia_raw, "%d/%m/%Y")
            validate_date(dt.strftime("%Y-%m-%d"))
        except ValueError:
            errors.append("Competência: data inválida (DD/MM/AAAA)")

        if errors:
            error_label.update(" | ".join(errors))
            return

        self._show_step(2)

    def _validate_step2(self) -> None:
        from emissor.utils.validators import (
            validate_c_nbs,
            validate_c_pais_result,
            validate_c_trib_nac,
            validate_tp_moeda,
        )

        error_label = self.query_one("#error-label-step2", Label)
        error_label.update("")
        errors: list[str] = []

        if not self.query_one("#x-desc-serv", Input).value.strip():
            errors.append("Descrição do Serviço: obrigatório")
        if not self.query_one("#c-trib-nac", Input).value.strip():
            errors.append("Código Tributação Nacional: obrigatório")

        for selector, validator in (
            ("#c-trib-nac", validate_c_trib_nac),
            ("#c-nbs", validate_c_nbs),
            ("#tp-moeda", validate_tp_moeda),
            ("#c-pais-result", validate_c_pais_result),
        ):
            val = self.query_one(selector, Input).value.strip()
            if val:
                try:
                    validator(val)
                except ValueError as e:
                    errors.append(str(e))

        if errors:
            error_label.update(" | ".join(errors))
            return

        self._show_step(3)

    def _do_prepare(self) -> None:
        from datetime import datetime

        from emissor.utils.validators import (
            validate_cst_pis_cofins,
            validate_date,
            validate_monetary,
            validate_percent,
        )

        error_label = self.query_one("#error-label-step3", Label)
        error_label.update("")
        errors: list[str] = []

        valor_brl = self.query_one("#valor-brl", Input).value.strip()
        valor_usd = self.query_one("#valor-usd", Input).value.strip()

        try:
            valor_brl = validate_monetary(valor_brl)
        except ValueError:
            errors.append("Valor BRL: valor numérico inválido")

        try:
            valor_usd = validate_monetary(valor_usd)
        except ValueError:
            errors.append("Valor USD: valor numérico inválido")

        cst = self.query_one("#cst-pis-cofins", Input).value.strip()
        if cst:
            try:
                validate_cst_pis_cofins(cst)
            except ValueError as e:
                errors.append(str(e))

        for selector in ("#p-tot-trib-fed", "#p-tot-trib-est", "#p-tot-trib-mun"):
            inp = self.query_one(selector, Input)
            val = inp.value.strip()
            if val:
                try:
                    inp.value = validate_percent(val)
                except ValueError as e:
                    errors.append(str(e))

        if errors:
            error_label.update(" | ".join(errors))
            return

        # Gather Step 1 data
        client_name = str(self.query_one("#client-select", Select).value)
        competencia_raw = self.query_one("#competencia", MaskedInput).value.strip()
        dt = datetime.strptime(competencia_raw, "%d/%m/%Y")
        competencia = dt.strftime("%Y-%m-%d")
        validate_date(competencia)

        inter_sel = self.query_one("#intermediario-select", Select)
        intermediario = None
        if inter_sel.value is not Select.BLANK and inter_sel.value != "__none__":
            intermediario = str(inter_sel.value)

        # Gather overrides from Step 2 + Step 3
        overrides = self._collect_overrides()

        self.query_one("#btn-preparar", Button).disabled = True
        self.notify("Preparando NFS-e…", severity="information", timeout=3)
        self._run_prepare(client_name, valor_brl, valor_usd, competencia, intermediario, overrides)

    def _collect_overrides(self) -> dict[str, str]:
        """Collect non-empty/non-placeholder override values from Steps 2 and 3."""
        overrides: dict[str, str] = {}
        for field_name, selector in _INPUT_FIELDS.items():
            val = self.query_one(selector, Input).value.strip()
            if val:
                overrides[field_name] = val
        for field_name, selector in _SELECT_FIELDS.items():
            sel = self.query_one(selector, Select)
            if sel.value is not Select.BLANK:
                overrides[field_name] = str(sel.value)
        return overrides

    @work(thread=True)
    def _run_prepare(
        self,
        client_name: str,
        valor_brl: str,
        valor_usd: str,
        competencia: str,
        intermediario: str | None,
        overrides: dict[str, str],
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
                overrides=overrides,
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

        # Pessoas
        table.add_row("Prestador", f"{prepared.emitter.razao_social} ({prepared.emitter.cnpj})")
        table.add_row("Tomador", f"{prepared.client.nome} (NIF: {prepared.client.nif})")
        if prepared.intermediary:
            inter = prepared.intermediary
            table.add_row("Intermediário", f"{inter.nome} ({inter.nif})")
        table.add_row("Competência", competencia)

        # Serviço
        inv = prepared.invoice
        table.add_row("─── Serviço ───", "")
        table.add_row("Descrição", inv.x_desc_serv or prepared.emitter.x_desc_serv)
        table.add_row("cTribNac", inv.c_trib_nac or prepared.emitter.c_trib_nac)
        table.add_row("cNBS", inv.c_nbs or prepared.emitter.c_nbs)
        table.add_row("tpMoeda", inv.tp_moeda or prepared.emitter.tp_moeda)

        # Valores
        table.add_row("─── Valores ───", "")
        table.add_row("Valor BRL", format_brl(valor_brl))
        table.add_row("Valor USD", format_usd(valor_usd))

        # Tributação
        table.add_row("─── Tributação ───", "")
        table.add_row("tribISSQN", inv.trib_issqn or "3")
        table.add_row("cPaisResult", inv.c_pais_result or prepared.emitter.c_pais_result)

        # Meta
        table.add_row("─── Meta ───", "")
        table.add_row("nDPS", str(prepared.n_dps))
        env = self.app.env  # type: ignore[attr-defined]
        table.add_row("Ambiente", env)

        self.query_one("#status-label", Label).update("")
        self._show_step(4)
        self.notify("NFS-e preparada — revise os dados antes de enviar", timeout=3)

    def _set_error(self, msg: str) -> None:
        self.query_one("#error-label-step3", Label).update(msg)
        self.query_one("#btn-preparar", Button).disabled = False
        self._show_step(3)

    def _do_submit(self) -> None:
        if not self._prepared:
            return
        env = self.app.env  # type: ignore[attr-defined]
        if env == "producao":
            from emissor.tui.screens.confirm import ConfirmScreen

            self.app.push_screen(
                ConfirmScreen(
                    "\u26a0 Você está emitindo uma NFS-e em PRODUÇÃO.\n\n"
                    "Esta nota terá validade fiscal e não poderá\n"
                    "ser desfeita.\n\n"
                    "Confirmar envio?"
                ),
                callback=self._on_submit_confirmed,
            )
        else:
            self._execute_submit()

    def _on_submit_confirmed(self, confirmed: bool | None) -> None:
        if confirmed:
            self._execute_submit()

    def _execute_submit(self) -> None:
        self._set_submit_buttons_enabled(False)
        self.notify("Enviando para SEFIN…", severity="information", timeout=5)
        self._run_submit()

    @work(thread=True)
    def _run_submit(self) -> None:
        prepared = self._prepared
        if prepared is None:
            return
        try:
            from emissor.services.emission import mark_failed, submit

            result = submit(prepared)
            self.app.call_from_thread(self._show_result, result)
        except SefinRejectError as e:
            mark_failed(prepared, str(e))
            self.app.call_from_thread(self._on_submit_error, f"SEFIN rejeitou a NFS-e: {e}")
        except Exception as e:
            mark_failed(prepared, str(e))
            self.app.call_from_thread(self._on_submit_error, f"Erro ao enviar: {e}")

    def _show_result(self, result: dict) -> None:
        resp = result.get("response") or {}
        ch_nfse = resp.get("chNFSe", "")
        n_nfse = resp.get("nNFSe", "N/A")
        saved = result.get("saved_to", "")

        if not ch_nfse:
            self._on_submit_error("Resposta sem chave de acesso (chNFSe)")
            return

        text = f"NFS-e emitida com sucesso!\n\nChave de acesso: {ch_nfse}\nnNFSe: {n_nfse}"
        if saved:
            text += f"\nXML salvo em: {saved}"

        self._result_ch_nfse = ch_nfse
        self.query_one("#result-info", Label).update(text)
        self._show_result_phase()
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

    def _get_result_chave(self) -> str | None:
        """Return the result chave if valid, or None."""
        ch = self._result_ch_nfse
        if not ch or ch == "N/A":
            return None
        return ch

    def _open_pdf(self) -> None:
        chave = self._get_result_chave()
        if not chave:
            return
        from emissor.tui.screens.download_pdf import DownloadPdfScreen

        self.app.push_screen(DownloadPdfScreen(chave=chave))

    def _open_query(self) -> None:
        chave = self._get_result_chave()
        if not chave:
            return
        from emissor.tui.screens.query import QueryScreen

        self.app.push_screen(QueryScreen(chave=chave))

    def on_key(self, event: Key) -> None:
        focused = self.app.focused
        if not isinstance(focused, OptionList):
            return
        match event.key:
            case "j":
                focused.action_cursor_down()
            case "k":
                focused.action_cursor_up()
            case _:
                return
        event.prevent_default()
        event.stop()

    def action_go_back(self) -> None:
        if self._phase == "result" or self._step == 1:
            self.app.pop_screen()
        elif self._step == 4:
            self._show_step(3)
        else:
            self._show_step(self._step - 1)
