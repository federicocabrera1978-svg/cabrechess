# SPDX-License-Identifier: GPL-3.0-or-later
"""Análisis en segundo plano de la posición mostrada: mejor jugada + evaluación.

Por defecto usa el motor propio (SimpleEngine) en un hilo del MISMO proceso:
no lanza subprocesos (amigable con antivirus como Avast). Solo si el usuario
configura stockfish_path se usa Stockfish vía UCI (cabrechess.stockfish).
"""
import threading
from dataclasses import dataclass
from typing import Optional

import chess

from .engine import SimpleEngine


@dataclass
class AnalysisResult:
    fen: str
    score: int                  # centipawns desde el punto de vista de blancas
    mate: Optional[int]         # +1/-1 = mate a favor de blancas/negras
    move: Optional[chess.Move]
    san: str
    depth: int
    engine: str                 # "CabreChess" o "Stockfish"

    def score_text(self):
        if self.mate:
            return "#" if self.mate > 0 else "-#"
        return f"{self.score / 100:+.2f}"


class Analyzer:
    def __init__(self, depth=3, stockfish_path=""):
        self.depth = depth
        self.stockfish_path = stockfish_path or ""
        self.engine = SimpleEngine()
        self._backend = None
        self.error = ""
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._pending = None            # chess.Board a analizar
        self._results = {}              # fen -> AnalysisResult
        self._busy = False
        self._stop = False
        self._thread = None

    @property
    def engine_name(self):
        return "Stockfish" if self.stockfish_path and not self.error else "CabreChess"

    def request(self, board):
        """Pide analizar `board` (se copia). Si ya está en caché no hace nada."""
        fen = board.fen()
        with self._lock:
            if fen in self._results or (self._pending is not None and self._pending.fen() == fen):
                return
            self._pending = board.copy()
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True, name="cabrechess-analysis")
            self._thread.start()
        self._wake.set()

    def result(self, board):
        with self._lock:
            return self._results.get(board.fen())

    def busy(self):
        with self._lock:
            return self._busy or self._pending is not None

    def wait(self, board, timeout=30.0):
        """Para tests: espera el resultado de `board`."""
        import time
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            res = self.result(board)
            if res is not None:
                return res
            time.sleep(0.01)
        return None

    def stop(self):
        self._stop = True
        self._wake.set()
        if self._backend is not None:
            try:
                self._backend.close()
            except Exception:   # noqa: BLE001 - cerrar Stockfish nunca debe romper la UI
                pass

    def analyse_now(self, board):
        """Análisis sincrónico (lo usa el hilo y los tests)."""
        engine = "CabreChess"
        if self.stockfish_path and not self.error:
            try:
                if self._backend is None:
                    from .stockfish import StockfishBackend
                    self._backend = StockfishBackend(self.stockfish_path)
                score, mate, move = self._backend.analyse(board)
                if mate is not None:
                    mate = 1 if mate > 0 else -1
                engine = "Stockfish"
            except Exception as e:  # noqa: BLE001 - ruta inválida, motor roto, etc.
                self.error = f"Stockfish no disponible: {e}"
                score, mate, move = self.engine.analyse(board, self.depth)
        else:
            score, mate, move = self.engine.analyse(board, self.depth)
        san = board.san(move) if move is not None and move in board.legal_moves else ""
        return AnalysisResult(board.fen(), int(score), mate, move, san, self.depth, engine)

    def _run(self):
        while not self._stop:
            self._wake.wait()
            self._wake.clear()
            while not self._stop:
                with self._lock:
                    board, self._pending = self._pending, None
                    self._busy = board is not None
                if board is None:
                    break
                res = self.analyse_now(board)
                with self._lock:
                    if len(self._results) > 2000:
                        self._results.clear()
                    self._results[res.fen] = res
                    self._busy = False
