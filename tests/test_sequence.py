from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from emissor.utils import sequence


def test_sequence_increment(tmp_path: Path):
    with patch("emissor.config.get_data_dir", return_value=tmp_path):
        assert sequence.current_n_dps("homologacao") == 0
        assert sequence.next_n_dps("homologacao") == 1
        assert sequence.next_n_dps("homologacao") == 2
        assert sequence.current_n_dps("homologacao") == 2


def test_set_sequence(tmp_path: Path):
    with patch("emissor.config.get_data_dir", return_value=tmp_path):
        sequence.set_n_dps(10, "homologacao")
        assert sequence.current_n_dps("homologacao") == 10
        assert sequence.next_n_dps("homologacao") == 11


def test_peek_does_not_persist(tmp_path: Path):
    with patch("emissor.config.get_data_dir", return_value=tmp_path):
        assert sequence.next_n_dps("homologacao") == 1
        assert sequence.peek_next_n_dps("homologacao") == 2
        assert sequence.peek_next_n_dps("homologacao") == 2
        assert sequence.current_n_dps("homologacao") == 1
        assert sequence.next_n_dps("homologacao") == 2


def test_per_env_isolation(tmp_path: Path):
    """Incrementing one env does not affect the other."""
    with patch("emissor.config.get_data_dir", return_value=tmp_path):
        sequence.next_n_dps("homologacao")
        sequence.next_n_dps("homologacao")
        sequence.next_n_dps("producao")

        assert sequence.current_n_dps("homologacao") == 2
        assert sequence.current_n_dps("producao") == 1


def test_old_format_migration(tmp_path: Path):
    """Old {"n_dps": N} format is migrated to {"producao": N, "homologacao": 0}."""
    sf = tmp_path / "sequence.json"
    sf.write_text(json.dumps({"n_dps": 42}))

    with patch("emissor.config.get_data_dir", return_value=tmp_path):
        assert sequence.current_n_dps("producao") == 42
        assert sequence.current_n_dps("homologacao") == 0

        # Verify migrated format on disk
        data = json.loads(sf.read_text())
        assert "n_dps" not in data
        assert data["producao"] == 42
        assert data["homologacao"] == 0


def test_set_and_peek_per_env(tmp_path: Path):
    with patch("emissor.config.get_data_dir", return_value=tmp_path):
        sequence.set_n_dps(5, "homologacao")
        sequence.set_n_dps(100, "producao")

        assert sequence.peek_next_n_dps("homologacao") == 6
        assert sequence.peek_next_n_dps("producao") == 101
