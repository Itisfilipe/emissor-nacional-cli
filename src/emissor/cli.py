from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import click
from rich.console import Console

console = Console()


def _validate_monetary(ctx: click.Context, param: click.Parameter, value: str) -> str:
    try:
        d = Decimal(value)
        if not d.is_finite():
            raise InvalidOperation
        if d <= 0:
            raise click.BadParameter(f"Valor deve ser positivo: '{value}'")
    except InvalidOperation:
        raise click.BadParameter(f"Valor numérico inválido: '{value}'") from None
    return format(d.normalize(), "f")


def _validate_date(ctx: click.Context, param: click.Parameter, value: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError:
        raise click.BadParameter(f"Data inválida: '{value}'. Use YYYY-MM-DD.") from None
    return value


@click.group()
@click.option(
    "--env",
    type=click.Choice(["homologacao", "producao"]),
    default="homologacao",
    help="Ambiente da API (homologacao ou producao)",
)
@click.pass_context
def cli(ctx: click.Context, env: str) -> None:
    """Emissor de NFS-e Nacional"""
    ctx.ensure_object(dict)
    ctx.obj["env"] = env


@cli.command()
@click.argument("cliente")
@click.option(
    "--valor-brl", required=True, callback=_validate_monetary, help="Valor em BRL (ex: 19684.93)"
)
@click.option(
    "--valor-usd", required=True, callback=_validate_monetary, help="Valor em USD (ex: 3640.00)"
)
@click.option(
    "--competencia",
    required=True,
    callback=_validate_date,
    help="Data de competência (YYYY-MM-DD)",
)
@click.option("--intermediario", default=None, help="Nome do intermediário (ex: oyster)")
@click.option("--dry-run", is_flag=True, help="Gera XML sem enviar para SEFIN")
@click.pass_context
def emit(
    ctx: click.Context,
    cliente: str,
    valor_brl: str,
    valor_usd: str,
    competencia: str,
    intermediario: str | None,
    dry_run: bool,
) -> None:
    """Emitir NFS-e para um cliente."""
    from emissor.services.emission import emit as do_emit

    env = ctx.obj["env"]

    console.print("\n[bold]Emitindo NFS-e[/bold]")
    console.print(f"  Cliente: [cyan]{cliente}[/cyan]")
    console.print(f"  Valor BRL: [green]{valor_brl}[/green]")
    console.print(f"  Valor USD: [green]{valor_usd}[/green]")
    console.print(f"  Competência: {competencia}")
    console.print(f"  Ambiente: [yellow]{env}[/yellow]")
    if intermediario:
        console.print(f"  Intermediário: {intermediario}")
    if dry_run:
        console.print("  [yellow]DRY RUN - XML não será enviado[/yellow]")
    console.print()

    try:
        result = do_emit(
            client_name=cliente,
            valor_brl=valor_brl,
            valor_usd=valor_usd,
            competencia=competencia,
            env=env,
            intermediario=intermediario,
            dry_run=dry_run,
        )

        console.print(f"[green]✓[/green] nDPS: {result['n_dps']}")

        if dry_run:
            console.print(f"[green]✓[/green] XML salvo em: {result.get('saved_to')}")
        else:
            resp = result["response"]
            console.print("[green]✓[/green] NFS-e emitida com sucesso!")
            if resp:
                console.print(f"  Chave de acesso: {resp.get('chNFSe', 'N/A')}")
                console.print(f"  nNFSe: {resp.get('nNFSe', 'N/A')}")
            if result.get("saved_to"):
                console.print(f"  XML salvo em: {result['saved_to']}")

    except Exception as e:
        console.print(f"[red]✗ Erro: {e}[/red]")
        raise SystemExit(1) from None


@cli.command()
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validar certificado e configuração."""
    from emissor.config import get_cert_password, get_cert_path, load_emitter
    from emissor.utils.certificate import validate_certificate

    console.print("\n[bold]Validando configuração[/bold]\n")

    # Check emitter config
    try:
        emitter = load_emitter()
        console.print(f"[green]✓[/green] Emitente: {emitter['razao_social']}")
        console.print(f"  CNPJ: {emitter['cnpj']}")
    except Exception as e:
        console.print(f"[red]✗ Erro no emitter.yaml: {e}[/red]")
        raise SystemExit(1) from None

    # Check certificate
    try:
        pfx_path = get_cert_path()
        pfx_password = get_cert_password()
        info = validate_certificate(pfx_path, pfx_password)

        status = "[green]válido[/green]" if info["valid"] else "[red]expirado[/red]"
        console.print(f"[green]✓[/green] Certificado: {status}")
        console.print(f"  Sujeito: {info['subject']}")
        console.print(f"  Emissor: {info['issuer']}")
        console.print(f"  Válido de: {info['not_before']}")
        console.print(f"  Válido até: {info['not_after']}")
    except KeyError:
        console.print("[red]✗ CERT_PFX_PATH ou CERT_PFX_PASSWORD não definidos no .env[/red]")
        raise SystemExit(1) from None
    except Exception as e:
        console.print(f"[red]✗ Erro no certificado: {e}[/red]")
        raise SystemExit(1) from None

    # Check clients
    from emissor.config import CONFIG_DIR

    clients_dir = CONFIG_DIR / "clients"
    if clients_dir.exists():
        for f in sorted(clients_dir.glob("*.yaml")):
            console.print(f"[green]✓[/green] Cliente: {f.stem}")

    console.print("\n[green]Configuração OK![/green]")


@cli.command()
@click.argument("chave_acesso")
@click.pass_context
def query(ctx: click.Context, chave_acesso: str) -> None:
    """Consultar NFS-e emitida pela chave de acesso."""
    from emissor.config import get_cert_password, get_cert_path
    from emissor.services.adn_client import query_nfse

    env = ctx.obj["env"]

    try:
        result = query_nfse(
            chave_acesso,
            get_cert_path(),
            get_cert_password(),
            env,
        )
        console.print_json(data=result)
    except Exception as e:
        console.print(f"[red]✗ Erro: {e}[/red]")
        raise SystemExit(1) from None


@cli.command()
@click.argument("chave_acesso")
@click.option("-o", "--output", required=True, help="Caminho do arquivo PDF de saída")
@click.pass_context
def pdf(ctx: click.Context, chave_acesso: str, output: str) -> None:
    """Baixar DANFSE PDF de uma NFS-e."""
    from emissor.config import get_cert_password, get_cert_path
    from emissor.services.adn_client import download_danfse

    env = ctx.obj["env"]

    try:
        content = download_danfse(
            chave_acesso,
            get_cert_path(),
            get_cert_password(),
            env,
        )
        Path(output).write_bytes(content)
        console.print(f"[green]✓[/green] PDF salvo em: {output}")
    except Exception as e:
        console.print(f"[red]✗ Erro: {e}[/red]")
        raise SystemExit(1) from None
