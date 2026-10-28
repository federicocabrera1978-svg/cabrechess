# SPDX-License-Identifier: GPL-3.0-or-later
"""Exportación e importación de partidas en PGN / FEN.

chess.pgn se importa solo dentro de las funciones que lo necesitan: ese módulo
carga chess.engine, y no queremos eso al arrancar (Avast / tests sin procesos).
"""
import datetime
import io
from pathlib import Path

import chess

from .openings import opening_for_board

MODE_TAGS = {"pvp": "PvP", "vsai": "vs IA", "analysis": "Análisis"}


def game_result(board):
    """Resultado PGN de la posición: 1-0, 0-1, 1/2-1/2 o * (en curso)."""
    if board.is_checkmate():
        return "0-1" if board.turn == chess.WHITE else "1-0"
    if board.is_stalemate() or board.is_insufficient_material():
        return "1/2-1/2"
    if board.is_seventyfive_moves() or board.is_fivefold_repetition():
        return "1/2-1/2"
    return "*"


def build_pgn(board, move_history_san, mode, white_name, black_name, now=None,
              result=None, termination=None, time_control=None):
    """Arma el texto PGN con chess.pgn. Devuelve (pgn_text, date_str)."""
    import chess.pgn

    now = now or datetime.datetime.now()
    date_str = now.strftime("%Y.%m.%d")
    mode_tag = MODE_TAGS.get(mode, "?")
    result = result or game_result(board)

    game = chess.pgn.Game()
    game.headers["Event"] = f"CabreChess — {mode_tag}"
    game.headers["Site"] = "CabreChess by Federico Cabrera"
    game.headers["Date"] = date_str
    game.headers["White"] = white_name
    game.headers["Black"] = black_name
    game.headers["Result"] = result
    if time_control:
        game.headers["TimeControl"] = time_control
    if termination:
        game.headers["Termination"] = termination

    root = board.root()
    if root.fen() != chess.STARTING_FEN:
        game.setup(root)

    node = game
    replay = root.copy(stack=False)
    moves = list(board.move_stack)
    if not moves and move_history_san:
        # Compatibilidad: callers que pasan solo SAN (tests de cabeceras).
        for san in move_history_san:
            move = replay.parse_san(san)
            node = node.add_variation(move)
            replay.push(move)
    else:
        for move in moves:
            if move not in replay.legal_moves:
                break
            node = node.add_variation(move)
            replay.push(move)

    opening = opening_for_board(board if moves else replay)
    if opening:
        game.headers["ECO"] = opening[0]
        game.headers["Opening"] = opening[1]

    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
    pgn_text = game.accept(exporter)
    if not pgn_text.endswith("\n"):
        pgn_text += "\n"
    return pgn_text, date_str


def parse_pgn(text):
    """Parsea un PGN. Devuelve (game, None) o (None, mensaje_de_error)."""
    import chess.pgn

    if text is None or not str(text).strip():
        return None, "PGN vacío"
    game = chess.pgn.read_game(io.StringIO(str(text)))
    if game is None:
        return None, "PGN inválido"
    return game, None


def parse_fen(fen):
    """Valida un FEN. Devuelve (Board, None) o (None, mensaje_de_error)."""
    fen = (fen or "").strip()
    if not fen:
        return None, "FEN vacío"
    try:
        board = chess.Board(fen)
    except ValueError as e:
        return None, f"FEN inválido: {e}"
    return board, None


def moves_from_game(game):
    """Jugadas legales de la línea principal, desde el tablero inicial del PGN."""
    board = game.board()
    moves = []
    for move in game.mainline_moves():
        if move not in board.legal_moves:
            break
        moves.append(move)
        board.push(move)
    return moves


def default_pgn_dir():
    home = Path.home()
    docs = home / "Documents"
    return (docs if docs.is_dir() else home) / "CabreChess"


def default_pgn_path(now=None, base_dir=None):
    now = now or datetime.datetime.now()
    base = Path(base_dir) if base_dir else default_pgn_dir()
    return base / f"CabreChess_{now.strftime('%Y%m%d_%H%M%S')}.pgn"


def write_pgn(pgn_text, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pgn_text, encoding="utf-8")
    return path


def read_pgn_file(path):
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"No se pudo leer: {e}"
    return text, None
