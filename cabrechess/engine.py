# SPDX-License-Identifier: GPL-3.0-or-later
"""Motor propio: minimax con poda alfa-beta."""
import math
import random

import chess


class SimpleEngine:
    """Motor propio: minimax con poda alfa-beta y tablas pieza-casilla.
    No usa Stockfish ni ningún motor externo."""
    PIECE_VALUES = {
        chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
        chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000,
    }
    PST = {  # Piece-square tables simplificadas
        chess.PAWN: [
             0,  0,  0,  0,  0,  0,  0,  0,
            50, 50, 50, 50, 50, 50, 50, 50,
            10, 10, 20, 30, 30, 20, 10, 10,
             5,  5, 10, 25, 25, 10,  5,  5,
             0,  0,  0, 20, 20,  0,  0,  0,
             5, -5,-10,  0,  0,-10, -5,  5,
             5, 10, 10,-20,-20, 10, 10,  5,
             0,  0,  0,  0,  0,  0,  0,  0,
        ],
        chess.KNIGHT: [
            -50,-40,-30,-30,-30,-30,-40,-50,
            -40,-20,  0,  0,  0,  0,-20,-40,
            -30,  0, 10, 15, 15, 10,  0,-30,
            -30,  5, 15, 20, 20, 15,  5,-30,
            -30,  0, 15, 20, 20, 15,  0,-30,
            -30,  5, 10, 15, 15, 10,  5,-30,
            -40,-20,  0,  5,  5,  0,-20,-40,
            -50,-40,-30,-30,-30,-30,-40,-50,
        ],
    }

    def evaluate(self, board):
        if board.is_checkmate():
            return -99999 if board.turn == chess.WHITE else 99999
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        score = 0
        for sq in chess.SQUARES:
            piece = board.piece_at(sq)
            if piece:
                val = self.PIECE_VALUES.get(piece.piece_type, 0)
                pst = self.PST.get(piece.piece_type, [0]*64)
                idx = chess.square_mirror(sq) if piece.color == chess.WHITE else sq
                val += pst[idx] if idx < len(pst) else 0
                score += val if piece.color == chess.WHITE else -val
        return score

    def minimax(self, board, depth, alpha, beta, maximizing):
        if depth == 0 or board.is_game_over():
            return self.evaluate(board), None
        best_move = None
        moves = list(board.legal_moves)
        random.shuffle(moves)
        if maximizing:
            best = -math.inf
            for move in moves:
                board.push(move)
                val, _ = self.minimax(board, depth-1, alpha, beta, False)
                board.pop()
                if val > best:
                    best, best_move = val, move
                alpha = max(alpha, best)
                if beta <= alpha:
                    break
            return best, best_move
        else:
            best = math.inf
            for move in moves:
                board.push(move)
                val, _ = self.minimax(board, depth-1, alpha, beta, True)
                board.pop()
                if val < best:
                    best, best_move = val, move
                beta = min(beta, best)
                if beta <= alpha:
                    break
            return best, best_move

    def get_best_move(self, board, depth=3):
        maximizing = board.turn == chess.WHITE
        _, move = self.minimax(board, depth, -math.inf, math.inf, maximizing)
        return move

    MATE_THRESHOLD = 90000

    def analyse(self, board, depth=3):
        """(score_cp_blancas, mate, jugada). mate es +1/-1 si el motor ve mate
        a favor de blancas/negras dentro de la profundidad, o None."""
        if board.is_game_over():
            return self.evaluate(board), None, None
        maximizing = board.turn == chess.WHITE
        score, move = self.minimax(board.copy(stack=False), depth, -math.inf, math.inf, maximizing)
        mate = None
        if abs(score) >= self.MATE_THRESHOLD:
            mate = 1 if score > 0 else -1
        return score, mate, move
