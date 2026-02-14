from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock

from emissor import config as _config


def _sequence_file() -> Path:
    return _config.get_data_dir() / "sequence.json"


@contextmanager
def _locked() -> Iterator[None]:
    """Hold an exclusive file lock during sequence read-modify-write."""
    sf = _sequence_file()
    sf.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(sf.with_suffix(".lock"))
    with lock:
        yield


def _load() -> dict[str, int]:
    sf = _sequence_file()
    if not sf.exists():
        return {"homologacao": 0, "producao": 0}
    data = json.loads(sf.read_text())
    # Migrate old format: {"n_dps": N} -> {"producao": N, "homologacao": 0}
    if "n_dps" in data:
        migrated = {"producao": data["n_dps"], "homologacao": 0}
        _save(migrated)
        return migrated
    return data


def _save(data: dict[str, int]) -> None:
    sf = _sequence_file()
    sf.parent.mkdir(parents=True, exist_ok=True)
    tmp = sf.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, sf)


def current_n_dps(env: str = "homologacao") -> int:
    with _locked():
        return _load().get(env, 0)


def next_n_dps(env: str = "homologacao") -> int:
    with _locked():
        data = _load()
        data[env] = data.get(env, 0) + 1
        _save(data)
        return data[env]


def peek_next_n_dps(env: str = "homologacao") -> int:
    """Return the next sequence number without persisting it."""
    with _locked():
        return _load().get(env, 0) + 1


def set_n_dps(value: int, env: str = "homologacao") -> None:
    with _locked():
        data = _load()
        data[env] = value
        _save(data)
