# SPDX-License-Identifier: GPL-3.0-or-later
"""Exportación de partidas a PGN."""
import datetime
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
    return "*"


def build_pgn(board, move_history_san, mode, white_name, black_name, now=None,
              result=None, termination=None, time_control=None):
    """Arma el texto PGN. Devuelve (pgn_text, date_str).
    result/termination permiten fijar el resultado cuando la posición no lo
    dice sola (p. ej. derrota por tiempo)."""
    now = now or datetime.datetime.now()
    date_str = now.strftime("%Y.%m.%d")
    mode_tag = MODE_TAGS.get(mode, "?")
    result = result or game_result(board)

    lines = [
        f'[Event "CabreChess — {mode_tag}"]',
        '[Site "CabreChess by Federico Cabrera"]',
        f'[Date "{date_str}"]',
        f'[White "{white_name}"]',
        f'[Black "{black_name}"]',
        f'[Result "{result}"]',
    ]
    root = board.root()
    if root.fen() != chess.STARTING_FEN:
        lines += ['[SetUp "1"]', f'[FEN "{root.fen()}"]']
    if time_control:
        lines.append(f'[TimeControl "{time_control}"]')
    if termination:
        lines.append(f'[Termination "{termination}"]')
    opening = opening_for_board(board)
    if opening:
        lines += [f'[ECO "{opening[0]}"]', f'[Opening "{opening[1]}"]']
    lines.append('')

    # Movimientos en formato PGN
    moves_line = ""
    number, white_to_move = root.fullmove_number, root.turn == chess.WHITE
    for i, san in enumerate(move_history_san):
        if white_to_move:
            moves_line += f"{number}. "
        elif i == 0:
            moves_line += f"{number}... "
        moves_line += san + " "
        if not white_to_move:
            number += 1
        white_to_move = not white_to_move
    moves_line += result
    # Partir en líneas de ~80 chars
    words = moves_line.split()
    line, pgn_moves = "", []
    for w in words:
        if len(line) + len(w) + 1 > 80:
            pgn_moves.append(line.rstrip())
            line = w + " "
        else:
            line += w + " "
    if line.strip():
        pgn_moves.append(line.rstrip())
    lines += pgn_moves

    return "\n".join(lines) + "\n", date_str


def default_pgn_dir():
    """Carpeta por defecto para guardar partidas si no hay diálogo de archivo:
    ~/Documents/CabreChess (o ~/CabreChess si no existe Documents)."""
    home = Path.home()
    docs = home / "Documents"
    return (docs if docs.is_dir() else home) / "CabreChess"


def default_pgn_path(now=None, base_dir=None):
    """Ruta por defecto con fecha y hora, para no pisar partidas anteriores."""
    now = now or datetime.datetime.now()
    base = Path(base_dir) if base_dir else default_pgn_dir()
    return base / f"CabreChess_{now.strftime('%Y%m%d_%H%M%S')}.pgn"


def write_pgn(pgn_text, path):
    """Escribe el PGN (UTF-8), creando la carpeta si hace falta. Devuelve la ruta."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pgn_text, encoding="utf-8")
    return path
