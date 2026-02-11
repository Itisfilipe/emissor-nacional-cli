from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from emissor.utils import sequence


def test_sequence_increment(tmp_path: Path):
    seq_file = tmp_path / "sequence.json"
    with patch.object(sequence, "SEQUENCE_FILE", seq_file):
        assert sequence.current_n_dps() == 0
        assert sequence.next_n_dps() == 1
        assert sequence.next_n_dps() == 2
        assert sequence.current_n_dps() == 2


def test_set_sequence(tmp_path: Path):
    seq_file = tmp_path / "sequence.json"
    with patch.object(sequence, "SEQUENCE_FILE", seq_file):
        sequence.set_n_dps(10)
        assert sequence.current_n_dps() == 10
        assert sequence.next_n_dps() == 11


def test_peek_does_not_persist(tmp_path: Path):
    seq_file = tmp_path / "sequence.json"
    with patch.object(sequence, "SEQUENCE_FILE", seq_file):
        assert sequence.next_n_dps() == 1
        assert sequence.peek_next_n_dps() == 2
        assert sequence.peek_next_n_dps() == 2
        assert sequence.current_n_dps() == 1
        assert sequence.next_n_dps() == 2
