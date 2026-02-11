from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, RichLog, Static


class HelpScreen(ModalScreen):
    """Help, keyboard shortcuts, and disclaimer."""

    BINDINGS = [
        Binding("escape", "go_back", "Voltar"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            with Horizontal(id="modal-title-bar"):
                yield Static("Ajuda", id="header-bar")
                yield Button("\u2715", id="btn-modal-close")
            yield RichLog(id="help-content", wrap=True, markup=True)
            with Horizontal(classes="button-bar"):
                yield Button("\u2715 Fechar", id="btn-voltar")

    def on_mount(self) -> None:
        log = self.query_one("#help-content", RichLog)

        log.write("[bold]Emissor Nacional CLI[/bold]")
        log.write("")
        log.write(
            "Ferramenta para emissão de NFS-e (Nota Fiscal de Serviço Eletrônica) "
            "via Sistema Nacional da SEFIN/ADN."
        )
        log.write("")

        log.write("[bold]Atalhos de teclado[/bold]")
        log.write("")
        log.write("  [bold cyan]n[/bold cyan]  Nova NFS-e         Emitir uma nova nota fiscal")
        log.write("  [bold cyan]c[/bold cyan]  Consultar          Consultar NFS-e por chave")
        log.write("  [bold cyan]p[/bold cyan]  Baixar PDF         Baixar DANFSE em PDF")
        log.write("  [bold cyan]y[/bold cyan]  Copiar chave       Copiar chave para clipboard")
        log.write("  [bold cyan]s[/bold cyan]  Sincronizar        Buscar notas do servidor")
        log.write("  [bold cyan]v[/bold cyan]  Validar            Validar certificado e config.")
        log.write("  [bold cyan]e[/bold cyan]  Ambiente           Alternar produção/homologação")
        log.write("  [bold cyan]f[/bold cyan]  Filtrar            Focar nos campos de data")
        log.write("  [bold cyan]h[/bold cyan]  Ajuda              Esta tela")
        log.write("  [bold cyan]q[/bold cyan]  Sair               Encerrar aplicação")
        log.write("")
        log.write("[bold]Navegação na tabela[/bold]")
        log.write("")
        log.write("  [bold cyan]j / \u2193[/bold cyan]  Próxima linha")
        log.write("  [bold cyan]k / \u2191[/bold cyan]  Linha anterior")
        log.write("  [bold cyan]enter[/bold cyan]   Abrir nota selecionada")
        log.write("")

        log.write("[bold]Sobre[/bold]")
        log.write("")
        log.write(
            "Este software utiliza as APIs do Sistema Nacional NFS-e "
            "(SEFIN e ADN) para emissão e consulta de notas fiscais de serviço. "
            "Requer certificado digital ICP-Brasil A1 (.pfx) válido."
        )
        log.write("")

        log.write("[bold yellow]Aviso[/bold yellow]")
        log.write("")
        log.write(
            "Este software é fornecido \"como está\", sem garantias de qualquer tipo. "
            "O usuário é responsável por verificar a conformidade das notas emitidas "
            "com a legislação vigente. Consulte seu contador para orientação fiscal."
        )
        log.write("")
        log.write(
            "As operações em ambiente de [bold red]PRODUÇÃO[/bold red] geram documentos "
            "fiscais reais com validade jurídica. Utilize o ambiente de "
            "[bold yellow]HOMOLOGAÇÃO[/bold yellow] para testes."
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("btn-voltar", "btn-modal-close"):
            self.app.pop_screen()

    def action_go_back(self) -> None:
        self.app.pop_screen()
