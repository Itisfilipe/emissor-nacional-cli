from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock

from emissor import config as _config


def _sequence_file() -> Path:
    return _config.get_data_dir() / "sequence.json"


@contextmanager
def _locked():
    """Hold an exclusive file lock during sequence read-modify-write."""
    sf = _sequence_file()
    sf.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(sf.with_suffix(".lock"))
    with lock:
        yield


def _load() -> dict:
    sf = _sequence_file()
    if sf.exists():
        return json.loads(sf.read_text())
    return {"n_dps": 0}


def _save(data: dict) -> None:
    sf = _sequence_file()
    sf.parent.mkdir(parents=True, exist_ok=True)
    tmp = sf.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, sf)


def current_n_dps() -> int:
    with _locked():
        return _load()["n_dps"]


def next_n_dps() -> int:
    with _locked():
        data = _load()
        data["n_dps"] += 1
        _save(data)
        return data["n_dps"]


def peek_next_n_dps() -> int:
    """Return the next sequence number without persisting it."""
    with _locked():
        return _load()["n_dps"] + 1


def set_n_dps(value: int) -> None:
    with _locked():
        data = _load()
        data["n_dps"] = value
        _save(data)
