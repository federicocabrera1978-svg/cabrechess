# SPDX-License-Identifier: GPL-3.0-or-later
"""Backend OPCIONAL de análisis con Stockfish (protocolo UCI vía python-chess).

Solo se importa y se usa si el usuario configuró "stockfish_path" en
settings.json (o CABRECHESS_STOCKFISH). Es el ÚNICO módulo que lanza un
proceso externo; por defecto el análisis corre con el motor propio, dentro
del proceso.
"""
import chess
import chess.engine


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
