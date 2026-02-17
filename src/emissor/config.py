from __future__ import annotations

import os
from datetime import timedelta, timezone
from pathlib import Path

import platformdirs
import yaml
from dotenv import load_dotenv

KEYRING_SERVICE = "emissor-nacional"
KEYRING_USERNAME = "cert-pfx-password"


def _resolve_config_dir_for_dotenv() -> Path | None:
    """Resolve config dir for .env loading without depending on env vars from .env itself.

    Uses the same 3-tier resolution as _resolve_dir but only checks sources
    available before .env is loaded (env var set in shell, dev layout).
    Returns None if only platformdirs would resolve (since the dir may not exist yet).
    """
    from_env = os.environ.get("EMISSOR_CONFIG_DIR")
    if from_env:
        return Path(from_env)
    project_root = Path(__file__).resolve().parent.parent.parent
    candidate = project_root / "config"
    if candidate.is_dir():
        return candidate
    # For pip installs, use platformdirs — dir may not exist yet but .env could be there
    pd = Path(platformdirs.user_config_dir("emissor-nacional"))
    if pd.is_dir():
        return pd
    return None


# Load .env: cwd first (highest priority), then config dir (won't override)
load_dotenv()
_cfg_dir = _resolve_config_dir_for_dotenv()
if _cfg_dir is not None:
    load_dotenv(_cfg_dir / ".env")


def _resolve_dir(env_var: str, default_subdir: str, kind: str) -> Path:
    """Resolve a directory from env var, repo layout, or platform default.

    Priority: 1) env var, 2) dev repo layout, 3) platformdirs user directory.
    """
    from_env = os.environ.get(env_var)
    if from_env:
        return Path(from_env)
    # Development layout: src/emissor/config.py -> ../../.. = project root
    project_root = Path(__file__).resolve().parent.parent.parent
    candidate = project_root / default_subdir
    if candidate.is_dir():
        return candidate
    # Installed via pip — use platform-standard directories
    if kind == "config":
        return Path(platformdirs.user_config_dir("emissor-nacional"))
    return Path(platformdirs.user_data_dir("emissor-nacional"))


def get_config_dir() -> Path:
    """Resolve config directory. Re-evaluated on each call to pick up env changes."""
    return _resolve_dir("EMISSOR_CONFIG_DIR", "config", kind="config")


def get_data_dir() -> Path:
    """Resolve data directory. Re-evaluated on each call to pick up env changes."""
    return _resolve_dir("EMISSOR_DATA_DIR", "data", kind="data")


NFSE_NS = "http://www.sped.fazenda.gov.br/nfse"

BRT = timezone(timedelta(hours=-3))

ENDPOINTS = {
    "homologacao": {
        "sefin": "https://sefin.producaorestrita.nfse.gov.br/SefinNacional/nfse",
        "adn": "https://adn.producaorestrita.nfse.gov.br",
    },
    "producao": {
        "sefin": "https://sefin.nfse.gov.br/SefinNacional/nfse",
        "adn": "https://adn.nfse.gov.br",
    },
}

TP_AMB = {"homologacao": "2", "producao": "1"}

SEFIN_TIMEOUT = 60
ADN_TIMEOUT = 30


# --- Keyring helpers ---


def _get_keyring_password() -> str | None:
    """Try to get the certificate password from the OS keyring.

    Returns None on any failure (no backend, not stored, dbus errors, etc.).
    """
    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except Exception:
        return None


def _set_keyring_password(password: str) -> bool:
    """Store the certificate password in the OS keyring. Returns True on success."""
    try:
        import keyring

        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, password)
        return True
    except Exception:
        return False


def _delete_keyring_password() -> bool:
    """Remove the certificate password from the OS keyring. Returns True on success."""
    try:
        import keyring

        keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
        return True
    except Exception:
        return False


# --- Certificate access ---


def get_cert_path() -> str:
    """Return the path to the .pfx certificate from CERT_PFX_PATH env var.

    Raises KeyError if the variable is not set.
    """
    return os.environ["CERT_PFX_PATH"]


def get_cert_password() -> str:
    """Return the certificate password.

    Priority: 1) CERT_PFX_PASSWORD env var, 2) OS keyring.
    Raises KeyError if neither source has the password.
    """
    pwd = os.environ.get("CERT_PFX_PASSWORD")
    if pwd is not None:
        return pwd
    pwd = _get_keyring_password()
    if pwd is not None:
        return pwd
    raise KeyError("CERT_PFX_PASSWORD")


# --- YAML config ---


def load_yaml(path: Path) -> dict:
    """Load and parse a YAML file, returning the top-level dict."""
    return yaml.safe_load(path.read_text())


def load_emitter() -> dict:
    """Load emitter configuration from config/emitter.yaml."""
    return load_yaml(get_config_dir() / "emitter.yaml")


def load_client(name: str) -> dict:
    """Load a client configuration from config/clients/{name}.yaml."""
    return load_yaml(get_config_dir() / "clients" / f"{name}.yaml")


def list_clients() -> list[str]:
    """Return sorted list of client names (YAML file stems) from config/clients/."""
    clients_dir = get_config_dir() / "clients"
    if not clients_dir.exists():
        return []
    return sorted(f.stem for f in clients_dir.glob("*.yaml"))


def save_client(name: str, data: dict) -> Path:
    """Save a client configuration to config/clients/{name}.yaml (atomic write)."""
    clients_dir = get_config_dir() / "clients"
    clients_dir.mkdir(parents=True, exist_ok=True)
    path = clients_dir / f"{name}.yaml"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))
    os.replace(tmp, path)
    return path


def delete_client(name: str) -> None:
    """Delete a client configuration file config/clients/{name}.yaml."""
    path = get_config_dir() / "clients" / f"{name}.yaml"
    path.unlink()


def get_issued_dir(env: str) -> Path:
    """Return the issued-invoices directory for the given environment."""
    return get_data_dir() / env / "issued"


def migrate_data_layout() -> None:
    """One-time: move data/issued/*.xml → data/homologacao/issued/."""
    old = get_data_dir() / "issued"
    new = get_data_dir() / "homologacao" / "issued"
    if old.exists() and not new.exists():
        xml_files = list(old.glob("*.xml"))
        if xml_files:
            new.mkdir(parents=True, exist_ok=True)
            for f in xml_files:
                f.rename(new / f.name)
