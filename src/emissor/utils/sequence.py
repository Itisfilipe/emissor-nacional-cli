from __future__ import annotations

import json
import os
from contextlib import contextmanager

from filelock import FileLock

from emissor.config import DATA_DIR

SEQUENCE_FILE = DATA_DIR / "sequence.json"


@contextmanager
def _locked():
    """Hold an exclusive file lock during sequence read-modify-write."""
    SEQUENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock_path = SEQUENCE_FILE.with_suffix(".lock")
    lock = FileLock(lock_path)
    with lock:
        yield


def _load() -> dict:
    if SEQUENCE_FILE.exists():
        return json.loads(SEQUENCE_FILE.read_text())
    return {"n_dps": 0}


def _save(data: dict) -> None:
    SEQUENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SEQUENCE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, SEQUENCE_FILE)


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
