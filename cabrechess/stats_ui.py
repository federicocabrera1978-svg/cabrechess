# SPDX-License-Identifier: GPL-3.0-or-later
"""Pantalla "Estadísticas" (mixin de CabreChess).

La lógica (stats.json, Elo) vive en ``stats.py``; acá se registra la partida al
terminar, se dibuja la pantalla y se atienden clics y teclas."""

import chess
import pygame

from .clock import time_control_label
from .constants import (
    ACCENT,
    ACCENT2,
    BORDER_COLOR,
    DANGER,
    PANEL_COLOR,
    TEXT_BRIGHT,
    TEXT_COLOR,
    TEXT_DIM,
    WINDOW_H,
    WINDOW_W,
)
from .engine import ai_level
from .stats import (
    K_FACTOR,
    PROVISIONAL_GAMES,
    START_ELO,
    load_stats,
    player_result,
    record_game,
    reset_stats,
    summarize,
)

RESULT_TEXT = {"win": ("Victoria", ACCENT), "draw": ("Tablas", ACCENT2), "loss": ("Derrota", DANGER)}
COLOR_TEXT = {"white": "blancas", "black": "negras"}

STATS_X = 60
TABLE_W = 600
RECENT_X = 690
RECENT_W = WINDOW_W - RECENT_X - STATS_X
TABLE_TOP = 290
ROW_H = 34
# Columnas de la tabla por nivel: (título, x relativa, alineación)
TABLE_COLS = (
    ("Nivel", 12, "left"),
    ("Rival", 70, "left"),
    ("Elo IA", 250, "right"),
    ("Partidas", 345, "right"),
    ("V", 400, "right"),
    ("E", 450, "right"),
    ("D", 500, "right"),
    ("Puntaje", 585, "right"),
)


class StatsScreenMixin:
    """Requiere los atributos de CabreChess (screen, fuentes, confirm...)."""

    # ── registro automático ──
    def record_game_stats(self):
        """Anota la partida recién terminada contra la IA en stats.json. No
        cuenta 2 jugadores, análisis ni partidas cargadas desde PGN o la base."""
        if self.mode != "vsai" or self.loaded_game_id is not None:
            return None
        result = player_result(self.result, self.ai_color == chess.BLACK)
        if result is None:
            return None
        return record_game(
            result,
            self.ai_level,
            "white" if self.ai_color == chess.BLACK else "black",
            engine="stockfish" if self.uses_stockfish() else "cabrechess",
            time_control=time_control_label(self.time_selected, self.time_increment) if self.use_timer else "",
            termination=self.termination,
            variant="chess960" if self.board.chess960 else "standard",
        )

    # ── navegación ──
    def open_stats(self):
        self.reset_game()
        self.mode = "stats"
        self.confirm = None
        self.stats_summary = summarize(load_stats())

    def close_stats(self):
        self.confirm = None
        self.mode = "menu"

    def ask_reset_stats(self):
        played = self.stats_summary["totals"]["played"]
        if not played:
            self.toast("No hay estadísticas para borrar")
            return
        self.confirm = {
            "title": "¿Reiniciar estadísticas?",
            "subtitle": f"Se borran {played} partida{'s' if played != 1 else ''} y el Elo vuelve a {START_ELO}",
            "buttons": [("Borrar todo", self.confirm_reset_stats), ("Cancelar", self.close_confirm)],
        }

    def confirm_reset_stats(self):
        self.confirm = None
        if reset_stats():
            self.toast("Estadísticas reiniciadas")
        else:
            self.toast("No se pudo escribir stats.json")
        self.stats_summary = summarize(load_stats())

    def stats_buttons(self):
        """Botones de la pantalla: (etiqueta, acción, color, rect)."""
        y = WINDOW_H - 80
        return [
            ("Reiniciar estadísticas", "reset", DANGER, pygame.Rect(WINDOW_W // 2 - 240, y, 230, 44)),
            ("Volver al menú", "back", ACCENT, pygame.Rect(WINDOW_W // 2 + 10, y, 230, 44)),
        ]

    def handle_stats_click(self, pos):
        if self.confirm:
            self.handle_confirm_click(pos)
            return
        for _label, action, _color, rect in self.stats_buttons():
            if rect.collidepoint(pos):
                if action == "reset":
                    self.ask_reset_stats()
                else:
                    self.close_stats()
                return

    def handle_stats_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            if self.confirm:
                self.close_confirm()
            else:
                self.close_stats()

    # ── dibujo ──
    def draw_stats(self):
        s = getattr(self, "stats_summary", None) or summarize(load_stats())
        self.stats_summary = s
        title = self.font_title.render("Estadísticas", True, TEXT_BRIGHT)
        self.screen.blit(title, (WINDOW_W // 2 - title.get_width() // 2, 40))
        sub = self.font_tiny.render(
            "Partidas contra la IA  ·  se guardan solas en stats.json  ·  Esc para volver", True, TEXT_DIM
        )
        self.screen.blit(sub, (WINDOW_W // 2 - sub.get_width() // 2, 108))

        self._draw_stats_cards(s)
        self._draw_stats_table(s)
        self._draw_stats_recent(s)

        mx, my = self.mouse_pos()
        for label, _action, color, rect in self.stats_buttons():
            hovered = rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen, (45, 44, 41) if hovered else (35, 34, 31), rect, border_radius=8)
            pygame.draw.rect(self.screen, color if hovered else BORDER_COLOR, rect, 2, border_radius=8)
            lbl = self.font_med.render(label, True, TEXT_BRIGHT if hovered else TEXT_COLOR)
            self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2, rect.centery - lbl.get_height() // 2))

        if self.confirm:
            self.draw_confirm()

    def _draw_stats_cards(self, s):
        t = s["totals"]
        elo_sub = "provisional" if s["provisional"] else f"máximo {s['elo_peak']}"
        cards = [
            ("Partidas", str(t["played"]), TEXT_BRIGHT, ""),
            ("Victorias", str(t["win"]), ACCENT, ""),
            ("Empates", str(t["draw"]), ACCENT2, ""),
            ("Derrotas", str(t["loss"]), DANGER, ""),
            ("Puntaje", f"{t['score_pct']}%", TEXT_BRIGHT, ""),
            ("Elo estimado", str(s["elo"]), ACCENT, elo_sub),
        ]
        gap = 12
        w = (WINDOW_W - 2 * STATS_X - gap * (len(cards) - 1)) // len(cards)
        for i, (label, value, color, extra) in enumerate(cards):
            rect = pygame.Rect(STATS_X + i * (w + gap), 140, w, 92)
            pygame.draw.rect(self.screen, PANEL_COLOR, rect, border_radius=10)
            pygame.draw.rect(self.screen, color if i == len(cards) - 1 else BORDER_COLOR, rect, 1, border_radius=10)
            lbl = self.font_small.render(label, True, TEXT_DIM)
            self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2, rect.y + 10))
            val = self.font_large.render(value, True, color)
            self.screen.blit(val, (rect.centerx - val.get_width() // 2, rect.y + 34))
            if extra:
                ex = self.font_tiny.render(extra, True, TEXT_DIM)
                self.screen.blit(ex, (rect.centerx - ex.get_width() // 2, rect.bottom - 22))

    def _stats_rows(self, s):
        rows = []
        for lvl, r in s["by_level"].items():
            rows.append((str(lvl), ai_level(lvl)["name"], str(r["elo"]), r))
        if s["stockfish"]["played"]:
            rows.append(("SF", "Stockfish (todos)", "—", s["stockfish"]))
        if s.get("chess960", {}).get("played"):
            # Ya están sumadas arriba (por nivel); esta fila es solo el detalle
            rows.append(("960", "Chess960 (incluidas)", "—", s["chess960"]))
        return rows

    def _draw_stats_table(self, s):
        x, y = STATS_X, TABLE_TOP
        head = self.font_med.render("Por nivel de IA", True, TEXT_COLOR)
        self.screen.blit(head, (x, y - 34))
        rows = self._stats_rows(s)
        rect = pygame.Rect(x, y, TABLE_W, ROW_H * (len(rows) + 1) + 6)
        pygame.draw.rect(self.screen, PANEL_COLOR, rect, border_radius=8)
        pygame.draw.rect(self.screen, BORDER_COLOR, rect, 1, border_radius=8)
        self._table_line([c[0] for c in TABLE_COLS], y + 4, TEXT_DIM)
        pygame.draw.line(self.screen, BORDER_COLOR, (x + 8, y + ROW_H), (x + TABLE_W - 8, y + ROW_H))
        for i, (lvl, name, elo, r) in enumerate(rows):
            ry = y + ROW_H * (i + 1) + 4
            played = r["played"]
            color = TEXT_COLOR if played else TEXT_DIM
            pct = f"{r['score_pct']}%" if played else "—"
            self._table_line(
                [lvl, name, elo, str(played), str(r["win"]), str(r["draw"]), str(r["loss"]), pct], ry, color
            )
        note_y = rect.bottom + 10
        notes = [
            f"Elo estimado: fórmula Elo estándar con K = {K_FACTOR}, empezando en {START_ELO},",
            f"contra el Elo asignado a cada nivel. Provisional con menos de {PROVISIONAL_GAMES} partidas.",
        ]
        for j, text in enumerate(notes):
            n = self.font_tiny.render(text, True, TEXT_DIM)
            self.screen.blit(n, (x, note_y + j * 18))

    def _table_line(self, cells, y, color):
        for text, (_title, cx, align) in zip(cells, TABLE_COLS):
            t = self.font_small.render(text, True, color)
            tx = STATS_X + cx - (t.get_width() if align == "right" else 0)
            self.screen.blit(t, (tx, y + ROW_H // 2 - t.get_height() // 2))

    def _draw_stats_recent(self, s):
        x, y = RECENT_X, TABLE_TOP
        head = self.font_med.render("Últimas partidas", True, TEXT_COLOR)
        self.screen.blit(head, (x, y - 34))
        rect = pygame.Rect(x, y, RECENT_W, 5 * 52 + 10)
        pygame.draw.rect(self.screen, PANEL_COLOR, rect, border_radius=8)
        pygame.draw.rect(self.screen, BORDER_COLOR, rect, 1, border_radius=8)
        if not s["recent"]:
            t = self.font_small.render("Todavía no hay partidas.", True, TEXT_DIM)
            self.screen.blit(t, (x + 14, y + 16))
            t = self.font_tiny.render("Jugá contra la IA y aparecen acá.", True, TEXT_DIM)
            self.screen.blit(t, (x + 14, y + 42))
            return
        for i, g in enumerate(s["recent"]):
            gy = y + 8 + i * 52
            text, color = RESULT_TEXT[g["result"]]
            pygame.draw.rect(self.screen, color, (x + 10, gy + 6, 6, 36), border_radius=3)
            t = self.font_small.render(text, True, color)
            self.screen.blit(t, (x + 26, gy + 4))
            rival = f"Stockfish nivel {g['level']}" if g["engine"] == "stockfish" else f"IA nivel {g['level']}"
            detail = f"{rival}  ·  con {COLOR_TEXT[g['color']]}"
            if g["time_control"]:
                detail += f"  ·  {g['time_control']}"
            if g.get("variant") == "chess960":
                detail += "  ·  960"
            d = self.font_tiny.render(detail, True, TEXT_COLOR)
            self.screen.blit(d, (x + 26, gy + 26))
            date = g["date"][:16].replace("T", " ")
            ds = self.font_tiny.render(date, True, TEXT_DIM)
            self.screen.blit(ds, (x + RECENT_W - 12 - ds.get_width(), gy + 7))

    # ── botón del menú principal (esquina superior izquierda) ──
    def menu_stats_button(self):
        """Botón "Estadísticas" del menú: (etiqueta, rect)."""
        return "Estadísticas", pygame.Rect(20, 20, 170, 34)

    def draw_menu_stats_button(self):
        label, rect = self.menu_stats_button()
        hovered = rect.collidepoint(*self.mouse_pos())
        pygame.draw.rect(self.screen, (45, 44, 41) if hovered else (35, 34, 31), rect, border_radius=6)
        pygame.draw.rect(self.screen, ACCENT2 if hovered else BORDER_COLOR, rect, 1, border_radius=6)
        self.draw_icon("chart", (rect.x + 20, rect.centery), ACCENT2, size=18)
        lbl = self.font_small.render(label, True, TEXT_BRIGHT if hovered else TEXT_COLOR)
        self.screen.blit(lbl, (rect.x + 36, rect.centery - lbl.get_height() // 2))
