import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def dades_temporals(tmp_path, monkeypatch):
    """Cada test fa servir un directori de dades propi."""
    from canconer import basedades

    monkeypatch.setattr(basedades, "DIRECTORI", tmp_path)
    yield tmp_path
