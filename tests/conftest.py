"""Configuración común de los tests: pygame sin pantalla ni audio."""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# Nunca tocar la carpeta real del usuario (partidas.db / settings.json)
import tempfile  # noqa: E402
os.environ["CABRECHESS_DATA_DIR"] = tempfile.mkdtemp(prefix="cabrechess-tests-")
os.environ.pop("CABRECHESS_STOCKFISH", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402


@pytest.fixture
def game():
    import cabrechess
    g = cabrechess.CabreChess()
    yield g
