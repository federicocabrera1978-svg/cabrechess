# SPDX-License-Identifier: GPL-3.0-or-later
"""Chess960 / Fischer Random (B11, parte 2).

Funciones puras sobre python-chess (sin pygame) para poder testearlas:

- Posición inicial al azar entre las 960 (numeradas 0 a 959 como en el
  esquema de Scharnagl; la 518 es la posición clásica).
- Enroque 960: python-chess lo codifica como "rey captura su torre" (p. ej.
  ``b1a1``). En la interfaz se puede enrocar llevando el rey **sobre su torre**
  (la forma sin ambigüedad) o **a la casilla final del rey** (g1 / c1), siempre
  que esa casilla no sea además una jugada normal del rey.
"""
import random

import chess

VARIANTS = ("standard", "chess960")
VARIANT_LABELS = {"standard": "Clásico", "chess960": "Chess960"}
POSITIONS = 960
STANDARD_POSITION = 518


def random_position(rng=None):
    """Número de posición al azar (0 a 959)."""
    return (rng or random).randrange(POSITIONS)


def new_board(position=None, rng=None):
    """Tablero Chess960 en la posición ``position`` (al azar si es None)."""
    if position is None:
        position = random_position(rng)
    if not 0 <= int(position) < POSITIONS:
        raise ValueError(f"posición Chess960 fuera de rango: {position}")
    return chess.Board.from_chess960_pos(int(position))


def position_number(board):
    """Número (0-959) de la posición inicial de la partida, o None si no es
    Chess960 o si arrancó desde una posición que no es inicial."""
    if board is None or not board.chess960:
        return None
    return board.root().chess960_pos()


def variant_label(board):
    """Texto para mostrar: "Chess960 · posición 123" ("" si es clásico)."""
    if board is None or not board.chess960:
        return ""
    n = position_number(board)
    return "Chess960" if n is None else f"Chess960 · posición {n}"


def castling_squares(board, move):
    """(rey_desde, rey_hasta, torre_desde, torre_hasta) de un enroque legal
    en ``board`` (posición ANTES de jugarlo). Sirve para el estándar (e1g1) y
    para el 960 (rey→torre)."""
    color = board.turn
    rank = chess.square_rank(move.from_square)
    kingside = board.is_kingside_castling(move)
    own_rook = chess.Piece(chess.ROOK, color)
    if board.piece_at(move.to_square) == own_rook:
        rook_from = move.to_square
    else:
        rook_from = chess.square(7 if kingside else 0, rank)
    king_to = chess.square(6 if kingside else 2, rank)
    rook_to = chess.square(5 if kingside else 3, rank)
    return move.from_square, king_to, rook_from, rook_to


def castling_move_to(board, from_sq, to_sq):
    """Enroque legal del rey en ``from_sq`` que el usuario pidió soltando el
    rey en ``to_sq``: sobre su torre o en la casilla final del rey. None si no
    hay. Si ``to_sq`` es también una jugada normal del rey, gana la normal (la
    decide quien llama: esto se usa solo como último recurso)."""
    for move in board.legal_moves:
        if move.from_square != from_sq or not board.is_castling(move):
            continue
        _kf, king_to, rook_from, _rt = castling_squares(board, move)
        if to_sq in (move.to_square, king_to, rook_from):
            return move
    return None


def fen_is_chess960(board):
    """True si un tablero cargado por FEN necesita reglas de Chess960 (derechos
    de enroque con torres o rey fuera de sus casillas clásicas)."""
    return bool(board.castling_rights) and board.has_chess960_castling_rights()
