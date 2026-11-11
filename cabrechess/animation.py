# SPDX-License-Identifier: GPL-3.0-or-later
"""Qué se anima en cada jugada (A8, como en Lichess).

- La pieza que mueve se desliza de su casilla a la de destino.
- En el **enroque** se deslizan las dos piezas: el rey y la torre.
- La pieza **capturada** (también al capturar al paso) se desvanece en su
  casilla mientras llega la que captura.

Estas funciones son puras (solo usan python-chess) para poder testearlas sin
pantalla; la interfaz las usa para dibujar cada cuadro.
"""
from dataclasses import dataclass
from typing import Optional

import chess


@dataclass(frozen=True)
class Slide:
    """Una pieza que se desliza de una casilla a otra."""
    piece: chess.Piece
    from_square: int
    to_square: int


@dataclass(frozen=True)
class MoveAnimation:
    slides: tuple
    captured: Optional[chess.Piece] = None
    captured_square: Optional[int] = None

    def hidden_squares(self):
        """Casillas donde no hay que dibujar la pieza fija mientras dura la animación."""
        return {s.to_square for s in self.slides}


def captured_square(board, move):
    """Casilla de la pieza capturada (distinta del destino al capturar al paso)."""
    if board.is_en_passant(move):
        return chess.square(chess.square_file(move.to_square),
                            chess.square_rank(move.from_square))
    if board.is_castling(move):
        return None
    if board.piece_at(move.to_square) is not None:
        return move.to_square
    return None


def plan_animation(board, move):
    """Arma la animación de ``move`` sobre ``board`` (la posición ANTES de jugarla)."""
    piece = board.piece_at(move.from_square)
    if piece is None:
        return MoveAnimation(slides=())
    if board.is_castling(move):
        rank = chess.square_rank(move.from_square)
        kingside = board.is_kingside_castling(move)
        # En python-chess el enroque estándar es e1g1; en Chess960 puede ser rey→torre.
        if board.piece_at(move.to_square) == chess.Piece(chess.ROOK, piece.color):
            rook_from = move.to_square
        else:
            rook_from = chess.square(7 if kingside else 0, rank)
        king_to = chess.square(6 if kingside else 2, rank)
        rook_to = chess.square(5 if kingside else 3, rank)
        rook = board.piece_at(rook_from) or chess.Piece(chess.ROOK, piece.color)
        return MoveAnimation(slides=(
            Slide(piece, move.from_square, king_to),
            Slide(rook, rook_from, rook_to),
        ))
    sq = captured_square(board, move)
    captured = board.piece_at(sq) if sq is not None else None
    return MoveAnimation(slides=(Slide(piece, move.from_square, move.to_square),),
                         captured=captured, captured_square=sq)
