from __future__ import annotations

import sys
from importlib.resources import files


def _init_config() -> None:
    """Copy bundled config templates to the user's config/data directories."""
    from emissor.config import get_config_dir, get_data_dir

    config_dir = get_config_dir()
    data_dir = get_data_dir()
    templates = files("emissor") / "templates"

    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "clients").mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for rel in [
        "emitter.yaml.example",
        "clients/acme-corp.yaml.example",
        "clients/intermediary.yaml.example",
    ]:
        dest = config_dir / rel
        if dest.exists():
            print(f"  já existe: {dest}")
            continue
        src = templates / rel
        with src.open("rb") as f:
            dest.write_bytes(f.read())
        print(f"  criado: {dest}")
        copied += 1

    print()
    print(f"Config:  {config_dir}")
    print(f"Dados:   {data_dir}")
    print()
    if copied:
        print("Próximos passos:")
        print(f"  1. cp {config_dir / 'emitter.yaml.example'} {config_dir / 'emitter.yaml'}")
        print("  2. Edite emitter.yaml com os dados do seu CNPJ")
        print("  3. Crie um .env com CERT_PFX_PATH e CERT_PFX_PASSWORD")
        print("  4. Execute: emissor-nacional")
    else:
        print("Nenhum arquivo novo criado (todos já existiam).")


def _preflight() -> bool:
    """Verify minimal config before launching the TUI.

    Auto-creates the data directory. Returns False with a helpful
    message when the config directory or emitter.yaml is missing.
    """
    from emissor.config import get_config_dir, get_data_dir

    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    config_dir = get_config_dir()
    if not config_dir.is_dir():
        print(f"Erro: diretório de configuração não encontrado: {config_dir}")
        print("Execute 'emissor-nacional init' para criar os arquivos de exemplo.")
        return False
    if not (config_dir / "emitter.yaml").is_file():
        print(f"Erro: emitter.yaml não encontrado em {config_dir}")
        print("Execute 'emissor-nacional init' e configure o emitente.")
        return False
    return True


def main() -> None:
    """Entry point for the Emissor Nacional CLI/TUI."""
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        _init_config()
        return

    if not _preflight():
        sys.exit(1)

    from emissor.tui.app import EmissorApp

    app = EmissorApp()
    app.run()


if __name__ == "__main__":
    main()
