from __future__ import annotations

import getpass
import stat
import sys
from importlib.resources import files
from pathlib import Path


def _check_keyring_available() -> bool:
    """Check if keyring is installed with a usable backend."""
    try:
        import keyring
        from keyring.backends.fail import Keyring as FailKeyring

        return not isinstance(keyring.get_keyring(), FailKeyring)
    except Exception:
        return False


def _upsert_env_var(env_file: Path, key: str, value: str) -> None:
    """Set or update a key=value pair in a .env file, creating it if needed.

    Uses dotenv.set_key for proper quoting (handles #, spaces, etc.).
    """
    from dotenv import set_key

    env_file.parent.mkdir(parents=True, exist_ok=True)
    if not env_file.exists():
        env_file.touch()
    set_key(str(env_file), key, value)


def _remove_env_var(env_file: Path, key: str) -> None:
    """Remove a key from a .env file if present."""
    from dotenv import unset_key

    if env_file.exists():
        unset_key(str(env_file), key)


def _warn_open_permissions(env_file: Path) -> None:
    """Warn if .env file has group/other read permissions (Unix only)."""
    try:
        mode = env_file.stat().st_mode
        if mode & (stat.S_IRGRP | stat.S_IROTH):
            print(f"\n  AVISO: {env_file} tem permissões abertas.")
            print("  Recomendação: chmod 600", env_file)
    except OSError:
        pass


def _setup_certificate(config_dir: Path) -> bool:
    """Interactive certificate setup. Returns True if cert was configured."""
    print()
    print("Configuração do certificado digital")
    print("────────────────────────────────────")
    print()

    # --- Cert path ---
    while True:
        pfx_path = input("Caminho do certificado .pfx/.p12 (vazio para pular): ").strip()
        if not pfx_path:
            print("  Configuração de certificado pulada.")
            return False
        if Path(pfx_path).is_file():
            break
        print(f"  Arquivo não encontrado: {pfx_path}")

    # --- Cert password ---
    pfx_password = getpass.getpass("Senha do certificado: ")

    # --- Validate ---
    print()
    print("Validando certificado…")
    try:
        from emissor.utils.certificate import validate_certificate

        info = validate_certificate(pfx_path, pfx_password)
    except Exception as e:
        print(f"  ERRO: Certificado inválido ou senha incorreta — {e}")
        print("  Configuração de certificado abortada.")
        return False

    print(f"  Sujeito: {info['subject']}")
    print(f"  Válido até: {info['not_after']}")
    if info["valid"]:
        print("  Certificado válido")
    else:
        print("  AVISO: Certificado expirado")

    # --- Always save path to config dir .env ---
    env_file = config_dir / ".env"
    _upsert_env_var(env_file, "CERT_PFX_PATH", pfx_path)

    # --- Password storage choice ---
    print()
    print("Onde deseja armazenar a senha?")

    keyring_ok = _check_keyring_available()
    options: list[tuple[str, str]] = []
    if keyring_ok:
        options.append(("1", "Keychain do sistema (recomendado)"))
    options.append(("2", "Arquivo .env no diretório de configuração"))
    options.append(("3", "Não armazenar (definir manualmente)"))

    for num, label in options:
        print(f"  {num}. {label}")

    if not keyring_ok:
        print()
        print("  Nota: keychain do sistema indisponível (sem backend configurado).")

    print()
    valid_choices = {num for num, _ in options}
    choice = ""
    while choice not in valid_choices:
        choice = input(f"Escolha [{'/'.join(valid_choices)}]: ").strip()

    from emissor.config import _delete_keyring_password

    if choice == "1" and keyring_ok:
        from emissor.config import _set_keyring_password

        if _set_keyring_password(pfx_password):
            print("  Senha armazenada no keychain do sistema.")
            # Remove from .env to avoid stale secret on disk
            _remove_env_var(env_file, "CERT_PFX_PASSWORD")
        else:
            print("  ERRO: Falha ao armazenar no keychain. Salvando no .env como alternativa.")
            _upsert_env_var(env_file, "CERT_PFX_PASSWORD", pfx_password)
            _warn_open_permissions(env_file)
    elif choice == "2":
        _upsert_env_var(env_file, "CERT_PFX_PASSWORD", pfx_password)
        print(f"  Senha salva em {env_file}")
        _warn_open_permissions(env_file)
        # Remove from keyring to avoid stale secret
        _delete_keyring_password()
    else:
        # Clean up any previously stored password
        _remove_env_var(env_file, "CERT_PFX_PASSWORD")
        _delete_keyring_password()
        print("  Senha não armazenada.")
        print("  Defina CERT_PFX_PASSWORD no seu shell ou .env antes de usar o emissor.")

    return True


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
    print(f"Configuração: {config_dir}")
    print(f"Dados:   {data_dir}")

    # --- Certificate setup ---
    print()
    cert_configured = False
    try:
        answer = input("Deseja configurar o certificado digital agora? [S/n]: ").strip().lower()
        if answer in ("", "s", "sim", "y", "yes"):
            cert_configured = _setup_certificate(config_dir)
    except (EOFError, KeyboardInterrupt):
        print()

    print()
    if copied:
        print("Próximos passos:")
        print(f"  1. cp {config_dir / 'emitter.yaml.example'} {config_dir / 'emitter.yaml'}")
        print("  2. Edite emitter.yaml com os dados do seu CNPJ")
        if not cert_configured:
            print("  3. Crie um .env com CERT_PFX_PATH e CERT_PFX_PASSWORD")
            print("  4. Execute: emissor-nacional")
        else:
            print("  3. Execute: emissor-nacional")
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
