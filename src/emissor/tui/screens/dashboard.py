from __future__ import annotations

import platform
import shutil
import subprocess
from datetime import datetime, timedelta

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Label, MaskedInput, Select, Static

from emissor.config import BRT


class DashboardScreen(Screen):
    """Main dashboard screen shown on startup."""

    BINDINGS = [
        # List actions — hidden from footer (have buttons above table)
        Binding("n", "new_invoice", "Nova NFS-e", show=False),
        Binding("r", "clone_invoice", "Clonar", show=False),
        Binding("c", "query", "Consultar", show=False),
        Binding("p", "download_pdf", "Baixar PDF", show=False),
        Binding("y", "copy_key", "Copiar chave", show=False),
        Binding("s", "sync", "Sincronizar", show=False),
        # Generic actions — shown in footer
        Binding("l", "clients", "Clientes"),
        Binding("v", "validate", "Validar"),
        Binding("e", "toggle_env", "Ambiente"),
        Binding("f", "focus_filter", "Filtrar"),
        Binding("h", "help", "Ajuda"),
        Binding("q", "quit", "Sair"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._all_invoices: list[dict] = []

    def compose(self) -> ComposeResult:
        env = self.app.env  # type: ignore[attr-defined]

        # Top bar: title + clickable env badge
        with Horizontal(id="top-bar"):
            yield Static("Emissor Nacional CLI", id="app-title")
            env_class = "env-homol" if env == "homologacao" else "env-prod"
            env_label = "\u21c4 HOMOLOGAÇÃO" if env == "homologacao" else "\u21c4 PRODUÇÃO"
            yield Button(
                env_label,
                id="env-badge",
                classes=env_class,
                tooltip="Alternar entre homologação e produção (e)",
            )

        # Info cards row
        with Horizontal(id="info-bar"):
            with Vertical(id="card-emitter", classes="info-card"):
                yield Label("Emitente", classes="card-title")
                yield Label("\u2026", id="emitter-info", classes="card-value")
            with Vertical(id="card-cert", classes="info-card"):
                yield Label("Certificado", classes="card-title")
                yield Label("\u2026", id="cert-info", classes="card-value")
            with Vertical(id="card-seq", classes="info-card"):
                yield Label("Sequ\u00eancia", classes="card-title")
                yield Label("\u2026", id="seq-info", classes="card-value")

        # Filter bar
        with Horizontal(id="filter-bar"):
            yield Static("Notas Fiscais", id="section-title")
            yield Select(
                [("Todas", "todas"), ("Emitidas", "emitida"), ("Recebidas", "recebida")],
                value="todas",
                allow_blank=False,
                id="filter-tipo",
                tooltip="Filtrar por tipo: emitida, recebida ou todas",
            )
            yield Select(
                [("Todos", "todos"), ("Hoje", "hoje"), ("Semana", "semana"), ("M\u00eas", "mes")],
                value="todos",
                allow_blank=False,
                id="filter-preset",
                tooltip="Período pré-definido: hoje, semana ou mês",
            )
            yield Static("De:", id="label-de")
            yield MaskedInput(
                template="00/00/0000",
                id="filter-de",
                tooltip="Data inicial do filtro (DD/MM/AAAA)",
            )
            yield Static("Até:", id="label-ate")
            yield MaskedInput(
                template="00/00/0000",
                id="filter-ate",
                tooltip="Data final do filtro (DD/MM/AAAA)",
            )
            yield Button(
                "\u25b7 Filtrar",
                id="btn-filtrar",
                variant="primary",
                tooltip="Aplicar filtros de data e tipo",
            )

        # Action buttons row
        with Horizontal(id="action-bar"):
            yield Button(
                "+ Nova NFS-e",
                id="btn-new",
                variant="primary",
                tooltip="Emitir nova NFS-e (n)",
            )
            yield Button(
                "\u21bb Clonar",
                id="btn-clone",
                tooltip="Clonar nota selecionada com dados pré-preenchidos (r)",
            )
            yield Button(
                "\u25b6 Consultar",
                id="btn-query",
                tooltip="Consultar NFS-e por chave de acesso (c)",
            )
            yield Button(
                "\u21d3 Baixar PDF",
                id="btn-pdf",
                tooltip="Baixar DANFSE em PDF (p)",
            )
            yield Button(
                "\u2398 Copiar",
                id="btn-copy",
                tooltip="Copiar chave de acesso para a área de transferência (y)",
            )
            yield Button(
                "\u21c4 Sincronizar",
                id="btn-sync",
                variant="success",
                tooltip="Sincronizar notas do servidor ADN (s)",
            )

        # DataTable
        yield DataTable(id="recent-table", cursor_type="row")

        # Empty state (shown when no invoices)
        yield Static(
            "Nenhuma nota fiscal encontrada.\n"
            "Pressione [bold]s[/bold] para sincronizar do servidor "
            "ou [bold]n[/bold] para emitir uma nova NFS-e.",
            id="empty-state",
        )

        yield Footer()

    def on_mount(self) -> None:
        self._load_emitter()
        self._load_certificate()
        self._load_sequence()
        self._scan_invoices()
        self.query_one("#recent-table", DataTable).focus()
        self._auto_sync()

    def on_key(self, event: Key) -> None:
        table = self.query_one("#recent-table", DataTable)
        match event.key:
            case "j":
                table.action_cursor_down()
            case "k":
                table.action_cursor_up()
            case "enter":
                self._open_selected()
            case _:
                return
        event.prevent_default()
        event.stop()

    # --- Data loading (threaded) ---

    @work(thread=True)
    def _load_emitter(self) -> None:
        try:
            from emissor.config import load_emitter

            emitter = load_emitter()
            text = f"{emitter['razao_social']}\nCNPJ: {emitter['cnpj']}"
        except Exception as e:
            text = f"Erro: {e}"
        self.app.call_from_thread(self._update_label, "emitter-info", text)

    @work(thread=True)
    def _load_certificate(self) -> None:
        try:
            from emissor.config import get_cert_password, get_cert_path
            from emissor.utils.certificate import validate_certificate

            info = validate_certificate(get_cert_path(), get_cert_password())
            status = "[green]válido[/green]" if info["valid"] else "[red]EXPIRADO[/red]"
            # Format date cleanly — strip time/tz if it's a full datetime string
            not_after = str(info["not_after"])
            if "T" in not_after or " " in not_after:
                try:
                    dt = datetime.fromisoformat(not_after)
                    not_after = dt.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    not_after = not_after.split("T")[0].split(" ")[0]
            text = f"{status}\nAté {not_after}"
        except KeyError:
            text = "não configurado"
        except Exception as e:
            text = f"erro - {e}"
        self.app.call_from_thread(self._update_label, "cert-info", text)

    @work(thread=True)
    def _load_sequence(self) -> None:
        try:
            from emissor.utils.sequence import peek_next_n_dps

            env = self.app.env  # type: ignore[attr-defined]
            n = peek_next_n_dps(env)
            text = f"Próximo: {n}"
        except Exception as e:
            text = f"erro - {e}"
        self.app.call_from_thread(self._update_label, "seq-info", text)

    @work(thread=True)
    def _scan_invoices(self) -> None:
        self.app.call_from_thread(self._do_scan_invoices)

    def _do_scan_invoices(self) -> None:
        from emissor.config import get_issued_dir
        from emissor.utils.registry import list_invoices

        env = self.app.env  # type: ignore[attr-defined]
        invoices: list[dict] = []
        seen_keys: set[str] = set()

        # 1) Registry invoices (emitida + recebida from sync)
        for entry in list_invoices(env):
            chave = entry.get("chave", "")
            seen_keys.add(chave)
            dt = self._parse_date(entry.get("emitted_at") or entry.get("competencia") or "")
            invoices.append(
                {
                    "stem": chave,
                    "datetime": dt,
                    "date_str": dt.strftime("%Y-%m-%d"),
                    "tipo": entry.get("status", "emitida"),
                    "client": entry.get("client", ""),
                    "valor": entry.get("valor_brl", ""),
                }
            )

        # 2) Local XML files not yet in registry (dry runs, etc.)
        issued_dir = get_issued_dir(env)
        if issued_dir.exists():
            for f in issued_dir.glob("*.xml"):
                if f.stem in seen_keys:
                    continue
                mtime = f.stat().st_mtime
                dt = datetime.fromtimestamp(mtime, tz=BRT)
                invoices.append(
                    {
                        "stem": f.stem,
                        "datetime": dt,
                        "date_str": dt.strftime("%Y-%m-%d %H:%M"),
                        "tipo": "rascunho" if f.stem.startswith("dry_run") else "emitida",
                        "client": "",
                        "valor": "",
                    }
                )

        invoices.sort(key=lambda x: x["datetime"], reverse=True)
        self._all_invoices = invoices
        self._apply_filter(show_toast=False)

    @staticmethod
    def _parse_date(value: str) -> datetime:
        """Parse ISO date/datetime strings using fromisoformat()."""
        if not value:
            return datetime.now(BRT)
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=BRT)
            return dt.astimezone(BRT)
        except (ValueError, TypeError):
            return datetime.now(BRT)

    # --- Filtering ---

    def _apply_filter(self, *, show_toast: bool = True) -> None:
        filtered = self._all_invoices

        # Filter by type
        tipo = self.query_one("#filter-tipo", Select).value
        if tipo == "emitida":
            filtered = [i for i in filtered if i["tipo"] == "emitida"]
        elif tipo == "recebida":
            filtered = [i for i in filtered if i["tipo"] == "recebida"]

        # Check custom date inputs first
        de_input = self.query_one("#filter-de", MaskedInput)
        ate_input = self.query_one("#filter-ate", MaskedInput)
        de_val = de_input.value.strip()
        ate_val = ate_input.value.strip()

        if de_val or ate_val:
            filtered = self._filter_by_dates(filtered, de_val, ate_val)
        else:
            preset = self.query_one("#filter-preset", Select).value
            if preset == "hoje":
                today = datetime.now(tz=BRT).date()
                filtered = [i for i in filtered if i["datetime"].date() == today]
            elif preset == "semana":
                week_ago = datetime.now(tz=BRT) - timedelta(days=7)
                filtered = [i for i in filtered if i["datetime"] >= week_ago]
            elif preset == "mes":
                month_ago = datetime.now(tz=BRT) - timedelta(days=30)
                filtered = [i for i in filtered if i["datetime"] >= month_ago]

        self._populate_table(filtered)
        if show_toast:
            count = len(filtered)
            if count == 0:
                self.notify(
                    "Nenhuma nota fiscal encontrada para o filtro selecionado",
                    severity="warning",
                    timeout=3,
                )
            else:
                self.notify(f"{count} nota(s) fiscal(is) encontrada(s)", timeout=2)

    def _filter_by_dates(self, invoices: list[dict], de_val: str, ate_val: str) -> list[dict]:
        result = invoices
        try:
            if de_val:
                de_date = datetime.strptime(de_val, "%d/%m/%Y").replace(tzinfo=BRT)
                result = [i for i in result if i["datetime"] >= de_date]
        except ValueError:
            pass
        try:
            if ate_val:
                ate_dt = datetime.strptime(ate_val, "%d/%m/%Y").replace(tzinfo=BRT)
                ate_end = ate_dt + timedelta(days=1)
                result = [i for i in result if i["datetime"] < ate_end]
        except ValueError:
            pass
        return result

    def _populate_table(self, invoices: list[dict]) -> None:
        table = self.query_one("#recent-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Data", "Tipo", "Cliente/Emitente", "Valor", "Chave")

        status_styles = {
            "emitida": "[green]emitida[/green]",
            "recebida": "[blue]recebida[/blue]",
            "rascunho": "[yellow]rascunho[/yellow]",
        }

        for inv in invoices:
            status = status_styles.get(inv["tipo"], inv["tipo"])
            stem = inv["stem"]
            chave_display = stem[:20] + "\u2026" if len(stem) > 20 else stem
            table.add_row(
                inv["date_str"],
                status,
                inv.get("client", ""),
                inv.get("valor", ""),
                chave_display,
                key=stem,
            )

        # Toggle empty state vs table
        has_rows = table.row_count > 0
        table.display = has_rows
        self.query_one("#empty-state", Static).display = not has_rows

    # --- Event handlers ---

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "filter-preset":
            self.query_one("#filter-de", MaskedInput).clear()
            self.query_one("#filter-ate", MaskedInput).clear()
        self._apply_filter()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "env-badge":
                self.action_toggle_env()
            case "btn-filtrar":
                self._apply_filter()
            case "btn-new":
                self.action_new_invoice()
            case "btn-clone":
                self.action_clone_invoice()
            case "btn-query":
                self.action_query()
            case "btn-pdf":
                self.action_download_pdf()
            case "btn-copy":
                self.action_copy_key()
            case "btn-sync":
                self.action_sync()

    def _selected_stem(self) -> str | None:
        """Return the stem of the currently selected row, or None if empty."""
        table = self.query_one("#recent-table", DataTable)
        if table.row_count == 0:
            return None
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        return str(row_key.value)

    # --- Open selected row ---

    def _open_selected(self) -> None:
        stem = self._selected_stem()
        if not stem:
            return
        if stem.startswith("dry_run"):
            self.notify(
                "Rascunho (dry_run) — não pode ser consultado na SEFIN",
                severity="warning",
            )
            return
        from emissor.tui.screens.query import QueryScreen

        self.app.push_screen(QueryScreen(chave=stem))

    # --- Helpers ---

    def _update_label(self, label_id: str, text: str) -> None:
        try:
            label = self.query_one(f"#{label_id}", Label)
            label.update(text)
        except Exception:
            pass

    # --- Actions ---

    def action_new_invoice(self) -> None:
        from emissor.tui.screens.new_invoice import NewInvoiceScreen

        self.app.push_screen(NewInvoiceScreen())

    def action_clone_invoice(self) -> None:
        stem = self._selected_stem()
        if not stem:
            self.notify("Nenhuma nota selecionada", severity="warning", timeout=3)
            return
        entry = next(
            (i for i in self._all_invoices if i["stem"] == stem),
            None,
        )
        if not entry:
            return
        prefill: dict = {}
        # Look up full registry entry for client_slug and valor_usd
        from emissor.utils.registry import list_invoices

        env = self.app.env  # type: ignore[attr-defined]
        reg_entry = next(
            (e for e in list_invoices(env) if e.get("chave") == stem),
            None,
        )
        if reg_entry:
            if reg_entry.get("client_slug"):
                prefill["client_slug"] = reg_entry["client_slug"]
            if reg_entry.get("valor_usd"):
                prefill["valor_usd"] = reg_entry["valor_usd"]
        if entry.get("valor"):
            prefill["valor_brl"] = entry["valor"]

        from emissor.tui.screens.new_invoice import NewInvoiceScreen

        self.app.push_screen(NewInvoiceScreen(prefill=prefill))

    def action_clients(self) -> None:
        from emissor.tui.screens.clients import ClientsScreen

        self.app.push_screen(ClientsScreen())

    def action_query(self) -> None:
        stem = self._selected_stem()
        chave = stem if stem and not stem.startswith("dry_run") else ""
        from emissor.tui.screens.query import QueryScreen

        self.app.push_screen(QueryScreen(chave=chave))

    def action_download_pdf(self) -> None:
        stem = self._selected_stem()
        chave = stem if stem and not stem.startswith("dry_run") else ""
        from emissor.tui.screens.download_pdf import DownloadPdfScreen

        self.app.push_screen(DownloadPdfScreen(chave=chave))

    def action_copy_key(self) -> None:
        stem = self._selected_stem()
        if not stem:
            return
        cmd = self._clipboard_cmd()
        if not cmd:
            self.notify(f"Chave: {stem}", severity="warning")
            return
        try:
            subprocess.run(cmd, input=stem.encode(), check=True, timeout=5)
            self.notify(f"Chave copiada: {stem}")
        except FileNotFoundError:
            self.notify(
                f"Área de transferência indisponível. Chave: {stem}",
                severity="warning",
            )
        except Exception:
            self.notify(f"Chave: {stem}", severity="warning")

    @staticmethod
    def _clipboard_cmd() -> list[str] | None:
        """Return the clipboard copy command for the current platform."""
        system = platform.system()
        if system == "Darwin":
            return ["pbcopy"]
        if system == "Linux":
            if shutil.which("xclip"):
                return ["xclip", "-selection", "clipboard"]
            if shutil.which("xsel"):
                return ["xsel", "--clipboard", "--input"]
            if shutil.which("wl-copy"):
                return ["wl-copy"]
            return None
        if system == "Windows":
            return ["clip"]
        return None

    def action_help(self) -> None:
        from emissor.tui.screens.help import HelpScreen

        self.app.push_screen(HelpScreen())

    def action_validate(self) -> None:
        from emissor.tui.screens.validate import ValidateScreen

        self.app.push_screen(ValidateScreen())

    @work(thread=True)
    def _auto_sync(self) -> None:
        """Auto-sync on startup — shows progress/result notifications."""
        self.app.call_from_thread(
            self.notify, "Sincronizando notas do servidor…", severity="information", timeout=3
        )
        self._do_sync()

    def action_sync(self) -> None:
        self.notify("Sincronizando notas do servidor…", severity="information", timeout=3)
        self._run_sync()

    @work(thread=True)
    def _run_sync(self) -> None:
        self._do_sync()

    def _do_sync(self) -> None:
        """Fetch and register NFS-e from ADN. Shared by auto-sync and manual sync."""
        try:
            from emissor.config import get_cert_password, get_cert_path, load_emitter
            from emissor.services.adn_client import iter_dfe, parse_dfe_xml
            from emissor.utils.registry import add_invoice, get_last_nsu, set_last_nsu

            env = self.app.env  # type: ignore[attr-defined]
            pfx_path = get_cert_path()
            pfx_password = get_cert_password()
            my_cnpj = load_emitter()["cnpj"]

            last_nsu = get_last_nsu(env)
            max_nsu = last_nsu
            total = 0

            for doc in iter_dfe(pfx_path, pfx_password, nsu=last_nsu, env=env):
                chave = doc.get("ChaveAcesso", "")
                doc_nsu = doc.get("NSU", 0)
                if doc_nsu > max_nsu:
                    max_nsu = doc_nsu
                if not chave:
                    continue

                meta = parse_dfe_xml(doc["ArquivoXml"])
                emitida = meta["emit_cnpj"] == my_cnpj
                total += 1

                add_invoice(
                    chave,
                    n_dps=int(meta["n_nfse"]) if meta["n_nfse"] else None,
                    client=meta["toma_nome"] if emitida else meta["emit_nome"],
                    valor_brl=meta["valor"],
                    competencia=meta["competencia"],
                    emitted_at=doc.get("DataHoraGeracao"),
                    nsu=doc_nsu if doc_nsu else None,
                    env=env,
                    status="emitida" if emitida else "recebida",
                )

            if max_nsu > last_nsu:
                set_last_nsu(env, max_nsu)

            self.app.call_from_thread(self._on_sync_done, total)
        except KeyError:
            self.app.call_from_thread(self._on_sync_error, "Certificado não configurado")
        except Exception as e:
            self.app.call_from_thread(self._on_sync_error, str(e))

    def _on_sync_done(self, total: int) -> None:
        self.notify(f"Sincronização concluída: {total} documento(s)", timeout=3)
        self._scan_invoices()

    def _on_sync_error(self, msg: str) -> None:
        self.notify(f"Erro na sincronização: {msg}", severity="error", timeout=5)

    def action_toggle_env(self) -> None:
        if self.app.env == "homologacao":  # type: ignore[attr-defined]
            from emissor.tui.screens.confirm import ConfirmScreen

            self.app.push_screen(
                ConfirmScreen(
                    "⚠ Você está alternando para o ambiente de PRODUÇÃO.\n\n"
                    "Notas emitidas neste ambiente terão validade\n"
                    "fiscal e não podem ser desfeitas.\n\n"
                    "Deseja continuar?"
                ),
                callback=self._on_env_toggle_confirmed,
            )
        else:
            self.app.env = "homologacao"  # type: ignore[attr-defined]
            self._update_env_badge()
            self._load_sequence()
            self._scan_invoices()

    def _on_env_toggle_confirmed(self, confirmed: bool | None) -> None:
        if confirmed:
            self.app.env = "producao"  # type: ignore[attr-defined]
            self._update_env_badge()
            self._load_sequence()
            self._scan_invoices()

    def _update_env_badge(self) -> None:
        badge = self.query_one("#env-badge", Button)
        env = self.app.env  # type: ignore[attr-defined]
        is_homol = env == "homologacao"
        badge.label = "\u21c4 HOMOLOGAÇÃO" if is_homol else "\u21c4 PRODUÇÃO"
        badge.set_class(is_homol, "env-homol")
        badge.set_class(not is_homol, "env-prod")

    def action_focus_filter(self) -> None:
        self.query_one("#filter-de", MaskedInput).focus()

    def action_quit(self) -> None:
        self.app.exit()
