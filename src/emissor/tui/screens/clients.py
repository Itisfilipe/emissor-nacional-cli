from __future__ import annotations

import re

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Select, Static

from emissor.tui.options import MEC_AF_COMEX_P_OPTIONS, MEC_AF_COMEX_T_OPTIONS

# Mapping of (widget_id, dict_key, default_value) for Input fields in the client form.
# Used by _fill_form, _clear_form, and _do_save to avoid repeating the same field list.
_INPUT_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("client-slug", "slug", ""),
    ("client-nome", "nome", ""),
    ("client-nif", "nif", ""),
    ("client-pais", "pais", "US"),
    ("client-logradouro", "logradouro", ""),
    ("client-numero", "numero", ""),
    ("client-bairro", "bairro", "n/a"),
    ("client-cidade", "cidade", ""),
    ("client-estado", "estado", ""),
    ("client-cep", "cep", ""),
    ("client-complemento", "complemento", ""),
)

_SELECT_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("client-mec-af-comex-p", "mec_af_comex_p", "02"),
    ("client-mec-af-comex-t", "mec_af_comex_t", "02"),
)


class ClientsScreen(ModalScreen):
    """Two-phase modal: list clients → add/edit client form."""

    BINDINGS = [
        Binding("escape", "go_back", "Voltar"),
        Binding("q", "go_back", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._phase = "list"
        self._editing_slug: str | None = None
        self._confirm_delete: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            with Horizontal(id="modal-title-bar"):
                yield Static("Clientes", id="header-bar")
                yield Button("\u2715", id="btn-modal-close")

            # Phase 1: List
            with Container(id="clients-list-container"):
                yield DataTable(id="clients-table", cursor_type="row")
                with Horizontal(classes="button-bar"):
                    yield Button("\u2715 Fechar", id="btn-clients-close", variant="error")
                    yield Button(
                        "\u25b6 Editar",
                        id="btn-edit-cliente",
                        tooltip="Editar cliente selecionado",
                    )
                    yield Button(
                        "\u2716 Excluir",
                        id="btn-delete-cliente",
                        variant="warning",
                        tooltip="Excluir cliente selecionado",
                    )
                    yield Button(
                        "\u25b6 Novo Cliente",
                        id="btn-novo-cliente",
                        variant="primary",
                        tooltip="Cadastrar novo cliente",
                    )

            # Phase 2: Form
            with Container(id="client-form-container"):
                yield Label("Identificador (slug)", classes="form-label")
                yield Input(
                    placeholder="acme-corp",
                    id="client-slug",
                    tooltip="Identificador único do cliente (letras minúsculas, números, _ e -)",
                )
                yield Label("Nome", classes="form-label")
                yield Input(
                    placeholder="Acme Corp",
                    id="client-nome",
                    tooltip="Nome ou razão social do cliente",
                )
                yield Label("NIF", classes="form-label")
                yield Input(
                    placeholder="123456789",
                    id="client-nif",
                    tooltip="Número de Identificação Fiscal no país de origem",
                )
                yield Label("País", classes="form-label")
                yield Input(
                    placeholder="US",
                    id="client-pais",
                    value="US",
                    tooltip="Código ISO 3166-1 alfa-2 do país (ex: US, DE, GB)",
                )
                yield Label("Logradouro", classes="form-label")
                yield Input(
                    placeholder="100 Main St",
                    id="client-logradouro",
                    tooltip="Endereço: rua ou avenida",
                )
                yield Label("Número", classes="form-label")
                yield Input(
                    placeholder="100",
                    id="client-numero",
                    tooltip="Número do endereço",
                )
                yield Label("Bairro", classes="form-label")
                yield Input(
                    placeholder="n/a",
                    id="client-bairro",
                    value="n/a",
                    tooltip="Bairro ou distrito",
                )
                yield Label("Cidade", classes="form-label")
                yield Input(
                    placeholder="New York",
                    id="client-cidade",
                    tooltip="Cidade",
                )
                yield Label("Estado", classes="form-label")
                yield Input(
                    placeholder="NY",
                    id="client-estado",
                    tooltip="Estado ou província (sigla)",
                )
                yield Label("CEP", classes="form-label")
                yield Input(
                    placeholder="10001",
                    id="client-cep",
                    tooltip="Código postal / ZIP code",
                )
                yield Label("Complemento", classes="form-label")
                yield Input(
                    placeholder="Sala 101",
                    id="client-complemento",
                    tooltip="Complemento do endereço (sala, andar, etc.)",
                )
                yield Label("Mecanismo de afastamento do COMEX (prestador)", classes="form-label")
                yield Select(
                    MEC_AF_COMEX_P_OPTIONS,
                    id="client-mec-af-comex-p",
                    value="02",
                    allow_blank=False,
                )
                yield Label("Mecanismo de afastamento do COMEX (tomador)", classes="form-label")
                yield Select(
                    MEC_AF_COMEX_T_OPTIONS,
                    id="client-mec-af-comex-t",
                    value="02",
                    allow_blank=False,
                )
                yield Label("", id="client-error-label")
                with Horizontal(classes="button-bar"):
                    yield Button("\u2190 Voltar", id="btn-form-back", variant="error")
                    yield Button(
                        "\u2716 Excluir",
                        id="btn-form-delete",
                        variant="warning",
                        tooltip="Excluir este cliente permanentemente",
                    )
                    yield Button(
                        "\u25b6 Salvar",
                        id="btn-salvar-cliente",
                        variant="success",
                        tooltip="Salvar dados do cliente em config/",
                    )

    def on_mount(self) -> None:
        self._show_phase("list")
        self._load_clients()
        self.query_one("#clients-table", DataTable).focus()

    def _show_phase(self, phase: str) -> None:
        self._phase = phase
        self.query_one("#clients-list-container").display = phase == "list"
        self.query_one("#client-form-container").display = phase == "form"

    @work(thread=True)
    def _load_clients(self) -> None:
        try:
            from emissor.config import list_clients, load_client

            slugs = list_clients()
            rows = []
            for slug in slugs:
                try:
                    data = load_client(slug)
                    nome = data.get("nome", "")
                    nif = data.get("nif", "")
                    pais = data.get("pais", "")
                    rows.append((slug, nome, nif, pais))
                except Exception:
                    rows.append((slug, "erro", "", ""))
        except Exception:
            rows = []
        self.app.call_from_thread(self._populate_table, rows)

    def _populate_table(self, rows: list[tuple[str, str, str, str]]) -> None:
        table = self.query_one("#clients-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Slug", "Nome", "NIF", "País")
        for slug, nome, nif, pais in rows:
            table.add_row(slug, nome, nif, pais, key=slug)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-clients-close" | "btn-modal-close":
                self.app.pop_screen()
            case "btn-edit-cliente":
                self._edit_selected()
            case "btn-novo-cliente":
                self._open_new_form()
            case "btn-form-back":
                self._show_phase("list")
            case "btn-salvar-cliente":
                self._do_save()
            case "btn-delete-cliente":
                self._delete_selected()
            case "btn-form-delete":
                if self._editing_slug:
                    self._request_delete(self._editing_slug)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        slug = str(event.row_key.value)
        self._open_edit_form(slug)

    def _edit_selected(self) -> None:
        """Edit the client selected in the table."""
        table = self.query_one("#clients-table", DataTable)
        if table.row_count == 0:
            self.notify("Nenhum cliente selecionado", severity="warning", timeout=3)
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        self._open_edit_form(str(row_key.value))

    def _open_new_form(self) -> None:
        self._editing_slug = None
        self._confirm_delete = None
        self._clear_form()
        self.query_one("#client-slug", Input).disabled = False
        self.query_one("#btn-form-delete", Button).display = False
        self._show_phase("form")
        self.query_one("#client-slug", Input).focus()

    def _open_edit_form(self, slug: str) -> None:
        self._editing_slug = slug
        self._confirm_delete = None
        self._clear_form()
        self.query_one("#client-slug", Input).disabled = True
        self.query_one("#btn-form-delete", Button).display = True
        self._load_client_into_form(slug)

    @work(thread=True)
    def _load_client_into_form(self, slug: str) -> None:
        try:
            from emissor.config import load_client

            data = load_client(slug)
        except Exception:
            data = {}
        self.app.call_from_thread(self._fill_form, slug, data)

    def _fill_form(self, slug: str, data: dict) -> None:
        merged = {**data, "slug": slug}
        for widget_id, key, default in _INPUT_FIELDS:
            self.query_one(f"#{widget_id}", Input).value = merged.get(key, default)
        for widget_id, key, default in _SELECT_FIELDS:
            self.query_one(f"#{widget_id}", Select).value = str(merged.get(key, default)).zfill(2)
        self._show_phase("form")
        self.query_one("#client-nome", Input).focus()

    def _clear_form(self) -> None:
        for widget_id, _, default in _INPUT_FIELDS:
            self.query_one(f"#{widget_id}", Input).value = default
        for widget_id, _, default in _SELECT_FIELDS:
            self.query_one(f"#{widget_id}", Select).value = default
        self.query_one("#client-error-label", Label).update("")

    def _read_form_values(self) -> dict[str, str]:
        """Read all form widget values into a dict keyed by field name."""
        values: dict[str, str] = {}
        for widget_id, key, _ in _INPUT_FIELDS:
            values[key] = self.query_one(f"#{widget_id}", Input).value.strip()
        for widget_id, key, _ in _SELECT_FIELDS:
            values[key] = str(self.query_one(f"#{widget_id}", Select).value)
        return values

    def _do_save(self) -> None:
        error_label = self.query_one("#client-error-label", Label)
        error_label.update("")

        v = self._read_form_values()
        errors: list[str] = []
        if not v["slug"] or not re.match(r"^[a-z0-9_-]+$", v["slug"]):
            errors.append("Slug: apenas letras minúsculas, números, _ e -")
        if not v["nome"]:
            errors.append("Nome obrigatório")
        if not v["nif"]:
            errors.append("NIF obrigatório")
        if not v["logradouro"]:
            errors.append("Logradouro obrigatório")
        if not v["numero"]:
            errors.append("Número obrigatório")
        if not v["cidade"]:
            errors.append("Cidade obrigatória")
        if not v["estado"]:
            errors.append("Estado obrigatório")
        if not v["cep"]:
            errors.append("CEP obrigatório")

        # Check slug uniqueness for new clients
        if not self._editing_slug and not errors:
            from emissor.config import list_clients

            if v["slug"] in list_clients():
                errors.append("Slug já existe")

        if errors:
            error_label.update(" | ".join(errors))
            return

        data: dict[str, str] = {
            "nif": v["nif"],
            "nome": v["nome"],
            "pais": v["pais"] or "US",
            "logradouro": v["logradouro"],
            "numero": v["numero"],
            "bairro": v["bairro"] or "n/a",
            "cidade": v["cidade"],
            "estado": v["estado"],
            "cep": v["cep"],
        }
        if v["complemento"]:
            data["complemento"] = v["complemento"]
        data["mec_af_comex_p"] = v["mec_af_comex_p"] or "02"
        data["mec_af_comex_t"] = v["mec_af_comex_t"] or "02"
        self._run_save(v["slug"], data)

    @work(thread=True)
    def _run_save(self, slug: str, data: dict) -> None:
        try:
            from emissor.config import save_client

            save_client(slug, data)
            self.app.call_from_thread(self._on_save_done, slug)
        except Exception as e:
            self.app.call_from_thread(self._on_save_error, str(e))

    def _on_save_done(self, slug: str) -> None:
        self.notify(f"Cliente '{slug}' salvo com sucesso", timeout=3)
        self._show_phase("list")
        self._load_clients()

    def _on_save_error(self, msg: str) -> None:
        self.query_one("#client-error-label", Label).update(f"Erro: {msg}")

    # --- Delete ---

    def _delete_selected(self) -> None:
        """Delete the client selected in the table."""
        table = self.query_one("#clients-table", DataTable)
        if table.row_count == 0:
            self.notify("Nenhum cliente selecionado", severity="warning", timeout=3)
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        slug = str(row_key.value)
        self._request_delete(slug)

    def _request_delete(self, slug: str) -> None:
        """First press = ask confirmation; second press = execute delete."""
        if self._confirm_delete == slug:
            self._run_delete(slug)
        else:
            self._confirm_delete = slug
            self.notify(
                f"Pressione novamente para confirmar exclusão de '{slug}'",
                severity="warning",
                timeout=4,
            )

    @work(thread=True)
    def _run_delete(self, slug: str) -> None:
        try:
            from emissor.config import delete_client

            delete_client(slug)
            self.app.call_from_thread(self._on_delete_done, slug)
        except Exception as e:
            self.app.call_from_thread(self._on_delete_error, str(e))

    def _on_delete_done(self, slug: str) -> None:
        self._confirm_delete = None
        self.notify(f"Cliente '{slug}' excluído", timeout=3)
        self._show_phase("list")
        self._load_clients()

    def _on_delete_error(self, msg: str) -> None:
        self._confirm_delete = None
        self.notify(f"Erro ao excluir: {msg}", severity="error", timeout=5)

    def action_go_back(self) -> None:
        self._confirm_delete = None
        if self._phase == "form":
            self._show_phase("list")
        else:
            self.app.pop_screen()
