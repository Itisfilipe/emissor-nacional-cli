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
            "Ferramenta para emissao de NFS-e (Nota Fiscal de Servico Eletronica) "
            "via Sistema Nacional da SEFIN/ADN."
        )
        log.write("")

        log.write("[bold]Atalhos de teclado[/bold]")
        log.write("")
        log.write("  [bold cyan]n[/bold cyan]  Nova NFS-e         Emitir uma nova nota fiscal")
        log.write("  [bold cyan]c[/bold cyan]  Consultar          Consultar NFS-e por chave de acesso")
        log.write("  [bold cyan]p[/bold cyan]  Baixar PDF         Baixar DANFSE em PDF")
        log.write("  [bold cyan]y[/bold cyan]  Copiar chave       Copiar chave de acesso para clipboard")
        log.write("  [bold cyan]s[/bold cyan]  Sincronizar        Buscar notas do servidor ADN")
        log.write("  [bold cyan]v[/bold cyan]  Validar            Validar certificado e configuracao")
        log.write("  [bold cyan]e[/bold cyan]  Ambiente           Alternar entre producao e homologacao")
        log.write("  [bold cyan]f[/bold cyan]  Filtrar            Focar nos campos de data")
        log.write("  [bold cyan]h[/bold cyan]  Ajuda              Esta tela")
        log.write("  [bold cyan]q[/bold cyan]  Sair               Encerrar aplicacao")
        log.write("")
        log.write("[bold]Navegacao na tabela[/bold]")
        log.write("")
        log.write("  [bold cyan]j / \u2193[/bold cyan]  Proxima linha")
        log.write("  [bold cyan]k / \u2191[/bold cyan]  Linha anterior")
        log.write("  [bold cyan]enter[/bold cyan]   Abrir nota selecionada")
        log.write("")

        log.write("[bold]Sobre[/bold]")
        log.write("")
        log.write(
            "Este software utiliza as APIs do Sistema Nacional NFS-e "
            "(SEFIN e ADN) para emissao e consulta de notas fiscais de servico. "
            "Requer certificado digital ICP-Brasil A1 (.pfx) valido."
        )
        log.write("")

        log.write("[bold yellow]Aviso[/bold yellow]")
        log.write("")
        log.write(
            "Este software e fornecido \"como esta\", sem garantias de qualquer tipo. "
            "O usuario e responsavel por verificar a conformidade das notas emitidas "
            "com a legislacao vigente. Consulte seu contador para orientacao fiscal."
        )
        log.write("")
        log.write(
            "As operacoes em ambiente de [bold red]PRODUCAO[/bold red] geram documentos "
            "fiscais reais com validade juridica. Utilize o ambiente de "
            "[bold yellow]HOMOLOGACAO[/bold yellow] para testes."
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("btn-voltar", "btn-modal-close"):
            self.app.pop_screen()

    def action_go_back(self) -> None:
        self.app.pop_screen()
