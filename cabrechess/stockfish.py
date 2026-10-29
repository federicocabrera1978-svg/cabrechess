# SPDX-License-Identifier: GPL-3.0-or-later
"""Backend OPCIONAL de Stockfish (protocolo UCI vía python-chess).

Solo se importa y se usa si el usuario configuró "stockfish_path" en
settings.json (o CABRECHESS_STOCKFISH). Es el ÚNICO módulo que lanza un
proceso externo; por defecto el análisis y la IA corren con el motor propio,
dentro del proceso.

Sirve para dos cosas:
- ``StockfishBackend``: análisis de la posición (mejor jugada + evaluación).
- ``StockfishPlayer``: rival en "Jugar contra IA" (B4), con la fuerza
  limitada por ``Skill Level`` según el nivel 1 a 6 del menú.
"""
import threading

import chess
import chess.engine

from .constants import STOCKFISH_SKILL as SKILL_BY_LEVEL
DEFAULT_SKILL_LEVEL = 3


def skill_for_level(level):
    """Skill Level de Stockfish para un nivel del menú (desconocido = nivel 3)."""
    return SKILL_BY_LEVEL.get(level, SKILL_BY_LEVEL[DEFAULT_SKILL_LEVEL])


class StockfishBackend:
    def __init__(self, path, time_limit=0.5):
        self.path = path
        self.time_limit = time_limit
        self._engine = None

    def analyse(self, board, depth=None):
        """Devuelve (score_cp_blancas, mate_en, jugada) como SimpleEngine.analyse."""
        if self._engine is None:
            self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
        info = self._engine.analyse(board, chess.engine.Limit(time=self.time_limit))
        pov = info["score"].white()
        move = (info.get("pv") or [None])[0]
        return pov.score(mate_score=100000), pov.mate(), move

    def close(self):
        if self._engine is not None:
            self._engine.quit()
            self._engine = None


class StockfishPlayer:
    """Stockfish como rival. Un solo proceso por partida/sesión, reutilizado
    entre jugadas. Es seguro llamarlo desde el hilo de la IA: las llamadas se
    serializan con un lock."""

    def __init__(self, path):
        self.path = path
        self._engine = None
        self._skill = None
        self._lock = threading.Lock()

    def play(self, board, level, time_limit):
        """Jugada de Stockfish para `board` con la fuerza del nivel 1-6.
        Lanza OSError / chess.engine.EngineError si el motor no anda."""
        with self._lock:
            if self._engine is None:
                self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
                self._skill = None
            skill = skill_for_level(level)
            if skill != self._skill and "Skill Level" in self._engine.options:
                self._engine.configure({"Skill Level": skill})
            self._skill = skill
            result = self._engine.play(board, chess.engine.Limit(time=max(0.05, time_limit)))
            return result.move

    def close(self):
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.quit()
                except (chess.engine.EngineError, OSError):
                    pass
                self._engine = None
                self._skill = None
