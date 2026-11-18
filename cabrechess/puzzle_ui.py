# SPDX-License-Identifier: GPL-3.0-or-later
"""Pantalla "Puzzle del día" (mixin de CabreChess).

La lógica vive en ``puzzles.py``; acá solo se dibuja y se atienden clics y
teclas. Reusa el tablero, las piezas cburnett y los resaltados del juego."""

import datetime
import time

import chess
import pygame

from .constants import (
    ACCENT,
    ACCENT2,
    BG_COLOR,
    BOARD_SIZE,
    BOARD_X,
    BOARD_Y,
    BORDER_COLOR,
    DANGER,
    PANEL_COLOR,
    PANEL_W,
    PANEL_X,
    SQUARE_SIZE,
    TEXT_BRIGHT,
    TEXT_COLOR,
    TEXT_DIM,
    WINDOW_W,
)
from .sounds import sound_for_move
from .sprites import make_piece_sprite
from .puzzles import (
    PuzzleSession,
    current_streak,
    load_progress,
    load_puzzles,
    puzzle_of_the_day,
    random_puzzle,
    record_solved,
    save_progress,
)

PUZZLE_REPLY_DELAY = 0.5  # segundos antes de la respuesta automática del rival
HINT_COLOR = (81, 150, 200)
SOLUTION_ARROW = (21, 120, 27, 170)

FEEDBACK = {
    "start": ("Encontrá la mejor jugada", TEXT_COLOR),
    "correct": ("¡Correcto! Seguí…", ACCENT),
    "wrong": ("No es la jugada. Probá otra vez", DANGER),
    "solved": ("¡Correcto! Puzzle resuelto", ACCENT),
    "solution": ("Esta era la jugada", HINT_COLOR),
    "hint": ("Pista: mové la pieza marcada", HINT_COLOR),
}


class PuzzleScreenMixin:
    """Requiere los atributos de CabreChess (screen, fuentes, sq_to_pixel...)."""

    # ── estado ──
    def puzzle_list(self):
        if getattr(self, "_puzzles", None) is None:
            try:
                self._puzzles = load_puzzles()
            except OSError:
                self._puzzles = []
        return self._puzzles

    def open_puzzle(self, daily=True, puzzle=None, today=None):
        """Abre el puzzle del día (o uno dado / al azar si daily=False)."""
        puzzles = self.puzzle_list()
        if not puzzles:
            self.toast("No se encontraron los puzzles")
            return False
        self.puzzle_progress = load_progress()
        self.puzzle_today = today or datetime.date.today()
        if puzzle is None:
            if daily:
                puzzle = puzzle_of_the_day(puzzles, self.puzzle_today)
            else:
                cur = getattr(self, "puzzle", None)
                puzzle = random_puzzle(puzzles, self.puzzle_progress["solved"], exclude=cur.puzzle.id if cur else None)
        self.puzzle_daily = daily and puzzle.id == puzzle_of_the_day(puzzles, self.puzzle_today).id
        self.reset_game()
        self.mode = "puzzle"
        self.puzzle = PuzzleSession(puzzle)
        self.flipped = self.puzzle.player_color == chess.BLACK
        self.puzzle_feedback = "start"
        self.puzzle_hint_sq = None
        self.puzzle_arrow = None
        self.puzzle_reply_at = None
        self.puzzle_selected = None
        return True

    def puzzle_click_square(self, sq):
        s = self.puzzle
        if s.solved or s.awaiting_opponent:
            return
        piece = s.board.piece_at(sq)
        if self.puzzle_selected is None or (piece and piece.color == s.player_color):
            self.puzzle_selected = sq if piece and piece.color == s.player_color else None
            return
        from_sq, self.puzzle_selected = self.puzzle_selected, None
        moving = s.board.piece_at(from_sq)
        promo = None
        if moving and moving.piece_type == chess.PAWN and chess.square_rank(sq) in (0, 7):
            promo = s.promotion_for(from_sq, sq)
        move = chess.Move(from_sq, sq, promotion=promo)
        if move not in s.board.legal_moves:
            return
        self.puzzle_play(move)

    def puzzle_play(self, move):
        s = self.puzzle
        before = s.board.copy(stack=False)
        result = s.try_move(move)
        self.puzzle_feedback = result
        self.puzzle_arrow = None
        if result == "wrong":
            return result
        self.puzzle_hint_sq = None
        self._puzzle_sound(before, move)
        if result == "correct":
            self.puzzle_reply_at = time.time() + PUZZLE_REPLY_DELAY
        elif result == "solved":
            self.puzzle_finish()
        return result

    def _puzzle_sound(self, before, move):
        sound = getattr(self, "sound", None)
        if sound is not None:
            sound.play(sound_for_move(before, move, self.puzzle.board))

    def puzzle_finish(self):
        s = self.puzzle
        if s.solved and not s.solution_shown:
            self.puzzle_progress = record_solved(
                self.puzzle_progress, s.puzzle.id, daily=self.puzzle_daily, date=self.puzzle_today
            )
            save_progress(self.puzzle_progress)

    def puzzle_tick(self, now=None):
        """Respuesta automática del rival cuando pasó el delay."""
        if self.mode != "puzzle" or self.puzzle_reply_at is None:
            return
        now = time.time() if now is None else now
        if now >= self.puzzle_reply_at:
            self.puzzle_reply_at = None
            before = self.puzzle.board.copy(stack=False)
            move = self.puzzle.opponent_reply()
            if move is not None:
                self._puzzle_sound(before, move)

    def puzzle_hint(self):
        if self.puzzle_reply_at is not None:
            return
        self.puzzle_hint_sq = self.puzzle.hint_square()
        if self.puzzle_hint_sq is not None:
            self.puzzle_feedback = "hint"

    def puzzle_solution(self):
        """Muestra la jugada (flecha) y la juega; el rival responde solo."""
        if self.puzzle_reply_at is not None:
            return
        move = self.puzzle.show_solution()
        if move is None:
            return
        self.puzzle_play(move)
        self.puzzle_arrow = move
        if self.puzzle_feedback != "solved":
            self.puzzle_feedback = "solution"

    # ── layout (una sola definición para dibujo y clics) ──
    def puzzle_buttons(self):
        specs = [
            ("Pista", "hint", ACCENT2),
            ("Ver solución", "solution", (200, 180, 80)),
            ("Otro puzzle", "next", ACCENT),
            ("Puzzle del día", "daily", ACCENT),
            ("Menú", "menu", TEXT_COLOR),
        ]
        x, w, h = PANEL_X + 15, PANEL_W - 40, 38
        y0 = BOARD_Y + BOARD_SIZE - len(specs) * (h + 8) - 8
        return [
            (label, action, color, pygame.Rect(x, y0 + i * (h + 8), w, h))
            for i, (label, action, color) in enumerate(specs)
        ]

    def puzzle_action(self, action):
        if action == "hint":
            self.puzzle_hint()
        elif action == "solution":
            self.puzzle_solution()
        elif action == "next":
            self.open_puzzle(daily=False)
        elif action == "daily":
            self.open_puzzle(daily=True)
        elif action == "menu":
            self.go_menu()

    def handle_puzzle_click(self, pos):
        for _label, action, _color, rect in self.puzzle_buttons():
            if rect.collidepoint(pos):
                self.puzzle_action(action)
                return
        sq = self.pixel_to_sq(*pos)
        if sq is not None:
            self.puzzle_click_square(sq)

    def handle_puzzle_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.go_menu()
        elif key == pygame.K_h:
            self.puzzle_hint()
        elif key == pygame.K_s:
            self.puzzle_solution()
        elif key in (pygame.K_n, pygame.K_RIGHT):
            self.open_puzzle(daily=False)
        elif key == pygame.K_f:
            self.flip_board()
        elif key == pygame.K_t:
            self.cycle_board_theme()
        elif key == pygame.K_m:
            self.toggle_sound()

    # ── dibujo ──
    def draw_puzzle(self):
        s = self.puzzle
        board_rect = pygame.Rect(BOARD_X, BOARD_Y, BOARD_SIZE, BOARD_SIZE)
        pygame.draw.rect(self.screen, BORDER_COLOR, board_rect.inflate(4, 4), border_radius=3)
        self.screen.blit(self.board_surf, (BOARD_X, BOARD_Y))
        live = (self.board, self.last_move, self.selected_sq, self.legal_moves_from)
        self.board, self.last_move = s.board, s.last_move
        self.selected_sq = self.puzzle_selected
        self.legal_moves_from = (
            [m for m in s.board.legal_moves if m.from_square == self.puzzle_selected]
            if self.puzzle_selected is not None
            else []
        )
        try:
            self.draw_highlights()
            if self.puzzle_hint_sq is not None:
                x, y = self.sq_to_pixel(self.puzzle_hint_sq)
                pygame.draw.rect(self.screen, HINT_COLOR, (x, y, SQUARE_SIZE, SQUARE_SIZE), 5)
            self.draw_pieces()
            self.draw_coordinates()
            if self.puzzle_arrow is not None:
                overlay = pygame.Surface((BOARD_SIZE, BOARD_SIZE), pygame.SRCALPHA)
                self._draw_arrow(overlay, self.puzzle_arrow.from_square, self.puzzle_arrow.to_square, SOLUTION_ARROW)
                self.screen.blit(overlay, (BOARD_X, BOARD_Y))
        finally:
            self.board, self.last_move, self.selected_sq, self.legal_moves_from = live
        self.draw_puzzle_panel()

    def draw_puzzle_panel(self):
        s, p = self.puzzle, self.puzzle.puzzle
        panel = pygame.Rect(PANEL_X, BOARD_Y, PANEL_W - 10, BOARD_SIZE)
        pygame.draw.rect(self.screen, PANEL_COLOR, panel, border_radius=8)
        pygame.draw.rect(self.screen, BORDER_COLOR, panel, 1, border_radius=8)
        x, y = PANEL_X + 15, BOARD_Y + 14
        title = "Puzzle del día" if self.puzzle_daily else "Puzzle"
        self.screen.blit(self.font_large.render(title, True, TEXT_BRIGHT), (x, y))
        y += 40
        side = "Blancas" if s.player_color == chess.WHITE else "Negras"
        self.screen.blit(self.font_med.render(f"Juegan {side}", True, TEXT_COLOR), (x, y))
        y += 32
        self.screen.blit(self.font_small.render(f"Rating: {p.rating}", True, ACCENT2), (x, y))
        y += 24
        themes = ", ".join(p.theme_labels())
        for line in self._wrap(f"Temas: {themes}", PANEL_W - 45):
            self.screen.blit(self.font_small.render(line, True, TEXT_COLOR), (x, y))
            y += 20
        y += 16
        text, color = FEEDBACK.get(self.puzzle_feedback, FEEDBACK["start"])
        fb = pygame.Rect(x - 5, y, PANEL_W - 30, 40)
        pygame.draw.rect(self.screen, (38, 37, 34), fb, border_radius=6)
        pygame.draw.rect(self.screen, color, fb, 2, border_radius=6)
        t = self.font_med.render(text, True, color)
        self.screen.blit(t, (fb.x + 10, fb.centery - t.get_height() // 2))
        y += 58
        prog = self.puzzle_progress
        total = len(self.puzzle_list())
        solved = len([i for i in prog["solved"] if i in {q.id for q in self.puzzle_list()}])
        stats = [
            f"Racha: {current_streak(prog, self.puzzle_today)} día(s)  ·  mejor: {prog['best_streak']}",
            f"Resueltos: {solved} de {total}",
        ]
        for line in stats:
            self.screen.blit(self.font_small.render(line, True, TEXT_DIM), (x, y))
            y += 20

        mx, my = self.mouse_pos()
        for label, _action, color, rect in self.puzzle_buttons():
            hovered = rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen, (45, 44, 41) if hovered else (35, 34, 31), rect, border_radius=6)
            pygame.draw.rect(self.screen, color if hovered else BORDER_COLOR, rect, 1, border_radius=6)
            lbl = self.font_small.render(label, True, TEXT_BRIGHT if hovered else TEXT_COLOR)
            self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2, rect.centery - lbl.get_height() // 2))

        credit = self.font_tiny.render(f"Puzzle {p.id} · base de Lichess (CC0)", True, TEXT_DIM)
        self.screen.blit(credit, (BOARD_X, BOARD_Y + BOARD_SIZE + 10))
        self.screen.blit(
            self.font_tiny.render("H pista · S solución · N otro · Esc menú", True, TEXT_DIM),
            (BOARD_X + BOARD_SIZE - 230, BOARD_Y + BOARD_SIZE + 10),
        )
        if self.pgn_saved_msg and (time.time() - self.pgn_saved_time) < 3:
            ts = self.font_small.render(self.pgn_saved_msg, True, BG_COLOR)
            pygame.draw.rect(self.screen, ACCENT, (x - 5, BOARD_Y - 34, ts.get_width() + 20, 26), border_radius=6)
            self.screen.blit(ts, (x + 5, BOARD_Y - 30))

    def _wrap(self, text, width):
        words, lines, cur = text.split(), [], ""
        for w in words:
            cand = f"{cur} {w}".strip()
            if self.font_small.size(cand)[0] <= width or not cur:
                cur = cand
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    # ── botón del menú principal (esquina superior derecha) ──
    def menu_puzzle_button(self):
        """Botón "Puzzle del día" del menú: (etiqueta, rect)."""
        return "Puzzle del día", pygame.Rect(WINDOW_W - 190, 20, 170, 34)

    def draw_menu_puzzle_button(self):
        label, rect = self.menu_puzzle_button()
        hovered = rect.collidepoint(*self.mouse_pos())
        pygame.draw.rect(self.screen, (45, 44, 41) if hovered else (35, 34, 31), rect, border_radius=6)
        pygame.draw.rect(self.screen, ACCENT if hovered else BORDER_COLOR, rect, 1, border_radius=6)
        icon = make_piece_sprite(chess.KNIGHT, chess.WHITE, 22)
        self.screen.blit(icon, (rect.x + 9, rect.centery - icon.get_height() // 2))
        lbl = self.font_small.render(label, True, TEXT_BRIGHT if hovered else TEXT_COLOR)
        self.screen.blit(lbl, (rect.x + 36, rect.centery - lbl.get_height() // 2))
