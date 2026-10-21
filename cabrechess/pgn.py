# SPDX-License-Identifier: GPL-3.0-or-later
"""Exportación de partidas a PGN."""
import datetime

import chess

MODE_TAGS = {"pvp": "PvP", "vsai": "vs IA", "analysis": "Análisis"}


def game_result(board):
    """Resultado PGN de la posición: 1-0, 0-1, 1/2-1/2 o * (en curso)."""
    if board.is_checkmate():
        return "0-1" if board.turn == chess.WHITE else "1-0"
    if board.is_stalemate() or board.is_insufficient_material():
        return "1/2-1/2"
    return "*"


def build_pgn(board, move_history_san, mode, white_name, black_name, now=None):
    """Arma el texto PGN. Devuelve (pgn_text, date_str)."""
    now = now or datetime.datetime.now()
    date_str = now.strftime("%Y.%m.%d")
    mode_tag = MODE_TAGS.get(mode, "?")
    result = game_result(board)

    lines = [
        f'[Event "CabreChess — {mode_tag}"]',
        '[Site "CabreChess by Federico Cabrera"]',
        f'[Date "{date_str}"]',
        f'[White "{white_name}"]',
        f'[Black "{black_name}"]',
        f'[Result "{result}"]',
        '',
    ]

    # Movimientos en formato PGN
    moves_line = ""
    for i, san in enumerate(move_history_san):
        if i % 2 == 0:
            moves_line += f"{i//2 + 1}. "
        moves_line += san + " "
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
