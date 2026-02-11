from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


def _resolve_dir(env_var: str, default_subdir: str) -> Path:
    """Resolve a directory from an env var or repo layout detection.

    Raises RuntimeError when neither source is available so we never
    silently bind to the current working directory.
    """
    from_env = os.environ.get(env_var)
    if from_env:
        return Path(from_env)
    # Development layout: src/emissor/config.py -> ../../.. = project root
    project_root = Path(__file__).resolve().parent.parent.parent
    candidate = project_root / default_subdir
    if candidate.is_dir():
        return candidate
    raise RuntimeError(
        f"Could not find '{default_subdir}/' directory. "
        f"Set the {env_var} environment variable to the correct path."
    )


CONFIG_DIR = _resolve_dir("EMISSOR_CONFIG_DIR", "config")
DATA_DIR = _resolve_dir("EMISSOR_DATA_DIR", "data")

NFSE_NS = "http://www.sped.fazenda.gov.br/nfse"

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


def get_cert_path() -> str:
    return os.environ["CERT_PFX_PATH"]


def get_cert_password() -> str:
    return os.environ["CERT_PFX_PASSWORD"]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def load_emitter() -> dict:
    return load_yaml(CONFIG_DIR / "emitter.yaml")


def load_client(name: str) -> dict:
    return load_yaml(CONFIG_DIR / "clients" / f"{name}.yaml")


def list_clients() -> list[str]:
    """Return sorted list of client names (YAML file stems) from config/clients/."""
    clients_dir = CONFIG_DIR / "clients"
    if not clients_dir.exists():
        return []
    return sorted(f.stem for f in clients_dir.glob("*.yaml"))


def get_issued_dir(env: str) -> Path:
    """Return the issued-invoices directory for the given environment."""
    return DATA_DIR / env / "issued"


def migrate_data_layout() -> None:
    """One-time: move data/issued/*.xml → data/homologacao/issued/."""
    old = DATA_DIR / "issued"
    new = DATA_DIR / "homologacao" / "issued"
    if old.exists() and not new.exists():
        xml_files = list(old.glob("*.xml"))
        if xml_files:
            new.mkdir(parents=True, exist_ok=True)
            for f in xml_files:
                f.rename(new / f.name)
