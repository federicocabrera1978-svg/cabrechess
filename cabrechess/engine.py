# SPDX-License-Identifier: GPL-3.0-or-later
"""Motor propio: alfa-beta con profundización iterativa, búsqueda de quietud
y orden de jugadas MVV-LVA, con límite de tiempo opcional."""
import random
import time

import chess

INF = 10**9
MATE_SCORE = 99999


# Tiempo máximo de pensamiento por jugada según el nivel (profundidad del menú).
AI_TIME_LIMITS = {1: 0.5, 3: 1.5, 5: 3.0}


def ai_time_budget(depth, remaining=None, increment=0.0):
    """Segundos que puede pensar la IA en esta jugada: el tope del nivel,
    recortado según lo que le queda en el reloj para no perder por tiempo."""
    budget = AI_TIME_LIMITS.get(depth, 1.5)
    if remaining is not None:
        budget = min(budget, remaining / 30 + increment / 2, remaining * 0.4)
    return max(0.05, budget)


class _SearchTimeout(Exception):
    """Se acabó el tiempo (o se pidió parar) en medio de una iteración."""


class SimpleEngine:
    """Motor propio: alfa-beta (negamax) con profundización iterativa,
    búsqueda de quietud en capturas y orden de jugadas MVV-LVA.
    No usa Stockfish ni ningún motor externo.

    ``get_best_move(board, depth)`` y ``analyse(board, depth)`` siguen igual.
    Con ``time_limit`` (segundos) la búsqueda profundiza de a un nivel y, si se
    acaba el tiempo, devuelve la mejor jugada de la última iteración completa.
    ``stop_event`` (un ``threading.Event``) permite cortarla desde otro hilo."""
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

    MATE_THRESHOLD = 90000

    def evaluate(self, board):
        """Evaluación estática en centipeones, desde el punto de vista de las blancas."""
        if board.is_checkmate():
            return -MATE_SCORE if board.turn == chess.WHITE else MATE_SCORE
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        return self._material_pst(board)

    def _material_pst(self, board):
        score = 0
        for sq, piece in board.piece_map().items():
            val = self.PIECE_VALUES.get(piece.piece_type, 0)
            pst = self.PST.get(piece.piece_type)
            if pst:
                val += pst[chess.square_mirror(sq) if piece.color == chess.WHITE else sq]
            score += val if piece.color == chess.WHITE else -val
        return score

    # ── Orden de jugadas ────────────────────────────────────────────────
    def _move_key(self, board, move, pv_move=None):
        """Más alta = se prueba antes: la mejor jugada de la iteración anterior,
        capturas por MVV-LVA (víctima más valiosa, atacante más barato),
        promociones y después el resto."""
        if move == pv_move:
            return 10**7
        key = 0
        if board.is_capture(move):
            victim = chess.PAWN if board.is_en_passant(move) else board.piece_type_at(move.to_square)
            attacker = board.piece_type_at(move.from_square)
            key += 10**5 + 10 * self.PIECE_VALUES[victim] - self.PIECE_VALUES[attacker] // 10
        if move.promotion:
            key += 10**5 + self.PIECE_VALUES[move.promotion]
        return key

    def order_moves(self, board, moves, pv_move=None):
        """Ordena las jugadas para que la poda alfa-beta corte antes. Entre
        jugadas con la misma clave se respeta el orden recibido (sort estable)."""
        return sorted(moves, key=lambda m: self._move_key(board, m, pv_move), reverse=True)

    # ── Búsqueda ────────────────────────────────────────────────────────
    def _check_time(self):
        self._nodes += 1
        if self._nodes & 511 == 0:
            if self._stop_event is not None and self._stop_event.is_set():
                raise _SearchTimeout
            if self._deadline is not None and time.perf_counter() >= self._deadline:
                raise _SearchTimeout

    def _side_eval(self, board):
        val = self._material_pst(board)
        return val if board.turn == chess.WHITE else -val

    def quiescence(self, board, alpha, beta, ply):
        """Sigue solo capturas y promociones hasta una posición tranquila,
        para no evaluar en medio de un cambio de piezas."""
        self._check_time()
        if board.is_checkmate():
            return -MATE_SCORE + ply
        if board.is_insufficient_material():
            return 0
        stand = self._side_eval(board)
        if stand >= beta:
            return stand
        alpha = max(alpha, stand)
        noisy = [m for m in board.legal_moves if m.promotion or board.is_capture(m)]
        for move in self.order_moves(board, noisy):
            board.push(move)
            score = -self.quiescence(board, -beta, -alpha, ply + 1)
            board.pop()
            if score >= beta:
                return score
            alpha = max(alpha, score)
        return alpha

    def negamax(self, board, depth, alpha, beta, ply, pv_move=None):
        """Devuelve (score desde el lado que mueve, mejor jugada)."""
        self._check_time()
        if ply > 0 and (board.is_insufficient_material() or board.halfmove_clock >= 100
                        or board.is_repetition(3)):
            return 0, None
        moves = list(board.legal_moves)
        if not moves:
            return (-MATE_SCORE + ply if board.is_check() else 0), None
        if depth <= 0:
            return self.quiescence(board, alpha, beta, ply), None
        self._rng.shuffle(moves)      # variedad entre jugadas equivalentes
        best, best_move = -INF, None
        for move in self.order_moves(board, moves, pv_move):
            board.push(move)
            score = -self.negamax(board, depth - 1, -beta, -alpha, ply + 1)[0]
            board.pop()
            if score > best:
                best, best_move = score, move
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return best, best_move

    def search(self, board, depth=3, time_limit=None, stop_event=None):
        """Profundización iterativa de 1 a ``depth``. Devuelve
        (score para el lado que mueve, jugada, profundidad completada).
        No modifica ``board``."""
        board = board.copy()
        self._nodes = 0
        self._stop_event = stop_event
        self._deadline = time.perf_counter() + time_limit if time_limit else None
        self._rng = random.Random()
        moves = list(board.legal_moves)
        if not moves:
            return self._side_eval(board), None, 0
        # Respaldo por si se corta antes de terminar la primera iteración.
        best_score, best_move, done = 0, self.order_moves(board, moves)[0], 0
        try:
            for d in range(1, max(1, depth) + 1):
                try:
                    score, move = self.negamax(board, d, -INF, INF, 0, pv_move=best_move if done else None)
                except _SearchTimeout:
                    break
                if move is not None:
                    best_score, best_move, done = score, move, d
                if score >= MATE_SCORE - 1000:    # ya encontró mate: no hace falta seguir
                    break
        finally:
            self._stop_event = None
            self._deadline = None
        return best_score, best_move, done

    def get_best_move(self, board, depth=3, time_limit=None, stop_event=None):
        return self.search(board, depth, time_limit, stop_event)[1]

    def analyse(self, board, depth=3, time_limit=None):
        """(score_cp_blancas, mate, jugada). mate es +1/-1 si el motor ve mate
        a favor de blancas/negras dentro de la profundidad, o None."""
        if board.is_game_over():
            return self.evaluate(board), None, None
        score, move, _ = self.search(board, depth, time_limit)
        if board.turn == chess.BLACK:
            score = -score
        mate = None
        if abs(score) >= self.MATE_THRESHOLD:
            mate = 1 if score > 0 else -1
        return score, mate, move
