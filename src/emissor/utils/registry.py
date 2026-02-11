"""Local invoice registry — tracks all known NFS-e keys with metadata.

The ADN API has no "list invoices" endpoint, so we maintain a local JSON
file to remember every invoice emitted through the CLI (or manually imported).
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from filelock import FileLock

from emissor import config as _config


def _registry_path() -> Path:
    return _config.get_data_dir() / "invoices.json"


@contextmanager
def _locked():
    """Hold an exclusive file lock during registry read-modify-write."""
    rp = _registry_path()
    rp.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(rp.with_suffix(".lock"))
    with lock:
        yield


def _load() -> list[dict[str, Any]]:
    rp = _registry_path()
    if not rp.exists():
        return []
    try:
        return json.loads(rp.read_text())
    except (json.JSONDecodeError, ValueError):
        return []


def _save(entries: list[dict[str, Any]]) -> None:
    rp = _registry_path()
    rp.parent.mkdir(parents=True, exist_ok=True)
    tmp = rp.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, rp)


def list_invoices(env: str | None = None) -> list[dict[str, Any]]:
    """Return all registered invoices, optionally filtered by env."""
    with _locked():
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
    with _locked():
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
    with _locked():
        entries = _load()
        filtered = [e for e in entries if e.get("chave") != chave]
        if len(filtered) == len(entries):
            return False
        _save(filtered)
        return True
