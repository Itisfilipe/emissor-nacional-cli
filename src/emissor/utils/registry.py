"""Local invoice registry — tracks all known NFS-e keys with metadata.

The ADN API has no "list invoices" endpoint, so we maintain a local JSON
file to remember every invoice emitted through the CLI (or manually imported).
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from filelock import FileLock

from emissor import config as _config

logger = logging.getLogger(__name__)


def _registry_path() -> Path:
    return _config.get_data_dir() / "invoices.json"


def _sync_state_path() -> Path:
    return _config.get_data_dir() / "sync_state.json"


def _backup_corrupt(path: Path) -> Path:
    """Rename a corrupt file to a timestamped backup before it gets overwritten."""
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    backup = path.with_name(f"{path.name}.corrupt.{ts}")
    path.rename(backup)
    logger.warning("Corrupt file backed up: %s → %s", path, backup)
    return backup


@contextmanager
def _locked() -> Iterator[None]:
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
        _backup_corrupt(rp)
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
    client_slug: str | None = None,
    valor_brl: str | None = None,
    valor_usd: str | None = None,
    competencia: str | None = None,
    emitted_at: str | None = None,
    nsu: int | None = None,
    env: str = "producao",
    status: str = "emitida",
    overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Add an invoice to the registry. Skips if chave already exists."""
    optional = {
        "n_dps": n_dps,
        "client": client,
        "client_slug": client_slug,
        "valor_brl": valor_brl,
        "valor_usd": valor_usd,
        "competencia": competencia,
        "emitted_at": emitted_at,
        "nsu": nsu,
    }

    with _locked():
        entries = _load()

        existing = next((e for e in entries if e.get("chave") == chave), None)
        if existing:
            changed = False
            for key, value in optional.items():
                if value is not None and existing.get(key) is None:
                    existing[key] = value
                    changed = True
            if overrides and "overrides" not in existing:
                existing["overrides"] = overrides
                changed = True
            if changed:
                _save(entries)
            return existing

        entry: dict[str, Any] = {
            "chave": chave,
            "env": env,
            "status": status,
            **{k: v for k, v in optional.items() if v is not None},
        }
        if overrides:
            entry["overrides"] = overrides

        entries.append(entry)
        _save(entries)
        return entry


def update_invoice(
    *,
    n_dps: int,
    env: str,
    status: str | None = None,
    chave: str | None = None,
    error: str | None = None,
) -> dict[str, Any] | None:
    """Update an existing registry entry looked up by n_dps + env.

    Can change status, swap chave (e.g. draft → real key), and store/clear
    error messages.  Returns the updated entry, or None if not found.
    """
    with _locked():
        entries = _load()
        target = next(
            (e for e in entries if e.get("n_dps") == n_dps and e.get("env") == env),
            None,
        )
        if target is None:
            return None

        changed = False
        if status is not None and target.get("status") != status:
            target["status"] = status
            changed = True
        if chave is not None and target.get("chave") != chave:
            target["chave"] = chave
            changed = True
        if error is not None and target.get("error") != error:
            target["error"] = error
            changed = True
        # Clear error when promoting to a success status
        if status == "emitida" and "error" in target:
            del target["error"]
            changed = True

        if changed:
            _save(entries)
    return target


def find_invoice(chave: str, env: str | None = None) -> dict[str, Any] | None:
    """Look up a single invoice by chave, optionally filtered by env."""
    with _locked():
        entries = _load()
    for e in entries:
        if e.get("chave") == chave and (env is None or e.get("env") == env):
            return e
    return None


def remove_invoice(chave: str) -> bool:
    """Remove an invoice from the registry by chave."""
    with _locked():
        entries = _load()
        filtered = [e for e in entries if e.get("chave") != chave]
        if len(filtered) == len(entries):
            return False
        _save(filtered)
        return True


def get_last_overrides(client_slug: str, env: str) -> dict[str, str] | None:
    """Return override fields from the most recent invoice for a client.

    Prefers same-env matches; falls back to cross-env if none found.
    Entries without an ``overrides`` key (sync-originated or pre-feature) are
    skipped.
    """
    with _locked():
        entries = _load()

    # Scan in reverse (most recent first)
    same_env: dict[str, str] | None = None
    cross_env: dict[str, str] | None = None
    for entry in reversed(entries):
        if entry.get("client_slug") != client_slug:
            continue
        overrides = entry.get("overrides")
        if not overrides:
            continue
        if entry.get("env") == env:
            same_env = overrides
            break
        if cross_env is None:
            cross_env = overrides

    return same_env or cross_env


# --- Sync state (last-seen NSU per env) ---


@contextmanager
def _sync_locked() -> Iterator[None]:
    """Hold an exclusive file lock during sync-state read-modify-write."""
    sp = _sync_state_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(sp.with_suffix(".lock"))
    with lock:
        yield


def get_last_nsu(env: str) -> int:
    """Return the last-seen NSU for the given environment, or 0 if unknown."""
    with _sync_locked():
        sp = _sync_state_path()
        if not sp.exists():
            return 0
        try:
            data = json.loads(sp.read_text())
            return int(data.get(env, 0))
        except (json.JSONDecodeError, ValueError, TypeError):
            _backup_corrupt(sp)
            return 0


def set_last_nsu(env: str, nsu: int) -> None:
    """Persist the last-seen NSU for the given environment."""
    with _sync_locked():
        sp = _sync_state_path()
        sp.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, int] = {}
        if sp.exists():
            try:
                data = json.loads(sp.read_text())
            except (json.JSONDecodeError, ValueError):
                _backup_corrupt(sp)
                data = {}
        data[env] = nsu
        tmp = sp.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n")
        os.replace(tmp, sp)


# --- Health check (read-only, no locks) ---


@dataclass
class RegistryHealth:
    registry_ok: bool
    registry_count: int
    registry_corrupt_backups: list[str] = field(default_factory=list)
    sync_state_ok: bool = True
    sync_state_corrupt_backups: list[str] = field(default_factory=list)


def check_registry_health() -> RegistryHealth:
    """Probe registry and sync-state files for corruption (read-only)."""
    rp = _registry_path()
    sp = _sync_state_path()

    # Registry file
    registry_ok = True
    registry_count = 0
    if rp.exists():
        try:
            entries = json.loads(rp.read_text())
            registry_count = len(entries)
        except (json.JSONDecodeError, ValueError):
            registry_ok = False
    if rp.parent.exists():
        registry_backups = sorted(str(p) for p in rp.parent.glob(f"{rp.name}.corrupt.*"))
    else:
        registry_backups = []

    # Sync state file
    sync_ok = True
    if sp.exists():
        try:
            json.loads(sp.read_text())
        except (json.JSONDecodeError, ValueError):
            sync_ok = False
    if sp.parent.exists():
        sync_backups = sorted(str(p) for p in sp.parent.glob(f"{sp.name}.corrupt.*"))
    else:
        sync_backups = []

    return RegistryHealth(
        registry_ok=registry_ok,
        registry_count=registry_count,
        registry_corrupt_backups=registry_backups,
        sync_state_ok=sync_ok,
        sync_state_corrupt_backups=sync_backups,
    )
