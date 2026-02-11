"""Local invoice registry — tracks all known NFS-e keys with metadata.

The ADN API has no "list invoices" endpoint, so we maintain a local JSON
file to remember every invoice emitted through the CLI (or manually imported).
"""

from __future__ import annotations

import json
from typing import Any

from emissor.config import DATA_DIR

REGISTRY_PATH = DATA_DIR / "invoices.json"


def _load() -> list[dict[str, Any]]:
    if not REGISTRY_PATH.exists():
        return []
    try:
        return json.loads(REGISTRY_PATH.read_text())
    except (json.JSONDecodeError, ValueError):
        return []


def _save(entries: list[dict[str, Any]]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")


def list_invoices(env: str | None = None) -> list[dict[str, Any]]:
    """Return all registered invoices, optionally filtered by env."""
    entries = _load()
    if env:
        entries = [e for e in entries if e.get("env") == env]
    return entries


def add_invoice(
    chave: str,
    *,
    n_dps: int | None = None,
    client: str | None = None,
    valor_brl: str | None = None,
    competencia: str | None = None,
    emitted_at: str | None = None,
    env: str = "producao",
    status: str = "emitida",
) -> dict[str, Any]:
    """Add an invoice to the registry. Skips if chave already exists."""
    entries = _load()

    existing = next((e for e in entries if e.get("chave") == chave), None)
    if existing:
        return existing

    entry: dict[str, Any] = {
        "chave": chave,
        "env": env,
        "status": status,
    }
    if n_dps is not None:
        entry["n_dps"] = n_dps
    if client:
        entry["client"] = client
    if valor_brl:
        entry["valor_brl"] = valor_brl
    if competencia:
        entry["competencia"] = competencia
    if emitted_at:
        entry["emitted_at"] = emitted_at

    entries.append(entry)
    _save(entries)
    return entry


def remove_invoice(chave: str) -> bool:
    """Remove an invoice from the registry by chave."""
    entries = _load()
    filtered = [e for e in entries if e.get("chave") != chave]
    if len(filtered) == len(entries):
        return False
    _save(filtered)
    return True
