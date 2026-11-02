# SPDX-License-Identifier: GPL-3.0-or-later
"""Revisión de la partida terminada: marca imprecisiones (?!), errores (?) y
errores graves (??), como el análisis de Lichess (parte de B9).

Se evalúa cada posición de la partida con el motor propio, en un hilo del
MISMO proceso (sin subprocesos: amigable con Avast). Para clasificar una jugada
se mira cuánto bajaron las chances de ganar del bando que movió, con la misma
curva y los mismos umbrales que usa Lichess. Así no se marcan como error las
jugadas de una posición que ya estaba ganada o perdida por mucho.
"""
import math
import threading

import chess

from .engine import SimpleEngine

# Umbrales sobre la caída de chances de ganar (escala -1..1, como Lichess)
INACCURACY, MISTAKE, BLUNDER = 0.1, 0.2, 0.3
CP_CAP = 1500                     # centipawns máximos (los mates se recortan acá)
NAGS = {"?!": 6, "?": 2, "??": 4}  # $6, $2, $4 en PGN
LABELS = {"?!": "Imprecisiones", "?": "Errores", "??": "Errores graves"}


def winning_chances(cp):
    """Chances de ganar de blancas en -1..1 para una evaluación en centipawns."""
    cp = max(-CP_CAP, min(CP_CAP, cp))
    return 2 / (1 + math.exp(-0.00368208 * cp)) - 1


def classify(cp_before, cp_after, mover):
    """'', '?!', '?' o '??' para la jugada de `mover` (chess.WHITE/BLACK).
    Las evaluaciones son en centipawns desde el punto de vista de blancas."""
    loss = winning_chances(cp_before) - winning_chances(cp_after)
    if mover == chess.BLACK:
        loss = -loss
    if loss >= BLUNDER:
        return "??"
    if loss >= MISTAKE:
        return "?"
    if loss >= INACCURACY:
        return "?!"
    return ""


def annotate(evals, root_turn=chess.WHITE):
    """Marca cada jugada a partir de las evaluaciones de las posiciones
    (evals[0] = inicial, evals[i] = después de la jugada i)."""
    marks = []
    mover = root_turn
    for i in range(1, len(evals)):
        marks.append(classify(evals[i - 1], evals[i], mover))
        mover = not mover
    return marks


def summary(marks, root_turn=chess.WHITE):
    """{color: {'?!': n, '?': n, '??': n}} contando las marcas de cada bando."""
    out = {chess.WHITE: dict.fromkeys(NAGS, 0), chess.BLACK: dict.fromkeys(NAGS, 0)}
    mover = root_turn
    for mark in marks:
        if mark:
            out[mover][mark] += 1
        mover = not mover
    return out


def position_eval(engine, board, depth, time_limit):
    """Evaluación en centipawns (blancas) de `board`, buscando."""
    if board.is_checkmate():
        return -CP_CAP if board.turn == chess.WHITE else CP_CAP
    if board.is_game_over(claim_draw=False):
        return 0
    score, mate, _move = engine.analyse(board, depth, time_limit)
    if mate:
        return CP_CAP if mate > 0 else -CP_CAP
    return int(score)


class GameReview:
    """Analiza en segundo plano todas las posiciones de una partida terminada."""

    def __init__(self, board, depth=2, time_limit=0.3):
        self.root = board.root()
        self.moves = list(board.move_stack)
        self.depth = depth
        self.time_limit = time_limit
        self.engine = SimpleEngine()
        self.evals = []
        self.marks = None
        self._stop = False
        self._lock = threading.Lock()
        self._thread = None

    @property
    def total(self):
        return len(self.moves) + 1

    def progress(self):
        """Fracción de posiciones ya evaluadas (0..1)."""
        with self._lock:
            return len(self.evals) / self.total

    def done(self):
        with self._lock:
            return self.marks is not None

    def start(self):
        self._thread = threading.Thread(target=self.run, daemon=True, name="cabrechess-review")
        self._thread.start()
        return self

    def stop(self):
        self._stop = True

    def wait(self, timeout=60.0):
        if self._thread is not None:
            self._thread.join(timeout)
        return self.done()

    def run(self):
        board = self.root.copy(stack=False)
        for i in range(self.total):
            if self._stop:
                return
            cp = position_eval(self.engine, board, self.depth, self.time_limit)
            with self._lock:
                self.evals.append(cp)
            if i < len(self.moves):
                board.push(self.moves[i])
        marks = annotate(self.evals, self.root.turn)
        with self._lock:
            self.marks = marks

    def mark(self, ply):
        """Marca de la jugada `ply` (0 = primera jugada) o '' si no hay/no terminó."""
        with self._lock:
            if self.marks is None or not 0 <= ply < len(self.marks):
                return ""
            return self.marks[ply]

    def nags(self):
        """{ply: NAG} para exportar en PGN."""
        with self._lock:
            if self.marks is None:
                return {}
            return {i: NAGS[m] for i, m in enumerate(self.marks) if m}

    def summary(self):
        with self._lock:
            if self.marks is None:
                return None
            return summary(self.marks, self.root.turn)


# Colores de las marcas en la lista de jugadas (como Lichess)
MARK_COLORS = {"?!": (230, 200, 70), "?": (232, 140, 50), "??": (222, 72, 60)}
