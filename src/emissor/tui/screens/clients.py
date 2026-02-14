from __future__ import annotations

import re

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Static


class ClientsScreen(ModalScreen):
    """Two-phase modal: list clients → add/edit client form."""

    BINDINGS = [
        Binding("escape", "go_back", "Voltar"),
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
                    yield Button("\u2716 Excluir", id="btn-delete-cliente", variant="warning")
                    yield Button("\u25b6 Novo Cliente", id="btn-novo-cliente", variant="primary")

            # Phase 2: Form
            with Container(id="client-form-container"):
                yield Label("Identificador (slug)", classes="form-label")
                yield Input(placeholder="acme-corp", id="client-slug")
                yield Label("Nome", classes="form-label")
                yield Input(placeholder="Acme Corp", id="client-nome")
                yield Label("NIF", classes="form-label")
                yield Input(placeholder="123456789", id="client-nif")
                yield Label("País", classes="form-label")
                yield Input(placeholder="US", id="client-pais", value="US")
                yield Label("Logradouro", classes="form-label")
                yield Input(placeholder="100 Main St", id="client-logradouro")
                yield Label("Número", classes="form-label")
                yield Input(placeholder="100", id="client-numero")
                yield Label("Bairro", classes="form-label")
                yield Input(placeholder="n/a", id="client-bairro", value="n/a")
                yield Label("Cidade", classes="form-label")
                yield Input(placeholder="New York", id="client-cidade")
                yield Label("Estado", classes="form-label")
                yield Input(placeholder="NY", id="client-estado")
                yield Label("CEP", classes="form-label")
                yield Input(placeholder="10001", id="client-cep")
                yield Label("", id="client-error-label")
                with Horizontal(classes="button-bar"):
                    yield Button("\u2190 Voltar", id="btn-form-back", variant="error")
                    yield Button("\u2716 Excluir", id="btn-form-delete", variant="warning")
                    yield Button("\u25b6 Salvar", id="btn-salvar-cliente", variant="success")

    def on_mount(self) -> None:
        self._show_phase("list")
        self._load_clients()

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

    def _open_new_form(self) -> None:
        self._editing_slug = None
        self._confirm_delete = None
        self._clear_form()
        self.query_one("#client-slug", Input).disabled = False
        self.query_one("#btn-form-delete", Button).display = False
        self._show_phase("form")

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
        self.query_one("#client-slug", Input).value = slug
        self.query_one("#client-nome", Input).value = data.get("nome", "")
        self.query_one("#client-nif", Input).value = data.get("nif", "")
        self.query_one("#client-pais", Input).value = data.get("pais", "US")
        self.query_one("#client-logradouro", Input).value = data.get("logradouro", "")
        self.query_one("#client-numero", Input).value = data.get("numero", "")
        self.query_one("#client-bairro", Input).value = data.get("bairro", "n/a")
        self.query_one("#client-cidade", Input).value = data.get("cidade", "")
        self.query_one("#client-estado", Input).value = data.get("estado", "")
        self.query_one("#client-cep", Input).value = data.get("cep", "")
        self._show_phase("form")

    def _clear_form(self) -> None:
        self.query_one("#client-slug", Input).value = ""
        self.query_one("#client-nome", Input).value = ""
        self.query_one("#client-nif", Input).value = ""
        self.query_one("#client-pais", Input).value = "US"
        self.query_one("#client-logradouro", Input).value = ""
        self.query_one("#client-numero", Input).value = ""
        self.query_one("#client-bairro", Input).value = "n/a"
        self.query_one("#client-cidade", Input).value = ""
        self.query_one("#client-estado", Input).value = ""
        self.query_one("#client-cep", Input).value = ""
        self.query_one("#client-error-label", Label).update("")

    def _do_save(self) -> None:
        error_label = self.query_one("#client-error-label", Label)
        error_label.update("")

        slug = self.query_one("#client-slug", Input).value.strip()
        nome = self.query_one("#client-nome", Input).value.strip()
        nif = self.query_one("#client-nif", Input).value.strip()
        pais = self.query_one("#client-pais", Input).value.strip()
        logradouro = self.query_one("#client-logradouro", Input).value.strip()
        numero = self.query_one("#client-numero", Input).value.strip()
        bairro = self.query_one("#client-bairro", Input).value.strip()
        cidade = self.query_one("#client-cidade", Input).value.strip()
        estado = self.query_one("#client-estado", Input).value.strip()
        cep = self.query_one("#client-cep", Input).value.strip()

        errors: list[str] = []
        if not slug or not re.match(r"^[a-z0-9_-]+$", slug):
            errors.append("Slug: apenas letras minúsculas, números, _ e -")
        if not nome:
            errors.append("Nome obrigatório")
        if not nif:
            errors.append("NIF obrigatório")
        if not logradouro:
            errors.append("Logradouro obrigatório")
        if not numero:
            errors.append("Número obrigatório")
        if not cidade:
            errors.append("Cidade obrigatória")
        if not estado:
            errors.append("Estado obrigatório")
        if not cep:
            errors.append("CEP obrigatório")

        # Check slug uniqueness for new clients
        if not self._editing_slug and not errors:
            from emissor.config import list_clients

            if slug in list_clients():
                errors.append("Slug já existe")

        if errors:
            error_label.update(" | ".join(errors))
            return

        data = {
            "nif": nif,
            "nome": nome,
            "pais": pais or "US",
            "logradouro": logradouro,
            "numero": numero,
            "bairro": bairro or "n/a",
            "cidade": cidade,
            "estado": estado,
            "cep": cep,
        }
        self._run_save(slug, data)

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
