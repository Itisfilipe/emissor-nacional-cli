from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, RichLog, Static


class ValidateScreen(ModalScreen):
    """Certificate and config validation display."""

    BINDINGS = [
        Binding("escape", "go_back", "Voltar"),
        Binding("q", "go_back", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            with Horizontal(id="modal-title-bar"):
                yield Static("Validar Configuração", id="header-bar")
                yield Button("\u2715", id="btn-modal-close")
            yield RichLog(id="validation-output", wrap=True, markup=True)
            with Horizontal(classes="button-bar"):
                yield Button("\u2715 Fechar", id="btn-voltar", variant="error")

    def on_mount(self) -> None:
        self.notify("Validando configuração…", severity="information", timeout=2)
        self._run_validation()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "btn-voltar" | "btn-modal-close":
                self.app.pop_screen()

    @work(thread=True)
    def _run_validation(self) -> None:
        lines: list[str] = []

        # Emitter
        try:
            from emissor.config import load_emitter

            emitter = load_emitter()
            lines.append(f"[green]OK[/green] Emitente: {emitter['razao_social']}")
            lines.append(f"   CNPJ: {emitter['cnpj']}")
        except Exception as e:
            lines.append(f"[red]ERRO[/red] Emitente: {e}")

        # Certificate + ADN connectivity (both need the certificate)
        pfx_path: str | None = None
        pfx_password: str | None = None
        try:
            from emissor.config import get_cert_password, get_cert_path
            from emissor.utils.certificate import validate_certificate

            pfx_path = get_cert_path()
            pfx_password = get_cert_password()
            info = validate_certificate(pfx_path, pfx_password)
            status = "[green]válido[/green]" if info["valid"] else "[red]expirado[/red]"
            lines.append(f"[green]OK[/green] Certificado: {status}")
            lines.append(f"   Sujeito: {info['subject']}")
            lines.append(f"   Emissor: {info['issuer']}")
            lines.append(f"   Válido de: {info['not_before']}")
            lines.append(f"   Válido até: {info['not_after']}")
        except KeyError:
            lines.append("[red]ERRO[/red] Certificado não configurado")
            lines.append("   Execute 'emissor-nacional init' para configurar")
        except Exception as e:
            lines.append(f"[red]ERRO[/red] Certificado: {e}")

        # Clients
        try:
            from emissor.config import list_clients, load_client
            from emissor.models.client import Client

            clients = list_clients()
            if clients:
                for c in clients:
                    try:
                        data = load_client(c)
                        Client.from_dict(data)
                        lines.append(f"[green]OK[/green] Cliente: {c}")
                    except Exception as ce:
                        lines.append(f"[red]ERRO[/red] Cliente {c}: {ce}")
            else:
                lines.append("[yellow]AVISO[/yellow] Nenhum cliente configurado")
        except Exception as e:
            lines.append(f"[red]ERRO[/red] Clientes: {e}")

        # API connectivity (ADN + SEFIN)
        env = self.app.env  # type: ignore[attr-defined]
        if pfx_path and pfx_password:
            try:
                from emissor.config import ENDPOINTS
                from emissor.services.adn_client import check_connectivity
                from emissor.services.sefin_client import check_sefin_connectivity
            except Exception as e:
                lines.append(f"[red]ERRO[/red] Conectividade: {e}")
                self.app.call_from_thread(self._display_lines, lines)
                return

            checks = [
                ("ADN", "adn", lambda: check_connectivity(pfx_path, pfx_password, env)),
                ("SEFIN", "sefin", lambda: check_sefin_connectivity(pfx_path, pfx_password, env)),
            ]
            for label, endpoint_key, check_fn in checks:
                try:
                    check_fn()
                    lines.append(f"[green]OK[/green] Conectividade {label} ({env})")
                except Exception as e:
                    endpoint = ENDPOINTS.get(env, {}).get(endpoint_key, "?")
                    lines.append(f"[red]ERRO[/red] Conectividade {label}: {e}")
                    lines.append(f"   Endpoint: {endpoint}")
        else:
            lines.append("[red]ERRO[/red] Conectividade ADN: certificado não configurado")
            lines.append("[red]ERRO[/red] Conectividade SEFIN: certificado não configurado")

        # Registry health
        try:
            from emissor.utils.registry import check_registry_health

            health = check_registry_health()
            if health.registry_ok:
                lines.append(f"[green]OK[/green] Registro local: {health.registry_count} nota(s)")
            else:
                lines.append("[red]ERRO[/red] Registro local: arquivo corrompido")
            for b in health.registry_corrupt_backups:
                lines.append(f"[yellow]AVISO[/yellow] Backup encontrado: {b}")
                lines.append("   Recuperação: renomear para invoices.json e reiniciar")
            if not health.sync_state_ok:
                lines.append("[red]ERRO[/red] Estado de sincronização: arquivo corrompido")
            for b in health.sync_state_corrupt_backups:
                lines.append(f"[yellow]AVISO[/yellow] Backup sync: {b}")
                lines.append("   Recuperação: renomear para sync_state.json e reiniciar")
        except Exception as e:
            lines.append(f"[red]ERRO[/red] Registro local: {e}")

        self.app.call_from_thread(self._display_lines, lines)

    def _display_lines(self, lines: list[str]) -> None:
        log = self.query_one("#validation-output", RichLog)
        for line in lines:
            log.write(line)
        has_errors = any("[red]" in line for line in lines)
        if has_errors:
            self.notify("Validação concluída com erros", severity="warning", timeout=3)
        else:
            self.notify("Validação concluída — tudo OK", timeout=3)

    def action_go_back(self) -> None:
        self.app.pop_screen()
