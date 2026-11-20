# SPDX-License-Identifier: GPL-3.0-or-later
"""Puzzle del día / táctica diaria (lógica pura, sin pygame).

Los puzzles salen de la base pública de Lichess (CC0,
https://database.lichess.org/#puzzles) y vienen en
``assets/puzzles/lichess_puzzles.csv`` (lo arma ``tools/sample_puzzles.py``).

Formato de Lichess: el FEN es la posición *antes* de la jugada del rival; la
primera jugada de ``Moves`` la hace el rival sola y después el usuario tiene
que encontrar el resto (las respuestas del rival también son automáticas).

El progreso se guarda en settings.json bajo la clave ``"puzzles"``::

    {"solved": ["00008", ...], "streak": 3, "best_streak": 5,
     "last_daily": "2026-11-18"}

``streak`` = días seguidos resolviendo el puzzle del día.
"""

import csv
import datetime
import json
import random
from dataclasses import dataclass
from pathlib import Path

import chess

from .settings import save_setting, settings_path

PUZZLES_CSV = Path(__file__).resolve().parent / "assets" / "puzzles" / "lichess_puzzles.csv"
SETTINGS_KEY = "puzzles"

# Nombres en castellano de los temas más comunes de Lichess
THEME_NAMES = {
    "mate": "mate",
    "mateIn1": "mate en 1",
    "mateIn2": "mate en 2",
    "mateIn3": "mate en 3",
    "backRankMate": "mate en la última fila",
    "fork": "ataque doble",
    "pin": "clavada",
    "skewer": "enfilada",
    "discoveredAttack": "ataque a la descubierta",
    "hangingPiece": "pieza colgada",
    "sacrifice": "sacrificio",
    "deflection": "desviación",
    "attraction": "atracción",
    "trappedPiece": "pieza atrapada",
    "promotion": "coronación",
    "endgame": "final",
    "middlegame": "medio juego",
    "opening": "apertura",
    "advancedPawn": "peón avanzado",
    "crushing": "ventaja decisiva",
    "advantage": "ventaja",
    "short": "corto",
    "long": "largo",
    "veryLong": "muy largo",
    "oneMove": "una jugada",
    "kingsideAttack": "ataque al flanco de rey",
    "queensideAttack": "ataque al flanco de dama",
    "defensiveMove": "jugada defensiva",
    "quietMove": "jugada tranquila",
    "exposedKing": "rey expuesto",
    "intermezzo": "jugada intermedia",
    "doubleCheck": "jaque doble",
    "clearance": "despeje",
    "interference": "interferencia",
    "xRayAttack": "rayos X",
    "zugzwang": "zugzwang",
    "capturingDefender": "capturar al defensor",
    "rookEndgame": "final de torres",
    "queenEndgame": "final de damas",
    "pawnEndgame": "final de peones",
    "bishopEndgame": "final de alfiles",
    "knightEndgame": "final de caballos",
    "queenRookEndgame": "final de dama y torre",
}


@dataclass(frozen=True)
class Puzzle:
    id: str
    fen: str
    moves: tuple  # jugadas UCI; la primera es del rival
    rating: int
    themes: tuple
    game_url: str

    def theme_labels(self, limit=3):
        """Temas en castellano (los "tácticos" primero, sin largo/corto)."""
        skip = {"short", "long", "veryLong", "oneMove", "advantage", "crushing", "master", "masterVsMaster", "superGM"}
        out = [THEME_NAMES.get(t, t) for t in self.themes if t not in skip]
        return out[:limit]


def load_puzzles(path=None):
    """Lee el CSV de puzzles (las líneas que empiezan con # son comentarios)."""
    path = Path(path) if path else PUZZLES_CSV
    with open(path, newline="", encoding="utf-8") as f:
        lines = [ln for ln in f if not ln.startswith("#")]
    puzzles = []
    for row in csv.DictReader(lines):
        try:
            moves = tuple(row["Moves"].split())
            if len(moves) < 2:
                continue
            puzzles.append(
                Puzzle(
                    row["PuzzleId"],
                    row["FEN"],
                    moves,
                    int(row["Rating"]),
                    tuple(row["Themes"].split()),
                    row.get("GameUrl", ""),
                )
            )
        except (KeyError, ValueError):
            continue
    return puzzles


def daily_index(date, count):
    """Índice del puzzle del día: mismo día -> mismo puzzle, y va rotando."""
    if count <= 0:
        raise ValueError("no hay puzzles")
    return date.toordinal() % count


def puzzle_of_the_day(puzzles, date=None):
    date = date or datetime.date.today()
    return puzzles[daily_index(date, len(puzzles))]


def random_puzzle(puzzles, solved=(), exclude=None, rng=None):
    """Otro puzzle al azar, preferentemente uno no resuelto."""
    rng = rng or random
    pool = [p for p in puzzles if p.id not in solved and p.id != exclude]
    if not pool:
        pool = [p for p in puzzles if p.id != exclude] or list(puzzles)
    return rng.choice(pool)


class PuzzleSession:
    """Estado de un puzzle en juego.

    ``board`` arranca con la jugada del rival ya hecha; ``try_move`` devuelve
    "wrong", "correct" (falta más; el rival responde con ``opponent_reply``)
    o "solved"."""

    def __init__(self, puzzle):
        self.puzzle = puzzle
        self.board = chess.Board(puzzle.fen)
        self.ply = 0  # índice en puzzle.moves de la próxima jugada
        self.mistakes = 0
        self.hint_used = False
        self.solution_shown = False
        self.solved = False
        self.last_move = None
        self.opponent_reply()  # jugada inicial del rival
        self.player_color = self.board.turn

    @property
    def expected_move(self):
        if self.ply >= len(self.puzzle.moves):
            return None
        return chess.Move.from_uci(self.puzzle.moves[self.ply])

    @property
    def awaiting_opponent(self):
        return not self.solved and self.expected_move is not None and self.board.turn != self.player_color

    def opponent_reply(self):
        """Juega la respuesta automática del rival (si le toca). Devuelve la jugada."""
        move = self.expected_move
        if move is None or self.solved:
            return None
        self.board.push(move)
        self.last_move = move
        self.ply += 1
        return move

    def try_move(self, move):
        if self.solved or self.awaiting_opponent or move not in self.board.legal_moves:
            return "wrong"
        expected = self.expected_move
        mate = self._gives_mate(move)
        if move != expected and not mate:
            self.mistakes += 1
            return "wrong"
        self.board.push(move)
        self.last_move = move
        self.ply += 1
        if mate or self.ply >= len(self.puzzle.moves):
            self.solved = True
            return "solved"
        return "correct"

    def _gives_mate(self, move):
        b = self.board.copy(stack=False)
        b.push(move)
        return b.is_checkmate()

    def hint_square(self):
        """Casilla de la pieza que hay que mover (pista)."""
        move = self.expected_move
        if move is None or self.awaiting_opponent:
            return None
        self.hint_used = True
        return move.from_square

    def show_solution(self):
        """Devuelve la jugada correcta (cuenta como puzzle no resuelto limpio)."""
        move = self.expected_move
        if move is None or self.awaiting_opponent:
            return None
        self.solution_shown = True
        return move

    def promotion_for(self, from_sq, to_sq):
        """Pieza de coronación: la de la solución si coincide, si no dama."""
        exp = self.expected_move
        if exp and exp.from_square == from_sq and exp.to_square == to_sq and exp.promotion:
            return exp.promotion
        return chess.QUEEN

    @property
    def clean(self):
        """Resuelto sin errores y sin mirar la solución."""
        return self.solved and self.mistakes == 0 and not self.solution_shown


# ─── PROGRESO ──────────────────────────────────────────────────────────────────
def default_progress():
    return {"solved": [], "streak": 0, "best_streak": 0, "last_daily": ""}


def load_progress(path=None):
    path = Path(path) if path else settings_path()
    prog = default_progress()
    try:
        data = json.loads(path.read_text(encoding="utf-8")).get(SETTINGS_KEY)
    except (OSError, ValueError, AttributeError):
        data = None
    if isinstance(data, dict):
        if isinstance(data.get("solved"), list):
            prog["solved"] = [str(x) for x in data["solved"]]
        for key in ("streak", "best_streak"):
            try:
                prog[key] = max(0, int(data.get(key, 0)))
            except (TypeError, ValueError):
                pass
        if isinstance(data.get("last_daily"), str):
            prog["last_daily"] = data["last_daily"]
    return prog


def record_solved(progress, puzzle_id, daily=False, date=None):
    """Marca un puzzle resuelto. Si es el del día, actualiza la racha."""
    prog = dict(progress)
    prog["solved"] = list(progress.get("solved", []))
    if puzzle_id not in prog["solved"]:
        prog["solved"].append(puzzle_id)
    if daily:
        date = date or datetime.date.today()
        today = date.isoformat()
        yesterday = (date - datetime.timedelta(days=1)).isoformat()
        last = prog.get("last_daily", "")
        if last != today:
            prog["streak"] = prog.get("streak", 0) + 1 if last == yesterday else 1
            prog["last_daily"] = today
        prog["best_streak"] = max(prog.get("best_streak", 0), prog["streak"])
    return prog


def current_streak(progress, date=None):
    """Racha vigente: si ayer ni hoy se resolvió el del día, vale 0."""
    date = date or datetime.date.today()
    last = progress.get("last_daily", "")
    ok = (date.isoformat(), (date - datetime.timedelta(days=1)).isoformat())
    return progress.get("streak", 0) if last in ok else 0


def save_progress(progress, path=None):
    return save_setting(SETTINGS_KEY, progress, path)
