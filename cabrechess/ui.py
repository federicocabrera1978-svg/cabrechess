# SPDX-License-Identifier: GPL-3.0-or-later
"""Interfaz pygame: clase principal CabreChess."""
import math
import random
import sys
import threading
import time

import chess
import pygame

from ._version import __version__
from .clock import TIME_INCREMENT, TIME_OPTIONS, format_clock
from .constants import (
    ACCENT,
    ACCENT2,
    BG_COLOR,
    BOARD_SIZE,
    BOARD_X,
    BOARD_Y,
    BORDER_COLOR,
    DANGER,
    BOARD_THEMES,
    LAST_MOVE,
    DEFAULT_THEME,
    MENU_BTN_X,
    MENU_OPT_X,
    MENU_ROW_Y,
    MOVE_ACTIVE,
    PANEL_COLOR,
    PANEL_W,
    PANEL_X,
    PREMOVE_ALPHA,
    PREMOVE_SQ,
    SELECTED_SQ,
    SQUARE_SIZE,
    TEXT_BRIGHT,
    TEXT_COLOR,
    TEXT_DIM,
    WINDOW_H,
    WINDOW_W,
)
from .display import (
    clamp_window_size,
    compute_viewport,
    enable_windows_dpi_awareness,
    initial_window_size,
    window_to_logical,
)
from .analysis import Analyzer
from .database import GameDB
from .endings import (
    PGN_TERMINATION,
    ai_accepts_draw,
    color_name,
    detect_end,
    end_message,
    flag_end,
    resign_end,
)
from .engine import SimpleEngine
from .pgn import build_pgn, default_pgn_path, write_pgn
from .settings import load_settings, save_setting
from .sounds import LOW_TIME_SECONDS, SoundManager, sound_for_move
from .sprites import PIECE_NAMES, load_window_icon, make_piece_shadow, make_piece_sprite


def menu_version_text():
    """Texto de versión del pie del menú (sale de ``__version__``)."""
    return f"v{__version__} — Motor: Minimax Alpha-Beta"


class CabreChess:
    def __init__(self):
        enable_windows_dpi_awareness()   # antes de crear la ventana
        pygame.init()
        pygame.display.set_caption("CabreChess")
        # El ícono va antes de set_mode para que lo tome la ventana y la barra
        # de tareas (en Windows/Linux no se actualiza bien si se pone después).
        icon = load_window_icon()
        if icon is not None:
            pygame.display.set_icon(icon)
        # Ventana real redimensionable; el juego dibuja en self.screen, una
        # superficie lógica de tamaño fijo que present() escala con letterbox.
        start_size = initial_window_size(self.desktop_size())
        self.window = pygame.display.set_mode(start_size, pygame.RESIZABLE)
        self.screen = pygame.Surface((WINDOW_W, WINDOW_H))
        self.fullscreen = False
        self.windowed_size = start_size
        self.clock = pygame.time.Clock()

        # Fuentes
        self.load_fonts()

        # Estado del juego
        self.board = chess.Board()
        self.selected_sq = None
        self.legal_moves_from = []
        self.last_move = None
        self.flipped = False
        self.move_history = []        # lista de strings UCI
        self.move_history_san = []    # lista SAN
        self.history_scroll = 0
        self.promotion_pending = None
        self.promotion_sq = None
        self.game_over = False
        self.game_over_panel = False   # panel de fin de partida visible
        self._game_over_seen = False
        self.review_index = None       # None = posición actual; n = tras n jugadas
        self.game_over_msg = ""
        self.hover_sq = None
        self.dragging = False
        self.drag_piece = None
        self.drag_pos = (0, 0)
        self.drag_from = None

        # Modo de juego
        self.mode = "menu"   # menu / pvp / vsai / analysis
        self.ai_color = chess.BLACK
        self.player_color_choice = "white"   # white / black / random (vs IA)
        self.ai_thinking = False
        self.ai_think_start = 0
        self.ai_delay = 0.6
        self.engine = SimpleEngine()
        _cfg = load_settings()
        self.sound = SoundManager(enabled=_cfg.get("sound", True))
        self.board_theme = _cfg.get("board_theme", DEFAULT_THEME)
        self.silent = False             # True al reconstruir partidas (sin sonido)
        self.low_time_warned = set()    # colores ya avisados con reloj bajo
        self.analyzer = None            # análisis en segundo plano (lazy)
        self.db = None                  # partidas.db (lazy)
        self.result = "*"
        self.termination = ""
        self.final_times = None
        self.saved_game_id = None
        self.loaded_game_id = None
        self.confirm = None             # diálogo abierto (abandonar / tablas)
        self.draw_offer_ply = None      # jugada en la que se ofreció tablas
        self.loaded_names = None
        self.saved_games = []
        self.saved_sel = None
        self.saved_scroll = 0
        self.saved_confirm_delete = None
        self.ai_depth = 3
        self.ai_thread = None
        self.ai_move_ready = False
        self.ai_result_move = None
        self.ai_search_id = 0          # descarta resultados de búsquedas viejas
        # Protege ai_search_id / ai_result_move / ai_move_ready entre el hilo
        # de la IA y el loop principal
        self.ai_lock = threading.Lock()

        # Animación
        self.anim_move = None
        self.anim_start = 0
        self.anim_duration = 0.15
        self.anim_piece = None
        self.anim_from_pos = None
        self.anim_to_pos = None

        # Capturadas
        self.captured_white = []
        self.captured_black = []

        # Deshacer: una "foto" del estado extra (relojes, capturas, evaluación)
        # por cada jugada, para poder restaurarlo exacto con Ctrl+Z.
        self.undo_stack = []

        # Tiempos
        self.time_options = list(TIME_OPTIONS)    # 1/3/5/10 min en segundos
        self.time_selected = 180                   # 3 min por defecto
        self.time_increment = TIME_INCREMENT       # +3s por movimiento
        self.time_white = self.time_selected
        self.time_black = self.time_selected
        self.time_last = time.time()
        self.use_timer = True                      # siempre activo

        # Premove
        self.premove_from = None   # casilla origen del premove
        self.premove_to   = None   # casilla destino del premove
        self.premove_piece = None  # pieza del premove (para dibujarla)

        # Análisis — barra de evaluación
        self.eval_score = 0.0        # centipawns, positivo = blancas mejor
        self.eval_history = []       # evaluación por movimiento
        self.eval_update_needed = False

        # PGN metadata
        self.pgn_white = "Blancas"
        self.pgn_black = "Negras"
        self.pgn_saved_msg = ""
        self.pgn_saved_time = 0

        # Efectos
        self.particles = []
        self.check_flash = 0

        # Superficie tablero (cache)
        self.board_surf = pygame.Surface((BOARD_SIZE, BOARD_SIZE))
        self.render_static_board()

        # Overlay surfaces
        self.overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)

        print("CabreChess iniciado!")

    def load_fonts(self):
        # Usamos fuentes del sistema, priorizando las más bonitas
        candidates = ["DejaVu Sans", "Liberation Sans", "Ubuntu", "FreeSans", "Arial"]
        # SysFont no falla si la fuente no existe (cae en silencio a la
        # default), así que verificamos con match_font si está instalada.
        font_name = next((c for c in candidates if pygame.font.match_font(c)), None)

        self.font_tiny   = pygame.font.SysFont(font_name, 12)
        self.font_coord  = pygame.font.SysFont(font_name, 13, bold=True)
        self.font_small  = pygame.font.SysFont(font_name, 14)
        self.font_med    = pygame.font.SysFont(font_name, 18)
        self.font_large  = pygame.font.SysFont(font_name, 24, bold=True)
        self.font_xl     = pygame.font.SysFont(font_name, 36, bold=True)
        self.font_title  = pygame.font.SysFont(font_name, 52, bold=True)
        # Fuente para piezas Unicode: SysFont no garantiza que la fuente tenga
        # el glifo — si no la encuentra, Windows/SDL la reemplaza en silencio
        # por otra (p.ej. "DejaVu Sans" -> Arial Narrow) y el símbolo sale
        # como un rectángulo ("tofu"). Verificamos con freetype que el glifo
        # exista de verdad antes de aceptar la fuente.
        piece_font_path = self.find_piece_font_path()
        if piece_font_path:
            self.font_piece     = pygame.font.Font(piece_font_path, SQUARE_SIZE - 10)
            self.font_piece_sm  = pygame.font.Font(piece_font_path, 20)
            self.font_piece_xs  = pygame.font.Font(piece_font_path, 14)
        else:
            self.font_piece     = pygame.font.SysFont(font_name, SQUARE_SIZE - 10)
            self.font_piece_sm  = pygame.font.SysFont(font_name, 20)
            self.font_piece_xs  = pygame.font.SysFont(font_name, 14)

    def find_piece_font_path(self):
        """Busca una fuente del sistema que realmente contenga los glifos de
        piezas de ajedrez (♔♛♞...), comprobando el glifo con freetype en vez
        de confiar en el ancho renderizado (un glifo faltante también ocupa
        ancho: se dibuja como un rectángulo de reemplazo)."""
        import pygame.freetype
        pygame.freetype.init()
        candidates = ["Segoe UI Symbol", "DejaVu Sans", "Noto Sans Symbols",
                      "Noto Sans Symbols2", "Symbola", "Apple Symbols",
                      "FreeSans", "Arial Unicode MS"]
        for name in candidates:
            path = pygame.font.match_font(name)
            if not path:
                continue
            try:
                metrics = pygame.freetype.Font(path, 32).get_metrics('♔')
                if metrics and metrics[0] is not None:
                    return path
            except (OSError, pygame.error):
                continue
        return None

    # ─── ÍCONOS DIBUJADOS ───────────────────────────────────────────────────────
    def draw_icon(self, kind, center, color, size=20):
        """Dibuja un ícono con primitivas de pygame. No depende de la fuente,
        así que nunca sale como rectángulo vacío ("tofu") en ningún sistema."""
        cx, cy = center
        h = size // 2
        scr = self.screen
        if kind == "reset":      # flecha circular (arco con puntos: sin huecos)
            r = h - 3
            pts = [(cx + r * math.cos(math.radians(a)), cy - r * math.sin(math.radians(a)))
                   for a in range(70, 361, 6)]
            pygame.draw.lines(scr, color, False, pts, 3)
            for x, y in pts:
                pygame.draw.circle(scr, color, (int(x), int(y)), 1)
            # punta de flecha al inicio del arco (70°), apuntando en sentido horario
            ax, ay = pts[0]
            pygame.draw.polygon(scr, color, [(ax + 6, ay), (ax - 3, ay - 6), (ax - 3, ay + 6)])
        elif kind == "flip":     # dos flechas opuestas
            pygame.draw.line(scr, color, (cx - h, cy - 4), (cx + h - 4, cy - 4), 3)
            pygame.draw.polygon(scr, color, [(cx + h, cy - 4), (cx + h - 7, cy - 10), (cx + h - 7, cy + 2)])
            pygame.draw.line(scr, color, (cx - h + 4, cy + 5), (cx + h, cy + 5), 3)
            pygame.draw.polygon(scr, color, [(cx - h, cy + 5), (cx - h + 7, cy - 1), (cx - h + 7, cy + 11)])
        elif kind == "undo":     # flecha a la izquierda
            pygame.draw.line(scr, color, (cx - h + 6, cy), (cx + h, cy), 3)
            pygame.draw.polygon(scr, color, [(cx - h, cy), (cx - h + 8, cy - 7), (cx - h + 8, cy + 7)])
        elif kind == "save":     # disquete
            body = pygame.Rect(cx - h, cy - h, size, size)
            pygame.draw.rect(scr, color, body, border_radius=3)
            pygame.draw.rect(scr, PANEL_COLOR, (cx - h + 4, cy - h, size - 10, 7))
            pygame.draw.rect(scr, color, (cx + h - 9, cy - h + 1, 3, 4))
            pygame.draw.rect(scr, PANEL_COLOR, (cx - h + 3, cy + 1, size - 6, h - 3), border_radius=1)
        elif kind == "menu":     # hamburguesa
            for dy in (-6, 0, 6):
                pygame.draw.line(scr, color, (cx - h + 1, cy + dy), (cx + h - 1, cy + dy), 3)
        elif kind == "chart":    # mini gráfico de barras (análisis)
            base = cy + h
            for i, bh in enumerate((8, 14, 20)):
                pygame.draw.rect(scr, color, (cx - h + i * 7, base - bh, 5, bh), border_radius=1)
        elif kind == "clock":    # reloj (tiempo agotado)
            pygame.draw.circle(scr, color, (cx, cy), h, 3)
            pygame.draw.line(scr, color, (cx, cy), (cx, cy - h + 5), 3)
            pygame.draw.line(scr, color, (cx, cy), (cx + h - 6, cy), 3)
        elif kind == "flag":     # bandera blanca (abandonar)
            pygame.draw.line(scr, color, (cx - h + 3, cy - h), (cx - h + 3, cy + h), 3)
            pygame.draw.polygon(scr, color, [(cx - h + 4, cy - h), (cx + h, cy - h + size // 4),
                                             (cx - h + 4, cy - h + size // 2)])
        elif kind == "draw":     # tablas: ½
            font = self.font_xl if size >= 30 else self.font_med
            surf = font.render("½", True, color)
            scr.blit(surf, (cx - surf.get_width() // 2, cy - surf.get_height() // 2))
        elif kind == "mate":     # dama cburnett
            surf = make_piece_sprite(chess.QUEEN, chess.BLACK, size)
            scr.blit(surf, (cx - surf.get_width() // 2, cy - surf.get_height() // 2))

    # ─── RENDER ESTÁTICO ────────────────────────────────────────────────────────
    @property
    def theme_colors(self):
        """(clara, oscura) del tema de tablero actual."""
        _, light, dark = BOARD_THEMES.get(self.board_theme, BOARD_THEMES[DEFAULT_THEME])
        return light, dark

    def set_board_theme(self, key, save=True):
        if key not in BOARD_THEMES:
            return False
        self.board_theme = key
        self.render_static_board()
        if save:
            save_setting("board_theme", key)
        return True

    def cycle_board_theme(self):
        """Tecla T: pasa al siguiente tema y lo recuerda en settings.json."""
        keys = list(BOARD_THEMES)
        idx = keys.index(self.board_theme) if self.board_theme in keys else -1
        key = keys[(idx + 1) % len(keys)]
        self.set_board_theme(key)
        self.toast(f"Tablero: {BOARD_THEMES[key][0]}")
        return key

    def render_static_board(self):
        light_sq, dark_sq = self.theme_colors
        for rank in range(8):
            for file in range(8):
                color = light_sq if (rank + file) % 2 == 0 else dark_sq
                rect = pygame.Rect(file * SQUARE_SIZE, rank * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                pygame.draw.rect(self.board_surf, color, rect)

    def sq_to_pixel(self, sq):
        """Convierte un square de chess a posición en pantalla (esquina superior izq)."""
        file = chess.square_file(sq)
        rank = chess.square_rank(sq)
        if self.flipped:
            x = (7 - file) * SQUARE_SIZE + BOARD_X
            y = rank * SQUARE_SIZE + BOARD_Y
        else:
            x = file * SQUARE_SIZE + BOARD_X
            y = (7 - rank) * SQUARE_SIZE + BOARD_Y
        return (x, y)

    def pixel_to_sq(self, px, py):
        """Convierte coordenadas de pantalla a square."""
        bx = px - BOARD_X
        by = py - BOARD_Y
        if bx < 0 or by < 0 or bx >= BOARD_SIZE or by >= BOARD_SIZE:
            return None
        file = bx // SQUARE_SIZE
        rank = 7 - (by // SQUARE_SIZE)
        if self.flipped:
            file = 7 - file
            rank = 7 - rank
        if 0 <= file <= 7 and 0 <= rank <= 7:
            return chess.square(file, rank)
        return None

    def center_of_sq(self, sq):
        x, y = self.sq_to_pixel(sq)
        return (x + SQUARE_SIZE // 2, y + SQUARE_SIZE // 2)

    # ─── DIBUJO PRINCIPAL ───────────────────────────────────────────────────────
    def draw(self):
        self.screen.fill(BG_COLOR)

        if self.mode == "menu":
            self.draw_menu()
        elif self.mode == "saved":
            self.draw_saved_games()
        else:
            self.draw_game()

        self.present()

    # ─── VENTANA / ESCALADO ─────────────────────────────────────────────────────
    def viewport(self):
        surf = pygame.display.get_surface()
        size = surf.get_size() if surf else (WINDOW_W, WINDOW_H)
        return compute_viewport(*size)

    def to_logical(self, pos):
        return window_to_logical(pos, self.viewport())

    def mouse_pos(self):
        """Posición del mouse en coordenadas lógicas del juego."""
        return self.to_logical(pygame.mouse.get_pos())

    def present(self):
        """Escala la superficie lógica a la ventana (con barras negras)."""
        window = pygame.display.get_surface()
        scale, x, y, w, h = self.viewport()
        if (w, h) == (WINDOW_W, WINDOW_H) and (x, y) == (0, 0):
            window.blit(self.screen, (0, 0))
        else:
            window.fill((0, 0, 0))
            window.blit(pygame.transform.smoothscale(self.screen, (w, h)), (x, y))
        pygame.display.flip()

    @staticmethod
    def desktop_size():
        """Resolución del escritorio (monitor principal), o el tamaño lógico."""
        try:
            sizes = pygame.display.get_desktop_sizes()
        except (AttributeError, pygame.error):
            sizes = []
        return sizes[0] if sizes and sizes[0][0] > 0 else (WINDOW_W, WINDOW_H)

    def on_resize(self, w, h):
        """VIDEORESIZE / WINDOWSIZECHANGED (también al maximizar). En pygame 2
        la superficie de la ventana ya cambió de tamaño; solo forzamos el mínimo."""
        if self.fullscreen:
            return
        cw, ch = clamp_window_size(w, h)
        if (cw, ch) != (w, h):
            self.window = pygame.display.set_mode((cw, ch), pygame.RESIZABLE)
        self.windowed_size = (cw, ch)

    def toggle_fullscreen(self):
        if self.fullscreen:
            self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            self.fullscreen = False
        else:
            surf = pygame.display.get_surface()
            if surf:
                self.windowed_size = surf.get_size()
            self.window = pygame.display.set_mode(self.desktop_size(), pygame.FULLSCREEN)
            self.fullscreen = True

    def draw_menu(self):
        # Fondo con patrón de tablero sutil
        for rank in range(8):
            for file in range(8):
                color = (28, 27, 24) if (rank+file)%2==0 else (32, 31, 28)
                pygame.draw.rect(self.screen, color,
                    (file*137, rank*97, 137, 97))

        # Título
        title_surf = self.font_title.render("CabreChess", True, TEXT_BRIGHT)
        sub_surf = self.font_med.render("by Federico Cabrera", True, ACCENT)
        tx = WINDOW_W//2 - title_surf.get_width()//2
        self.screen.blit(title_surf, (tx, 90))
        self.screen.blit(sub_surf, (WINDOW_W//2 - sub_surf.get_width()//2, 155))

        # Pieza decorativa (cburnett)
        king_surf = make_piece_sprite(chess.KING, chess.BLACK, 64)
        self.screen.blit(king_surf, (WINDOW_W//2 - king_surf.get_width()//2, 185))

        # Botones
        mx, my = self.mouse_pos()
        for label, icon, _action, color, rect in self.menu_main_buttons():
            hovered = rect.collidepoint(mx, my)
            bg = (45, 44, 41) if hovered else (35, 34, 31)
            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            pygame.draw.rect(self.screen, color if hovered else BORDER_COLOR, rect, 2, border_radius=8)
            tc = TEXT_BRIGHT if hovered else TEXT_COLOR
            lbl = self.font_large.render(label, True, tc)
            # Ícono + texto centrados como bloque
            total_w = 28 + lbl.get_width()
            ix = rect.centerx - total_w // 2
            if icon.startswith("piece:"):
                # piece:W/K etc -> color + type short codes
                code = icon[6:]
                color = chess.WHITE if code[0] == "W" else chess.BLACK
                ptype = {"K": chess.KING, "Q": chess.QUEEN, "R": chess.ROOK,
                         "B": chess.BISHOP, "N": chess.KNIGHT, "P": chess.PAWN}[code[1]]
                g = make_piece_sprite(ptype, color, 22)
                self.screen.blit(g, (ix + 10 - g.get_width() // 2, rect.centery - g.get_height() // 2))
            else:
                self.draw_icon(icon, (ix + 10, rect.centery), tc, size=18)
            self.screen.blit(lbl, (ix + 28, rect.centery - lbl.get_height() // 2))

        # Opciones (dificultad, color, tiempo) — etiqueta en su propia columna
        for row_label, row_y, accent, options in self.menu_option_rows():
            lbl = self.font_small.render(row_label, True, TEXT_DIM)
            self.screen.blit(lbl, (MENU_OPT_X, row_y + 13 - lbl.get_height() // 2))
            for text, rect, selected, _cb in options:
                pygame.draw.rect(self.screen, accent if selected else (40, 40, 37), rect, border_radius=5)
                t = self.font_small.render(text, True, BG_COLOR if selected else TEXT_COLOR)
                self.screen.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))

        # Incremento info
        inc_surf = self.font_tiny.render(f"+{self.time_increment}s por movimiento", True, TEXT_DIM)
        self.screen.blit(inc_surf, (WINDOW_W//2 - inc_surf.get_width()//2, MENU_ROW_Y[-1] + 34))

    # Layout del menú: una sola fuente de verdad para dibujo y clics
    def menu_main_buttons(self):
        items = [
            ("Jugar contra IA",    "piece:BP", "vsai",     ACCENT),
            ("2 Jugadores (PvP)",  "piece:WN", "pvp",      ACCENT2),
            ("Análisis",           "chart",   "analysis", (150, 150, 150)),
            ("Partidas guardadas", "save",    "saved",    (200, 180, 80)),
        ]
        return [(label, icon, action, color,
                 pygame.Rect(WINDOW_W//2 - 160, 290 + i*62, 320, 50))
                for i, (label, icon, action, color) in enumerate(items)]

    def menu_option_rows(self):
        def row(y, specs, w, current):
            return [(text, pygame.Rect(MENU_BTN_X + i*(w + 6), y, w, 26), value == current, value)
                    for i, (text, value) in enumerate(specs)]
        return [
            ("Dificultad IA:", MENU_ROW_Y[0], ACCENT,
             row(MENU_ROW_Y[0], [("Fácil", 1), ("Normal", 3), ("Difícil", 5)], 84, self.ai_depth)),
            ("Color (vs IA):", MENU_ROW_Y[1], ACCENT,
             row(MENU_ROW_Y[1], [("Blancas", "white"), ("Negras", "black"), ("Azar", "random")],
                 84, self.player_color_choice)),
            ("Tiempo:", MENU_ROW_Y[2], ACCENT2,
             row(MENU_ROW_Y[2], [("1 min", 60), ("3 min", 180), ("5 min", 300), ("10 min", 600)],
                 62, self.time_selected)),
        ]

        # Versión
        v = self.font_tiny.render(menu_version_text(), True, TEXT_DIM)
        self.screen.blit(v, (WINDOW_W//2 - v.get_width()//2, WINDOW_H - 30))

    def draw_game(self):
        if self.review_index is None:
            self._draw_game()
            return
        # Modo revisión: dibujar la posición tras review_index jugadas
        live_board, live_last = self.board, self.last_move
        self.board = self.review_board()
        self.last_move = self.board.peek() if self.board.move_stack else None
        try:
            self._draw_game()
        finally:
            self.board, self.last_move = live_board, live_last

    # ─── ANÁLISIS (mejor jugada en segundo plano) ───────────────────────────────
    def analysis_active(self):
        """Análisis visible: en modo análisis, o revisando una partida terminada."""
        return self.mode == "analysis" or (self.game_over and not self.game_over_panel)

    def displayed_board(self):
        return self.review_board() if self.review_index is not None else self.board

    def get_analyzer(self):
        if self.analyzer is None:
            from .settings import load_settings
            cfg = load_settings()
            self.analyzer = Analyzer(depth=cfg["analysis_depth"],
                                     stockfish_path=cfg["stockfish_path"])
        return self.analyzer

    def request_analysis(self):
        if self.mode in ("analysis", "pvp", "vsai") and self.analysis_active():
            self.get_analyzer().request(self.displayed_board())

    def analysis_result(self):
        """Resultado para la posición que se está dibujando (self.board ya es
        la posición revisada dentro de draw_game)."""
        if self.analyzer is None or not self.analysis_active():
            return None
        return self.analyzer.result(self.board)

    def draw_best_move_arrow(self):
        res = self.analysis_result()
        if res is None or res.move is None:
            return
        start = pygame.Vector2(self.center_of_sq(res.move.from_square))
        end = pygame.Vector2(self.center_of_sq(res.move.to_square))
        if (end - start).length() < 1:
            return
        direction = (end - start).normalize()
        normal = pygame.Vector2(-direction.y, direction.x)
        head = SQUARE_SIZE * 0.38
        tip = end - direction * (SQUARE_SIZE * 0.12)
        base = tip - direction * head
        overlay = pygame.Surface((BOARD_SIZE, BOARD_SIZE), pygame.SRCALPHA)
        off = pygame.Vector2(BOARD_X, BOARD_Y)
        color = (21, 120, 27, 170)          # verde flecha Lichess
        pygame.draw.line(overlay, color, start - off, base - off, max(6, SQUARE_SIZE // 7))
        pygame.draw.polygon(overlay, color, [tip - off, base + normal * head * 0.6 - off,
                                             base - normal * head * 0.6 - off])
        self.screen.blit(overlay, (BOARD_X, BOARD_Y))

    def draw_analysis_line(self, y):
        res = self.analysis_result()
        if res is None:
            text, color = "Analizando…", TEXT_DIM
        elif res.move is None:
            text, color = "Sin jugadas (partida terminada)", TEXT_DIM
        else:
            text = f"Mejor: {res.san}   {res.score_text()}   ({res.engine}, d{res.depth})"
            color = ACCENT
        surf = self.font_small.render(text, True, color)
        pygame.draw.rect(self.screen, (38, 37, 34), (PANEL_X + 5, y, PANEL_W - 20, 22), border_radius=4)
        self.screen.blit(surf, (PANEL_X + 10, y + 11 - surf.get_height() // 2))

    def review_board(self):
        board = self.board.root()
        for move in self.board.move_stack[:self.review_index]:
            board.push(move)
        return board

    def _draw_game(self):
        # Barra de evaluación (solo en modo análisis)
        # Barra de evaluación: en modo análisis, y en la revisión de cualquier
        # partida terminada (evalúa la posición que se está mirando)
        if self.mode == "analysis" or self.game_over:
            self.draw_eval_bar()

        # Panel superior: el bando que está arriba del tablero
        top_color = chess.WHITE if self.flipped else chess.BLACK
        self.draw_player_panel(top_color, BOARD_X, BOARD_Y - 30)

        # Tablero base
        board_rect = pygame.Rect(BOARD_X, BOARD_Y, BOARD_SIZE, BOARD_SIZE)
        pygame.draw.rect(self.screen, BORDER_COLOR, board_rect.inflate(4, 4), border_radius=3)
        self.screen.blit(self.board_surf, (BOARD_X, BOARD_Y))

        # Highlights
        self.draw_highlights()

        # Piezas (excepto la que se arrastra)
        self.draw_pieces()

        # Coordenadas (después de las piezas para que no queden tapadas)
        self.draw_coordinates()

        # Mejor jugada del análisis (flecha)
        if self.analysis_active():
            self.draw_best_move_arrow()

        # Animación de movimiento
        if self.anim_move:
            self.draw_animation()

        # Pieza arrastrada
        if self.dragging and self.drag_piece:
            self.draw_dragged_piece()

        # Menú de promoción
        if self.promotion_pending:
            self.draw_promotion_menu()

        # Panel derecho
        self.draw_side_panel()

        # Panel inferior
        self.draw_player_panel(not top_color, BOARD_X, BOARD_Y + BOARD_SIZE + 10)

        # Diálogo de abandonar / tablas
        if self.confirm and not self.game_over:
            self.draw_confirm()

        # Overlay fin de juego
        if self.game_over and self.game_over_panel:
            self.draw_game_over()
        elif self.game_over:
            # Partida terminada y panel cerrado: SIEMPRE se ve la barra de
            # revisión (antes solo aparecía tras retroceder una jugada)
            self.draw_review_bar()

        # Thinking indicator
        if self.ai_thinking:
            self.draw_thinking()

        # Partículas
        self.draw_particles()

    def draw_eval_bar(self):
        """Barra vertical de evaluación estilo Lichess, a la izquierda del tablero."""
        bar_x = BOARD_X - 22
        bar_y = BOARD_Y
        bar_w = 14
        bar_h = BOARD_SIZE

        # Fondo
        pygame.draw.rect(self.screen, (40, 39, 36),
            pygame.Rect(bar_x, bar_y, bar_w, bar_h), border_radius=4)

        # Convertir score a proporción (clampeado a ±6 peones = extremo)
        res = self.analysis_result()
        if res is not None:
            score = res.score
        else:
            score = self.engine.evaluate(self.board) if self.game_over else self.eval_score
        MAX_SCORE = 600  # centipawns
        clamped = max(-MAX_SCORE, min(MAX_SCORE, score))
        # Proporción blancas (0=todo negro, 1=todo blancas)
        white_ratio = 0.5 + (clamped / (MAX_SCORE * 2))
        white_h = int(bar_h * white_ratio)
        black_h = bar_h - white_h

        # Bloque negro (arriba)
        if black_h > 0:
            pygame.draw.rect(self.screen, (30, 29, 26),
                pygame.Rect(bar_x, bar_y, bar_w, black_h), border_radius=4)
        # Bloque blanco (abajo)
        if white_h > 0:
            pygame.draw.rect(self.screen, (220, 215, 200),
                pygame.Rect(bar_x, bar_y + black_h, bar_w, white_h), border_radius=4)

        # Línea central
        pygame.draw.line(self.screen, (80, 79, 76),
            (bar_x, bar_y + bar_h//2), (bar_x + bar_w, bar_y + bar_h//2), 1)

        # Texto de evaluación
        if abs(score) >= 9900:
            txt = "M" + ("+" if score > 0 else "-")
        elif abs(score) >= 100:
            txt = f"{score/100:+.1f}"
        else:
            txt = f"{score/100:+.2f}".rstrip('0').rstrip('.')
        # Texto debajo de la barra, alineado a la derecha del borde del
        # tablero para que no se pise con el panel del jugador inferior.
        color = TEXT_BRIGHT if score >= 0 else (180, 180, 180)
        ev_surf = self.font_tiny.render(txt, True, color)
        self.screen.blit(ev_surf, (bar_x + bar_w - ev_surf.get_width(),
                                    bar_y + bar_h + 3))

    def draw_player_panel(self, color, x, y):
        name = "Jugador Negro" if color == chess.BLACK else "Jugador Blanco"
        if self.mode == "vsai":
            if color == self.ai_color:
                name = "CabreChess AI"
        if self.loaded_names:                     # partida abierta desde la base
            name = self.loaded_names[0 if color == chess.WHITE else 1]
        sym_surf = make_piece_sprite(chess.KING, color, 22)
        name_surf = self.font_small.render(name, True, TEXT_COLOR)
        turn_indicator = color == self.board.turn and not self.game_over
        if turn_indicator:
            dot_x = x + 8
            dot_y = y + 12
            pygame.draw.circle(self.screen, ACCENT, (dot_x, dot_y), 5)
        self.screen.blit(sym_surf, (x + 18, y))
        self.screen.blit(name_surf, (x + 42, y + 3))

        # Tiempo - reloj estilo Lichess
        if self.use_timer:
            t = self.time_white if color == chess.WHITE else self.time_black
            time_str = format_clock(t)
            is_active = color == self.board.turn and not self.game_over
            is_low = t < 30
            # Fondo del reloj
            ts = self.font_large.render(time_str, True, TEXT_BRIGHT)
            clock_w = max(ts.get_width() + 20, 90)
            clock_x = BOARD_X + BOARD_SIZE - clock_w - 2
            clock_y = y - 4
            clock_rect = pygame.Rect(clock_x, clock_y, clock_w, 30)
            if is_low and is_active:
                # Parpadeo rojo cuando queda poco tiempo
                alpha = int(abs(math.sin(time.time() * 4)) * 120 + 80)
                bg_surf = pygame.Surface((clock_w, 30), pygame.SRCALPHA)
                bg_surf.fill((*DANGER, alpha))
                self.screen.blit(bg_surf, (clock_x, clock_y))
                pygame.draw.rect(self.screen, DANGER, clock_rect, 2, border_radius=5)
            elif is_active:
                pygame.draw.rect(self.screen, (55, 54, 50), clock_rect, border_radius=5)
                pygame.draw.rect(self.screen, ACCENT, clock_rect, 2, border_radius=5)
            else:
                pygame.draw.rect(self.screen, (38, 37, 34), clock_rect, border_radius=5)
            tc = DANGER if is_low else (TEXT_BRIGHT if is_active else TEXT_DIM)
            ts = self.font_large.render(time_str, True, tc)
            self.screen.blit(ts, (clock_x + clock_w//2 - ts.get_width()//2, clock_y + 4))

        # Piezas capturadas
        self.draw_captured(color, x + 200, y + 2)

    def draw_captured(self, color, x, y):
        caps = self.captured_black if color == chess.BLACK else self.captured_white
        size = 18
        for i, p in enumerate(caps[:16]):
            spr = make_piece_sprite(p.piece_type, p.color, size)
            self.screen.blit(spr, (x + i * 14, y - 2))

    def draw_highlights(self):
        # Último movimiento
        if self.last_move:
            for sq in [self.last_move.from_square, self.last_move.to_square]:
                x, y = self.sq_to_pixel(sq)
                lm_surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                lm_surf.fill((*LAST_MOVE[:3], 120))
                self.screen.blit(lm_surf, (x, y))

        # Casilla en jaque
        if self.board.is_check():
            king_sq = self.board.king(self.board.turn)
            if king_sq is not None:
                x, y = self.sq_to_pixel(king_sq)
                ck_surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                # Gradiente radial simulado
                for r in range(SQUARE_SIZE//2, 0, -4):
                    alpha = int(160 * (1 - r/(SQUARE_SIZE//2)))
                    pygame.draw.circle(ck_surf, (220, 50, 50, alpha),
                        (SQUARE_SIZE//2, SQUARE_SIZE//2), r)
                self.screen.blit(ck_surf, (x, y))

        # Seleccionado
        if self.selected_sq is not None:
            x, y = self.sq_to_pixel(self.selected_sq)
            sel_surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            sel_surf.fill((*SELECTED_SQ, 180))
            self.screen.blit(sel_surf, (x, y))

        # Movimientos legales
        for move in self.legal_moves_from:
            sq = move.to_square
            x, y = self.sq_to_pixel(sq)
            dot_surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            if self.board.piece_at(sq):
                # Captura: ring
                pygame.draw.circle(dot_surf, (0, 0, 0, 100),
                    (SQUARE_SIZE//2, SQUARE_SIZE//2), SQUARE_SIZE//2 - 2, 6)
            else:
                # Punto
                pygame.draw.circle(dot_surf, (0, 0, 0, 90),
                    (SQUARE_SIZE//2, SQUARE_SIZE//2), SQUARE_SIZE//7)
            self.screen.blit(dot_surf, (x, y))

        # Premove highlight (naranja-rojo, sobre todo lo demás)
        if self.premove_from is not None:
            for sq in [self.premove_from, self.premove_to]:
                if sq is not None:
                    x, y = self.sq_to_pixel(sq)
                    pm_surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                    pm_surf.fill((*PREMOVE_SQ, PREMOVE_ALPHA))
                    self.screen.blit(pm_surf, (x, y))

        # Hover
        if self.hover_sq is not None and not self.dragging:
            x, y = self.sq_to_pixel(self.hover_sq)
            hov_surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            hov_surf.fill((255, 255, 255, 18))
            self.screen.blit(hov_surf, (x, y))

    def draw_coordinates(self):
        files = 'abcdefgh'
        ranks = '12345678'
        light_sq, dark_sq = self.theme_colors
        for i in range(8):
            # Archivos (abajo)
            fi = i if not self.flipped else 7-i
            # Fila inferior: columna par = casilla oscura -> letra clara
            f_surf = self.font_coord.render(files[fi], True,
                light_sq if i%2==0 else dark_sq)
            self.screen.blit(f_surf, (BOARD_X + (i+1)*SQUARE_SIZE - f_surf.get_width() - 3,
                                      BOARD_Y + BOARD_SIZE - f_surf.get_height() - 1))
            # Rangos (izquierda)
            ri = 7-i if not self.flipped else i
            r_surf = self.font_coord.render(ranks[ri], True,
                dark_sq if (7-i)%2==1 else light_sq)
            self.screen.blit(r_surf, (BOARD_X + 2, BOARD_Y + i*SQUARE_SIZE + 2))

    def draw_pieces(self):
        for sq in chess.SQUARES:
            if sq == self.drag_from and self.dragging:
                continue
            # Ocultar pieza origen del premove (se muestra semi-transparente)
            if sq == self.premove_from and self.premove_to is not None:
                continue
            if self.anim_move and sq == self.anim_move.to_square:
                continue
            piece = self.board.piece_at(sq)
            if piece:
                self.draw_piece_at_sq(piece, sq)

        # Dibujar pieza premove en destino (fantasma)
        if self.premove_from is not None and self.premove_to is not None and self.premove_piece:
            self.draw_piece_premove_ghost()

    def draw_piece_premove_ghost(self):
        """Dibuja la pieza del premove en el destino con transparencia."""
        sq = self.premove_to
        piece = self.premove_piece
        x, y = self.sq_to_pixel(sq)
        ghost = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
        p_surf = make_piece_sprite(piece.piece_type, piece.color, SQUARE_SIZE).copy()
        p_surf.fill((255, 255, 255, 150), special_flags=pygame.BLEND_RGBA_MULT)
        ghost.blit(p_surf, (0, 0))
        self.screen.blit(ghost, (x, y))

    def draw_piece_at_sq(self, piece, sq):
        x, y = self.sq_to_pixel(sq)
        self.screen.blit(make_piece_shadow(piece.piece_type, SQUARE_SIZE), (x + 2, y + 2))
        self.screen.blit(make_piece_sprite(piece.piece_type, piece.color, SQUARE_SIZE), (x, y))

    def draw_dragged_piece(self):
        x = self.drag_pos[0] - SQUARE_SIZE // 2
        y = self.drag_pos[1] - SQUARE_SIZE // 2
        self.screen.blit(make_piece_shadow(self.drag_piece.piece_type, SQUARE_SIZE, 80),
                         (x + 4, y + 4))
        self.screen.blit(make_piece_sprite(self.drag_piece.piece_type, self.drag_piece.color,
                                           SQUARE_SIZE), (x, y))

    def draw_animation(self):
        t = (time.time() - self.anim_start) / self.anim_duration
        if t >= 1:
            self.anim_move = None
            return
        # Interpolación suave
        t = t * t * (3 - 2 * t)  # smoothstep
        if self.anim_from_pos and self.anim_to_pos and self.anim_piece:
            x = self.anim_from_pos[0] + (self.anim_to_pos[0] - self.anim_from_pos[0]) * t
            y = self.anim_from_pos[1] + (self.anim_to_pos[1] - self.anim_from_pos[1]) * t
            self.screen.blit(
                make_piece_sprite(self.anim_piece.piece_type, self.anim_piece.color,
                                  SQUARE_SIZE),
                (int(x), int(y)),
            )

    def draw_promotion_menu(self):
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        pieces = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        pw = 200
        ph = 60
        px = WINDOW_W//2 - pw//2
        py = WINDOW_H//2 - (len(pieces)*ph + 40)//2

        # Panel
        panel_rect = pygame.Rect(px - 20, py - 20, pw + 40, len(pieces)*ph + 80)
        pygame.draw.rect(self.screen, PANEL_COLOR, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, ACCENT, panel_rect, 2, border_radius=12)

        title = self.font_large.render("Promoción", True, TEXT_BRIGHT)
        self.screen.blit(title, (WINDOW_W//2 - title.get_width()//2, py - 5))

        color = self.board.turn
        mx, my = self.mouse_pos()
        for i, pt in enumerate(pieces):
            bx, by = px, py + 30 + i*ph
            brect = pygame.Rect(bx, by, pw, ph - 8)
            hovered = brect.collidepoint(mx, my)
            bg = ACCENT if hovered else (50, 49, 46)
            pygame.draw.rect(self.screen, bg, brect, border_radius=8)
            tc = BG_COLOR if hovered else TEXT_BRIGHT
            p_surf = make_piece_sprite(pt, color, 36)
            n_surf = self.font_med.render(PIECE_NAMES[pt], True, tc)
            self.screen.blit(p_surf, (bx + 10, by + ph // 2 - 18 - 2))
            self.screen.blit(n_surf, (bx + 55, by + ph // 2 - n_surf.get_height() // 2 - 4))

    def draw_side_panel(self):
        # Panel de movimientos
        panel_rect = pygame.Rect(PANEL_X, BOARD_Y, PANEL_W - 10, BOARD_SIZE)
        pygame.draw.rect(self.screen, PANEL_COLOR, panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, BORDER_COLOR, panel_rect, 1, border_radius=8)

        # Título panel: nombre de la apertura si se reconoce (en revisión,
        # la de la posición revisada), si no "Movimientos"
        mode_w = self.font_tiny.size(self.mode_label())[0]
        opening = self.opening_text(PANEL_W - 40 - mode_w)
        if opening:
            title = self.font_tiny.render(opening, True, TEXT_COLOR)
            self.screen.blit(title, (PANEL_X + 10, BOARD_Y + 12))
        else:
            title = self.font_small.render("Movimientos", True, TEXT_DIM)
            self.screen.blit(title, (PANEL_X + 10, BOARD_Y + 10))

        # Movimientos en pares
        top = 30
        if self.analysis_active():
            self.draw_analysis_line(BOARD_Y + 30)
            top = 54
        list_h = BOARD_SIZE - (140 if self.game_over and not self.game_over_panel else 80) - (top - 30)
        clip_rect = pygame.Rect(PANEL_X + 5, BOARD_Y + top, PANEL_W - 20, list_h)
        self.screen.set_clip(clip_rect)

        row_h = 24
        visible_rows = (clip_rect.height) // row_h
        total_rows = (len(self.move_history_san) + 1) // 2 + 1

        # Auto-scroll para que se vea la jugada activa (la última, o la
        # que se está revisando)
        if total_rows > visible_rows:
            active_row = max(0, self.active_ply()) // 2
            self.history_scroll = max(0, min(total_rows - visible_rows,
                                             active_row - visible_rows + 2))
        else:
            self.history_scroll = 0

        for i in range(0, len(self.move_history_san), 2):
            row = i // 2
            y = BOARD_Y + top + 2 + (row - self.history_scroll) * row_h
            if y < BOARD_Y + top - 2 or y > BOARD_Y + BOARD_SIZE - 30:
                continue

            # Número
            num_s = self.font_small.render(f"{row+1}.", True, TEXT_DIM)
            self.screen.blit(num_s, (PANEL_X + 8, y))

            # Jugada blanca
            if i < len(self.move_history_san):
                is_last = i == self.active_ply()
                bg = MOVE_ACTIVE if is_last else None
                if bg:
                    pygame.draw.rect(self.screen, bg,
                        (PANEL_X + 35, y-2, 60, row_h-2), border_radius=3)
                ms = self.font_small.render(self.move_history_san[i], True,
                    TEXT_BRIGHT if is_last else TEXT_COLOR)
                self.screen.blit(ms, (PANEL_X + 38, y))

            # Jugada negra
            if i+1 < len(self.move_history_san):
                is_last = i+1 == self.active_ply()
                bg = MOVE_ACTIVE if is_last else None
                if bg:
                    pygame.draw.rect(self.screen, bg,
                        (PANEL_X + 95, y-2, 60, row_h-2), border_radius=3)
                ms = self.font_small.render(self.move_history_san[i+1], True,
                    TEXT_BRIGHT if is_last else TEXT_COLOR)
                self.screen.blit(ms, (PANEL_X + 98, y))

        self.screen.set_clip(None)

        # Botones inferiores del panel
        mx, my = self.mouse_pos()
        for icon, color, _action, brect in self.panel_buttons():
            hovered = brect.collidepoint(mx, my)
            bg = (50, 49, 46) if hovered else (38, 37, 34)
            pygame.draw.rect(self.screen, bg, brect, border_radius=6)
            self.draw_icon(icon, brect.center, TEXT_BRIGHT if hovered else color, size=18)

        # Turno actual (cuadradito dibujado en vez de ⬜/⬛)
        if not self.game_over:
            is_white = self.board.turn == chess.WHITE
            ty = BOARD_Y + BOARD_SIZE - 60
            t_surf = self.font_small.render("Turno:", True, TEXT_COLOR)
            self.screen.blit(t_surf, (PANEL_X + 10, ty))
            sw_x = PANEL_X + 16 + t_surf.get_width()
            sw = pygame.Rect(sw_x, ty + t_surf.get_height()//2 - 6, 12, 12)
            pygame.draw.rect(self.screen, (235, 235, 235) if is_white else (25, 25, 25), sw, border_radius=2)
            pygame.draw.rect(self.screen, TEXT_DIM, sw, 1, border_radius=2)
            n_surf = self.font_small.render("Blancas" if is_white else "Negras", True, TEXT_COLOR)
            self.screen.blit(n_surf, (sw_x + 18, ty))

        # Modo
        m_surf = self.font_tiny.render(self.mode_label(), True, TEXT_DIM)
        self.screen.blit(m_surf, (PANEL_X + PANEL_W - m_surf.get_width() - 12, BOARD_Y + 10))

        # Toast "PGN guardado"
        if self.pgn_saved_msg and (time.time() - self.pgn_saved_time) < 3:
            toast_surf = self.font_small.render(self.pgn_saved_msg, True, BG_COLOR)
            tw = toast_surf.get_width() + 20
            tx = PANEL_X + (PANEL_W - tw) // 2
            ty = BOARD_Y + BOARD_SIZE - 80
            pygame.draw.rect(self.screen, ACCENT, pygame.Rect(tx, ty, tw, 26), border_radius=6)
            self.screen.blit(toast_surf, (tx + 10, ty + 4))

        # Mini gráfico de evaluación (solo análisis)
        if self.mode == "analysis" and len(self.eval_history) > 1:
            self.draw_eval_graph()

    def panel_buttons(self):
        """Botones de abajo del panel: (ícono, color, acción, rect). Una sola
        definición para dibujar y para los clicks. Abandonar y ofrecer tablas
        solo aparecen en una partida en curso (vs IA o 2 jugadores)."""
        specs = [
            ("reset", ACCENT, self.reset_game),
            ("flip",  ACCENT2, self.flip_board),
            ("undo",  TEXT_COLOR, self.undo_move),
        ]
        if self.mode in ("vsai", "pvp") and not self.game_over:
            specs += [
                ("draw", TEXT_COLOR, self.offer_draw),
                ("flag", TEXT_COLOR, self.ask_resign),
            ]
        specs += [
            ("save",  (200, 180, 80), self.save_pgn),
            ("menu",  TEXT_COLOR, self.go_menu),
        ]
        btn_y = BOARD_Y + BOARD_SIZE - 42
        bw = (PANEL_W - 20) // len(specs)
        return [(icon, color, action, pygame.Rect(PANEL_X + 5 + i * bw, btn_y, bw - 4, 34))
                for i, (icon, color, action) in enumerate(specs)]

    # ─── ABANDONAR Y TABLAS ─────────────────────────────────────────────────────
    CONFIRM_PANEL = (440, 170)

    def human_color(self):
        """Bando que usa los botones: en vs IA el jugador; en 2 jugadores,
        el que tiene el turno."""
        if self.mode == "vsai":
            return not self.ai_color
        return self.board.turn

    def ask_resign(self):
        if self.game_over or self.mode not in ("vsai", "pvp"):
            return
        who = color_name(self.human_color()).capitalize()
        self.confirm = {
            "title": "¿Abandonar la partida?",
            "subtitle": f"{who} pierden la partida",
            "buttons": [("Abandonar", self.resign), ("Cancelar", self.close_confirm)],
        }

    def resign(self):
        self.confirm = None
        if not self.game_over:
            self.end_game(*resign_end(self.human_color()))

    def can_offer_draw(self):
        """Una oferta por jugada: si la rechazan, hay que mover para volver
        a ofrecer (como en Lichess)."""
        return (not self.game_over and self.mode in ("vsai", "pvp")
                and self.draw_offer_ply != len(self.board.move_stack))

    def offer_draw(self):
        if self.game_over or self.mode not in ("vsai", "pvp"):
            return
        if not self.can_offer_draw():
            self.toast("Ya ofreciste tablas: mové antes de volver a ofrecer")
            return
        self.draw_offer_ply = len(self.board.move_stack)
        offerer = self.human_color()
        if self.mode == "vsai":
            ev = self.engine.evaluate(self.board)
            if ai_accepts_draw(ev, self.ai_color, self.board.fullmove_number):
                self.end_game("agreement", "1/2-1/2")
            else:
                self.toast("La IA rechaza las tablas")
            return
        # 2 jugadores: responde el rival
        self.confirm = {
            "title": f"{color_name(offerer).capitalize()} ofrecen tablas",
            "subtitle": f"¿Aceptan {color_name(not offerer)}?",
            "buttons": [("Aceptar", self.accept_draw), ("Rechazar", self.decline_draw)],
        }

    def accept_draw(self):
        self.confirm = None
        if not self.game_over:
            self.end_game("agreement", "1/2-1/2")

    def decline_draw(self):
        self.confirm = None
        self.toast("Tablas rechazadas")

    def close_confirm(self):
        self.confirm = None

    def confirm_buttons(self):
        pw, ph = self.CONFIRM_PANEL
        py = WINDOW_H // 2 - ph // 2
        out = []
        for i, (label, action) in enumerate(self.confirm["buttons"]):
            rect = pygame.Rect(WINDOW_W // 2 - 205 + i * 210, py + ph - 64, 200, 44)
            out.append((label, action, rect))
        return out

    def draw_confirm(self):
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))
        pw, ph = self.CONFIRM_PANEL
        rect = pygame.Rect(WINDOW_W // 2 - pw // 2, WINDOW_H // 2 - ph // 2, pw, ph)
        pygame.draw.rect(self.screen, PANEL_COLOR, rect, border_radius=14)
        pygame.draw.rect(self.screen, ACCENT2, rect, 2, border_radius=14)
        title = self.font_large.render(self.confirm["title"], True, TEXT_BRIGHT)
        self.screen.blit(title, (WINDOW_W // 2 - title.get_width() // 2, rect.y + 22))
        sub = self.font_med.render(self.confirm["subtitle"], True, TEXT_COLOR)
        self.screen.blit(sub, (WINDOW_W // 2 - sub.get_width() // 2, rect.y + 62))
        mx, my = self.mouse_pos()
        for i, (label, _action, brect) in enumerate(self.confirm_buttons()):
            hov = brect.collidepoint(mx, my)
            c = ACCENT if i == 0 else ACCENT2
            pygame.draw.rect(self.screen, c if hov else (50, 49, 46), brect, border_radius=8)
            ls = self.font_med.render(label, True, BG_COLOR if hov else TEXT_COLOR)
            self.screen.blit(ls, (brect.centerx - ls.get_width() // 2, brect.y + 12))

    def handle_confirm_click(self, pos):
        for _label, action, rect in self.confirm_buttons():
            if rect.collidepoint(pos):
                action()
                return True
        return False

    def mode_label(self):
        mode_names = {"pvp": "PvP", "vsai": f"vs IA (d{self.ai_depth})", "analysis": "Análisis"}
        return mode_names.get(self.mode, "")

    def opening_text(self, max_w):
        """Apertura de la posición mostrada ("B20 · Defensa Siciliana"),
        recortada con "…" para que entre en max_w píxeles. "" si no hay."""
        from .openings import opening_label
        text = opening_label(self.board)
        if not text or self.font_tiny.size(text)[0] <= max_w:
            return text
        while text and self.font_tiny.size(text + "…")[0] > max_w:
            text = text[:-1]
        return text.rstrip() + "…"

    GAME_OVER_PANEL = (560, 300)

    def game_over_buttons(self):
        """Botones del panel de fin de partida: (etiqueta, acción, rect)."""
        pw, ph = self.GAME_OVER_PANEL
        py = WINDOW_H//2 - ph//2
        specs = [("Guardar PGN", self.save_pgn), ("Revisar / Analizar", self.start_review),
                 ("Nueva partida", self.reset_game), ("Cerrar", self.close_game_over_panel)]
        out = []
        for i, (label, action) in enumerate(specs):
            col, row = i % 2, i // 2
            rect = pygame.Rect(WINDOW_W//2 - 205 + col*210, py + 160 + row*54, 200, 44)
            out.append((label, action, rect))
        return out

    def draw_game_over(self):
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        pw, ph = self.GAME_OVER_PANEL
        px = WINDOW_W//2 - pw//2
        py = WINDOW_H//2 - ph//2
        panel_rect = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(self.screen, PANEL_COLOR, panel_rect, border_radius=14)
        pygame.draw.rect(self.screen, ACCENT, panel_rect, 2, border_radius=14)

        # Icono
        lines = self.game_over_msg.split('\n')
        icon = lines[0] if lines else "draw"
        self.draw_icon(icon, (WINDOW_W//2, py + 48), ACCENT, size=40)

        if len(lines) > 1:
            # Cartel grande; si no entra, una fuente más chica
            for font in (self.font_xl, self.font_large, self.font_med):
                msg_surf = font.render(lines[1], True, TEXT_BRIGHT)
                if msg_surf.get_width() <= pw - 30:
                    break
            self.screen.blit(msg_surf, (WINDOW_W//2 - msg_surf.get_width()//2, py + 74))
        if len(lines) > 2:
            sub_surf = self.font_med.render(lines[2], True, TEXT_COLOR)
            self.screen.blit(sub_surf, (WINDOW_W//2 - sub_surf.get_width()//2, py + 115))

        mx, my = self.mouse_pos()
        for i, (label, _action, brect) in enumerate(self.game_over_buttons()):
            hov = brect.collidepoint(mx, my)
            c = ACCENT if i == 2 else ACCENT2
            pygame.draw.rect(self.screen, c if hov else (50, 49, 46), brect, border_radius=8)
            ls = self.font_med.render(label, True, BG_COLOR if hov else TEXT_COLOR)
            self.screen.blit(ls, (brect.centerx - ls.get_width()//2, brect.y + 12))

        hint = self.font_tiny.render("Esc: cerrar y ver el tablero", True, TEXT_DIM)
        self.screen.blit(hint, (WINDOW_W//2 - hint.get_width()//2, py + ph - 22))

    # ─── REVISIÓN DE LA PARTIDA TERMINADA ───────────────────────────────────────
    def review_buttons(self):
        """Barra de navegación (fin de partida, panel cerrado): (id, rect)."""
        y = BOARD_Y + BOARD_SIZE - 88
        ids = ["first", "prev", "next", "last", "result"]
        widths = [40, 40, 40, 40, 110]
        out, x = [], PANEL_X + 8
        for bid, w in zip(ids, widths):
            out.append((bid, pygame.Rect(x, y, w, 32)))
            x += w + 6
        return out

    def draw_review_bar(self):
        labels = {"first": "|<", "prev": "<", "next": ">", "last": ">|", "result": "Resultado"}
        mx, my = self.mouse_pos()
        for bid, rect in self.review_buttons():
            hov = rect.collidepoint(mx, my)
            pygame.draw.rect(self.screen, (50, 49, 46) if hov else (38, 37, 34), rect, border_radius=6)
            ls = self.font_small.render(labels[bid], True, TEXT_BRIGHT if hov else TEXT_COLOR)
            self.screen.blit(ls, (rect.centerx - ls.get_width()//2, rect.centery - ls.get_height()//2))
        n = len(self.move_history_san)   # self.board puede ser la posición revisada
        cur = n if self.review_index is None else self.review_index
        info = self.font_tiny.render(f"Jugada {cur}/{n}  (\u2190 \u2192 Inicio Fin)", True, TEXT_DIM)
        self.screen.blit(info, (PANEL_X + 10, BOARD_Y + BOARD_SIZE - 104))

    def active_ply(self):
        """Índice (0-based) de la jugada resaltada en la lista."""
        n = len(self.move_history_san)
        return (n if self.review_index is None else self.review_index) - 1

    def review_step(self, delta=None, to=None):
        n = len(self.board.move_stack)
        cur = n if self.review_index is None else self.review_index
        new = to if to is not None else cur + delta
        new = max(0, min(n, new))
        self.review_index = None if new == n else new

    def start_review(self):
        self.game_over_panel = False
        self.review_index = None   # arranca en la posición final

    def close_game_over_panel(self):
        self.game_over_panel = False

    def sync_game_over_panel(self):
        """Muestra el panel una sola vez cuando termina la partida."""
        if self.game_over and not self._game_over_seen:
            self._game_over_seen = True
            self.game_over_panel = True
            self.game_over_time = time.time()
            self.selected_sq = None
            self.legal_moves_from = []
            self.dragging = False
            self.drag_piece = None
            self.autosave_game()

    # ─── BASE DE DATOS DE PARTIDAS ──────────────────────────────────────────────
    def get_db(self):
        if self.db is None:
            try:
                self.db = GameDB()
            except (OSError, Exception) as e:   # noqa: BLE001 - sqlite3.Error y similares
                self.toast(f"No se pudo abrir la base de partidas: {e}")
                return None
        return self.db

    def time_control(self):
        if not self.use_timer:
            return "-"
        return f"{int(self.time_selected)}+{int(self.time_increment)}"

    def player_names(self):
        white_name, black_name = self.pgn_white, self.pgn_black
        if self.mode == "vsai":
            if self.ai_color == chess.BLACK:
                black_name = "CabreChess AI"
            else:
                white_name = "CabreChess AI"
        return white_name, black_name

    def autosave_game(self):
        """Guarda la partida terminada en partidas.db (una sola vez). No guarda
        el modo análisis ni partidas abiertas desde la base."""
        if (self.mode not in ("pvp", "vsai") or self.loaded_game_id is not None
                or self.saved_game_id is not None):
            return None
        db = self.get_db()
        if db is None:
            return None
        from .openings import opening_for_board
        opening = opening_for_board(self.board) or ("", "")
        white, black = self.player_names()
        pgn_text, _ = self.build_pgn()
        try:
            self.saved_game_id = db.add_game(
                mode=self.mode, white=white, black=black, result=self.result,
                termination=self.termination, eco=opening[0], opening=opening[1],
                time_control=self.time_control(), num_moves=len(self.board.move_stack),
                pgn=pgn_text)
        except Exception as e:  # noqa: BLE001 - disco lleno, base bloqueada...
            self.toast(f"No se pudo guardar en el historial: {e}")
            return None
        return self.saved_game_id

    def clear_game_over_ui(self):
        self.game_over_panel = False
        self._game_over_seen = False
        self.review_index = None

    def draw_thinking(self):
        elapsed = time.time() - self.ai_think_start
        dots = "." * (int(elapsed * 2) % 4)
        txt = self.font_med.render(f"IA pensando{dots}", True, ACCENT)
        bx, by = BOARD_X + BOARD_SIZE//2 - 80, BOARD_Y + BOARD_SIZE + 50
        pygame.draw.rect(self.screen, PANEL_COLOR,
            pygame.Rect(bx-10, by-5, txt.get_width()+20, txt.get_height()+10), border_radius=5)
        self.screen.blit(txt, (bx, by))

    def draw_particles(self):
        now = time.time()
        alive = []
        for p in self.particles:
            age = now - p['start']
            if age < p['life']:
                alpha = int(255 * (1 - age/p['life']))
                surf = pygame.Surface((p['size']*2, p['size']*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*p['color'], alpha), (p['size'], p['size']), p['size'])
                self.screen.blit(surf, (int(p['x'] - p['size']), int(p['y'] - p['size'])))
                p['x'] += p['vx']
                p['y'] += p['vy']
                p['vy'] += 0.2
                alive.append(p)
        self.particles = alive

    # ─── LÓGICA DEL JUEGO ──────────────────────────────────────────────────────
    def spawn_particles(self, sq, color=(138, 196, 33)):
        x, y = self.center_of_sq(sq)
        for _ in range(18):
            angle = random.uniform(0, math.pi*2)
            speed = random.uniform(2, 7)
            self.particles.append({
                'x': x, 'y': y,
                'vx': math.cos(angle)*speed,
                'vy': math.sin(angle)*speed - 3,
                'color': color,
                'size': random.randint(3, 8),
                'life': random.uniform(0.4, 0.9),
                'start': time.time(),
            })

    def handle_square_click(self, sq):
        if self.game_over or self.promotion_pending or self.ai_thinking:
            return
        if self.mode == "vsai" and self.board.turn == self.ai_color:
            return

        piece = self.board.piece_at(sq)

        if self.selected_sq is None:
            if piece and piece.color == self.board.turn:
                self.selected_sq = sq
                self.legal_moves_from = [m for m in self.board.legal_moves
                                          if m.from_square == sq]
        else:
            move = self.find_move(self.selected_sq, sq)
            if move:
                self.attempt_move(move)
            elif piece and piece.color == self.board.turn:
                self.selected_sq = sq
                self.legal_moves_from = [m for m in self.board.legal_moves
                                          if m.from_square == sq]
            else:
                self.selected_sq = None
                self.legal_moves_from = []

    def find_move(self, from_sq, to_sq):
        for move in self.board.legal_moves:
            if move.from_square == from_sq and move.to_square == to_sq:
                if move.promotion:
                    # Siempre promovemos a reina por defecto (o mostramos menú)
                    return move  # retornamos el primero (puede haber varios por promo)
                return move
        return None

    def attempt_move(self, move):
        # ¿Requiere promoción?
        piece = self.board.piece_at(move.from_square)
        if (piece and piece.piece_type == chess.PAWN and
                chess.square_rank(move.to_square) in (0, 7)):
            # Múltiples opciones de promoción
            promos = [m for m in self.board.legal_moves
                      if m.from_square == move.from_square and m.to_square == move.to_square
                      and m.promotion]
            if promos:
                self.promotion_pending = promos
                self.promotion_sq = move.to_square
                self.selected_sq = None
                self.legal_moves_from = []
                return

        self.execute_move(move)

    def snapshot_state(self):
        """Foto del estado que python-chess no guarda en el tablero."""
        return {
            "time_white": self.time_white,
            "time_black": self.time_black,
            "captured_white": list(self.captured_white),
            "captured_black": list(self.captured_black),
            "eval_score": self.eval_score,
            "eval_history_len": len(self.eval_history),
        }

    def restore_state(self, snap):
        self.time_white = snap["time_white"]
        self.time_black = snap["time_black"]
        self.captured_white = list(snap["captured_white"])
        self.captured_black = list(snap["captured_black"])
        self.eval_score = snap["eval_score"]
        del self.eval_history[snap["eval_history_len"]:]

    def execute_move(self, move):
        self.undo_stack.append(self.snapshot_state())
        # Guardar pieza para animación
        piece = self.board.piece_at(move.from_square)
        captured = self.board.piece_at(move.to_square)
        if captured:
            if captured.color == chess.WHITE:
                self.captured_white.append(captured)
            else:
                self.captured_black.append(captured)

        # Iniciar animación
        self.anim_piece = piece
        self.anim_from_pos = self.sq_to_pixel(move.from_square)
        self.anim_to_pos = self.sq_to_pixel(move.to_square)
        self.anim_move = move
        self.anim_start = time.time()

        san = self.board.san(move)
        mover_color = self.board.turn   # color ANTES de push
        board_before = self.board.copy(stack=False)
        self.board.push(move)
        if not self.silent:
            self.sound.play(sound_for_move(board_before, move, self.board))
        self.last_move = move
        self.move_history.append(move.uci())
        self.move_history_san.append(san)

        # Incremento Fischer: se suma en TODAS las jugadas (también la
        # primera) y sin tope, como en Lichess/FIDE.
        self._last_mover = mover_color

        self.selected_sq = None
        self.legal_moves_from = []

        # Partículas en captura
        if captured:
            self.spawn_particles(move.to_square, (220, 100, 50))
        elif self.board.is_check():
            king_sq = self.board.king(self.board.turn)
            if king_sq is not None:     # a1 es la casilla 0
                self.spawn_particles(king_sq, (220, 50, 50))

        # Verificar fin
        self.check_game_over()

        # Incremento Fischer después de cada jugada (también la primera), pero
        # NO en la jugada que termina la partida: los relojes quedan congelados.
        if self.use_timer and not self.game_over:
            if mover_color == chess.WHITE:
                self.time_white += self.time_increment
            else:
                self.time_black += self.time_increment

        # Actualizar evaluación en modo análisis
        if self.mode == "analysis":
            self.update_eval()
            self.eval_history.append(self.eval_score)

        # Turno IA
        if (self.mode == "vsai" and self.board.turn == self.ai_color
                and not self.game_over):
            self.maybe_start_ai()
        elif not self.game_over:
            # Si hay premove registrado y ahora es turno del jugador, ejecutarlo
            self.try_execute_premove()

    def check_game_over(self):
        end = detect_end(self.board)
        if end:
            self.end_game(*end)
            if end[0] == "checkmate":
                self.spawn_particles(self.board.king(self.board.turn), ACCENT)

    def end_game(self, termination, result):
        """ÚNICO punto donde termina una partida: congela relojes y resultado,
        corta la IA y deja el estado listo para el panel (que se muestra y
        autoguarda la partida en sync_game_over_panel)."""
        if self.game_over:
            return
        self.game_over = True
        self.confirm = None
        self.termination = termination
        self.result = result
        self.game_over_msg = end_message(termination, result)
        self.final_times = (self.time_white, self.time_black)
        if termination not in ("checkmate", "stalemate") and not self.silent:
            # mate/ahogado ya sonaron con la jugada; acá tiempo, tablas, etc.
            self.sound.play("end")
        self.time_last = time.time()
        self.cancel_ai_search()
        self.clear_premove()

    def start_ai_search(self):
        """Lanza el cálculo del movimiento de la IA en un hilo aparte
        para no bloquear el loop principal (dibujo/eventos) durante la búsqueda."""
        board_copy = self.board.copy()
        depth = self.ai_depth
        with self.ai_lock:
            self.ai_move_ready = False
            self.ai_result_move = None
            self.ai_search_id += 1
            search_id = self.ai_search_id

        def worker():
            move = self.engine.get_best_move(board_copy, depth=depth)
            with self.ai_lock:
                # Si la partida se reinició/deshizo mientras pensaba, descartar
                if search_id != self.ai_search_id:
                    return
                self.ai_result_move = move
                self.ai_move_ready = True

        self.ai_thread = threading.Thread(target=worker, daemon=True)
        self.ai_thread.start()

    def maybe_start_ai(self):
        """Si es vs IA y le toca a la IA (p.ej. el jugador eligió negras),
        lanza la búsqueda."""
        if (self.mode == "vsai" and not self.game_over and not self.ai_thinking
                and self.board.turn == self.ai_color):
            self.ai_thinking = True
            self.ai_think_start = time.time()
            self.start_ai_search()

    def cancel_ai_search(self):
        """Invalida cualquier búsqueda en curso: su resultado se descarta."""
        with self.ai_lock:
            self.ai_search_id += 1
            self.ai_move_ready = False
            self.ai_result_move = None
        self.ai_thinking = False
        self.ai_thread = None

    def ai_move(self):
        with self.ai_lock:
            move = self.ai_result_move
            self.ai_move_ready = False
            self.ai_result_move = None
        self.ai_thread = None
        self.ai_thinking = False
        if self.game_over:      # p.ej. a la IA se le cayó la bandera
            return
        if move and move in self.board.legal_moves:
            self.execute_move(move)
        # Ejecutar premove si hay uno registrado
        if not self.game_over:
            self.try_execute_premove()

    def reset_game(self):
        self.board = chess.Board()
        self.selected_sq = None
        self.legal_moves_from = []
        self.last_move = None
        self.move_history = []
        self.move_history_san = []
        self.history_scroll = 0
        self.promotion_pending = None
        self.game_over = False
        self.game_over_msg = ""
        self.cancel_ai_search()
        self.captured_white = []
        self.captured_black = []
        self.undo_stack = []
        self.particles = []
        self.anim_move = None
        self.dragging = False
        self.drag_piece = None
        self.clear_premove()
        self.eval_score = 0.0
        self.eval_history = []
        self.pgn_saved_msg = ""
        self.pgn_saved_time = 0
        self.clear_game_over_ui()
        self.result = "*"
        self.termination = ""
        self.final_times = None
        self.saved_game_id = None
        self.loaded_game_id = None
        self.confirm = None             # diálogo abierto (abandonar / tablas)
        self.draw_offer_ply = None      # jugada en la que se ofreció tablas
        self.loaded_names = None
        self.time_white = self.time_selected
        self.time_black = self.time_selected
        self.time_last = time.time()
        self.low_time_warned = set()
        self.maybe_start_ai()

    def undo_move(self):
        """Deshace la última jugada y restaura todo el estado: relojes,
        piezas capturadas, evaluación, historial y premoves.
        En vs IA vuelve hasta que le toque al jugador (normalmente 2 jugadas).
        Si la IA está pensando, cancela la búsqueda y deshace la jugada
        del jugador.
        Con la partida terminada NO deshace nada: el resultado y los relojes
        quedan congelados y el botón solo retrocede en la revisión."""
        if self.game_over:
            self.game_over_panel = False
            self.review_step(-1)
            return
        if not self.board.move_stack:
            return
        # Cancelar una búsqueda en curso: su resultado se descarta
        self.cancel_ai_search()
        self.confirm = None

        self._undo_one()
        if self.mode == "vsai":
            while self.board.move_stack and self.board.turn == self.ai_color:
                self._undo_one()

        self.selected_sq = None
        self.legal_moves_from = []
        self.last_move = self.board.peek() if self.board.move_stack else None
        self.clear_premove()
        self.promotion_pending = None
        self.dragging = False
        self.drag_piece = None
        self.anim_move = None
        self.particles = []
        self.game_over = False
        self.game_over_msg = ""
        self.clear_game_over_ui()
        self.time_last = time.time()
        if self.mode == "analysis":
            self.update_eval()
        self.maybe_start_ai()   # si quedó el turno de la IA (jugando con negras)

    def _undo_one(self):
        self.board.pop()
        if self.move_history:
            self.move_history.pop()
        if self.move_history_san:
            self.move_history_san.pop()
        if self.undo_stack:
            self.restore_state(self.undo_stack.pop())

    def clear_premove(self):
        self.premove_from = None
        self.premove_to   = None
        self.premove_piece = None

    def try_execute_premove(self):
        """Intenta ejecutar el premove guardado. Si ya no es válido, lo descarta."""
        if self.premove_from is None or self.premove_to is None:
            return
        # Buscar el movimiento en los legales del nuevo estado
        move = None
        for m in self.board.legal_moves:
            if m.from_square == self.premove_from and m.to_square == self.premove_to:
                move = m
                break
        self.clear_premove()
        if move:
            self.attempt_move(move)

    def draw_eval_graph(self):
        """Mini gráfico de evaluación a lo largo de la partida."""
        gx = PANEL_X + 5
        gy = BOARD_Y + BOARD_SIZE - 110
        gw = PANEL_W - 20
        gh = 50

        # Fondo
        pygame.draw.rect(self.screen, (35, 34, 31), pygame.Rect(gx, gy, gw, gh), border_radius=4)
        pygame.draw.rect(self.screen, BORDER_COLOR, pygame.Rect(gx, gy, gw, gh), 1, border_radius=4)

        # Línea central (eval = 0)
        mid_y = gy + gh // 2
        pygame.draw.line(self.screen, (60, 59, 56), (gx+2, mid_y), (gx+gw-2, mid_y), 1)

        history = self.eval_history
        n = len(history)
        if n < 2:
            return

        MAX_E = 800
        pts_white, pts_black = [], []
        for i, e in enumerate(history):
            x = gx + 2 + int(i / (n - 1) * (gw - 4))
            clamped = max(-MAX_E, min(MAX_E, e))
            # Positivo = blancas arriba (hacia arriba en pantalla = menor y)
            y = mid_y - int((clamped / MAX_E) * (gh // 2 - 2))
            if clamped >= 0:
                pts_white.append((x, y))
                pts_black.append((x, mid_y))
            else:
                pts_white.append((x, mid_y))
                pts_black.append((x, y))

        # Rellenar área blanca (arriba de la línea central)
        if len(pts_white) >= 2:
            poly = [(gx+2, mid_y)] + pts_white + [(pts_white[-1][0], mid_y)]
            pygame.draw.polygon(self.screen, (200, 195, 180), poly)
        # Rellenar área negra (abajo)
        if len(pts_black) >= 2:
            poly = [(gx+2, mid_y)] + pts_black + [(pts_black[-1][0], mid_y)]
            pygame.draw.polygon(self.screen, (50, 49, 46), poly)

        # Línea de evaluación
        pts_line = []
        for i, e in enumerate(history):
            x = gx + 2 + int(i / (n - 1) * (gw - 4))
            clamped = max(-MAX_E, min(MAX_E, e))
            y = mid_y - int((clamped / MAX_E) * (gh // 2 - 2))
            pts_line.append((x, y))
        if len(pts_line) >= 2:
            pygame.draw.lines(self.screen, ACCENT, False, pts_line, 1)

        lbl = self.font_tiny.render("Evaluación", True, TEXT_DIM)
        self.screen.blit(lbl, (gx + 2, gy - 12))

    def save_pgn(self):
        """Guarda la partida en PGN. Usa el diálogo de archivo de tkinter y, si
        no está disponible, guarda en la carpeta por defecto (~/Documents/CabreChess)."""
        if not self.move_history_san:
            self.toast("No hay movimientos para guardar.")
            return None
        pgn_text, date_str = self.build_pgn()
        return self.save_pgn_text(pgn_text, date_str)

    def save_pgn_text(self, pgn_text, date_str):
        filename = self.ask_pgn_filename(date_str)
        if filename == "":          # el usuario canceló el diálogo
            return None
        if filename is None:        # sin tkinter / sin display: ruta por defecto
            filename = default_pgn_path()
        try:
            path = write_pgn(pgn_text, filename)
        except OSError as e:
            self.toast(f"No se pudo guardar: {e.strerror or e}")
            return None
        self.toast(f"Guardado: {path.parent.name}/{path.name}")
        return path

    def toggle_sound(self):
        on = self.sound.toggle()
        save_setting("sound", on)
        self.toast("Sonido activado" if on else "Sonido silenciado")
        return on

    def check_low_time(self):
        """Un aviso por color cuando su reloj baja de LOW_TIME_SECONDS
        (solo si la partida tiene más tiempo que eso)."""
        if not self.use_timer or self.game_over:
            return
        for color, left in ((chess.WHITE, self.time_white), (chess.BLACK, self.time_black)):
            if (color not in self.low_time_warned and 0 < left <= LOW_TIME_SECONDS
                    and self.board.turn == color):
                self.low_time_warned.add(color)
                if not (self.mode == "vsai" and color == self.ai_color):
                    self.sound.play("low_time")

    def toast(self, msg):
        self.pgn_saved_msg = msg
        self.pgn_saved_time = time.time()

    def ask_pgn_filename(self, date_str):
        """Diálogo "Guardar como". Devuelve la ruta elegida, "" si se canceló,
        o None si tkinter no está disponible."""
        try:
            import tkinter
            import tkinter.filedialog
        except ImportError:
            return None
        if self.fullscreen:         # el diálogo no se ve encima de pantalla completa
            self.toggle_fullscreen()
        try:
            root = tkinter.Tk()
            root.withdraw()
            root.lift()
            filename = tkinter.filedialog.asksaveasfilename(
                defaultextension=".pgn",
                filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")],
                initialfile=f"CabreChess_{date_str.replace('.','')}.pgn",
                title="Guardar partida PGN",
            )
            root.destroy()
        except tkinter.TclError:
            return None
        return filename or ""

    def build_pgn(self):
        """Arma el texto PGN de la partida actual. Devuelve (pgn_text, date_str)."""
        white_name, black_name = self.player_names()
        extra = {}
        if self.game_over:
            extra["result"] = self.result
            extra["termination"] = PGN_TERMINATION.get(self.termination, "normal")
        return build_pgn(self.board, self.move_history_san, self.mode,
                         white_name, black_name, time_control=self.time_control(), **extra)

    def update_eval(self):
        """Calcula evaluación estática para la posición actual."""
        if self.mode != "analysis":
            return
        # evaluate() ya devuelve centipawns desde el punto de vista de blancas
        self.eval_score = self.engine.evaluate(self.board)

    def flip_board(self):
        self.flipped = not self.flipped

    def go_menu(self):
        self.mode = "menu"
        self.reset_game()

    # ─── PARTIDAS GUARDADAS ─────────────────────────────────────────────────────
    SAVED_ROWS = 14
    SAVED_ROW_H = 34
    SAVED_TOP = 130
    SAVED_X, SAVED_W = 70, WINDOW_W - 140
    MODE_NAMES = {"pvp": "2 jugadores", "vsai": "vs IA", "analysis": "Análisis"}

    def open_saved_games(self):
        self.reset_game()
        self.mode = "saved"
        self.saved_sel = None
        self.saved_scroll = 0
        self.saved_confirm_delete = None
        self.refresh_saved_games()

    def refresh_saved_games(self):
        db = self.get_db()
        self.saved_games = db.list_games() if db else []
        if self.saved_sel is not None and self.saved_sel >= len(self.saved_games):
            self.saved_sel = len(self.saved_games) - 1 if self.saved_games else None

    def selected_saved_game(self):
        if self.saved_sel is None or not (0 <= self.saved_sel < len(self.saved_games)):
            return None
        return self.saved_games[self.saved_sel]

    def saved_buttons(self):
        specs = [("Abrir en análisis", "open"), ("Exportar PGN", "export"),
                 ("Borrar", "delete"), ("Volver", "back")]
        w, gap = 200, 14
        x0 = WINDOW_W // 2 - (len(specs) * w + (len(specs) - 1) * gap) // 2
        y = self.SAVED_TOP + self.SAVED_ROWS * self.SAVED_ROW_H + 30
        return [(label, bid, pygame.Rect(x0 + i * (w + gap), y, w, 44))
                for i, (label, bid) in enumerate(specs)]

    def saved_row_rect(self, visible_i):
        return pygame.Rect(self.SAVED_X, self.SAVED_TOP + visible_i * self.SAVED_ROW_H,
                           self.SAVED_W, self.SAVED_ROW_H - 4)

    @staticmethod
    def _result_label(game):
        from .endings import end_title
        return end_title(game["termination"], game["result"])

    def draw_saved_games(self):
        title = self.font_xl.render("Partidas guardadas", True, TEXT_BRIGHT)
        self.screen.blit(title, (WINDOW_W // 2 - title.get_width() // 2, 30))
        cols = [("Fecha", 10), ("Modo", 175), ("Resultado", 300), ("Apertura", 640)]
        for name, dx in cols:
            h = self.font_small.render(name, True, TEXT_DIM)
            self.screen.blit(h, (self.SAVED_X + dx, self.SAVED_TOP - 26))
        if not self.saved_games:
            msg = self.font_med.render("Todavía no hay partidas. Las partidas terminadas se guardan solas.",
                                       True, TEXT_COLOR)
            self.screen.blit(msg, (WINDOW_W // 2 - msg.get_width() // 2, self.SAVED_TOP + 60))
        mx, my = self.mouse_pos()
        visible = self.saved_games[self.saved_scroll:self.saved_scroll + self.SAVED_ROWS]
        for i, g in enumerate(visible):
            idx = self.saved_scroll + i
            rect = self.saved_row_rect(i)
            sel = idx == self.saved_sel
            bg = MOVE_ACTIVE if sel else ((45, 44, 41) if rect.collidepoint(mx, my) else (35, 34, 31))
            pygame.draw.rect(self.screen, bg, rect, border_radius=5)
            if sel:
                pygame.draw.rect(self.screen, ACCENT, rect, 2, border_radius=5)
            date = g["played_at"].replace("T", " ")[:16]
            opening = f'{g["eco"]} {g["opening"]}'.strip() or "—"
            values = [date, self.MODE_NAMES.get(g["mode"], g["mode"]),
                      self._result_label(g), opening]
            for (_, dx), val in zip(cols, values):
                t = self.font_small.render(val, True, TEXT_BRIGHT if sel else TEXT_COLOR)
                max_w = (cols[cols.index((_, dx)) + 1][1] - dx - 10) if dx != cols[-1][1] else rect.w - dx - 10
                if t.get_width() > max_w:
                    while val and self.font_small.size(val + "…")[0] > max_w:
                        val = val[:-1]
                    t = self.font_small.render(val + "…", True, TEXT_BRIGHT if sel else TEXT_COLOR)
                self.screen.blit(t, (rect.x + dx, rect.centery - t.get_height() // 2))
        if len(self.saved_games) > self.SAVED_ROWS:
            info = self.font_tiny.render(
                f"{self.saved_scroll + 1}-{self.saved_scroll + len(visible)} de {len(self.saved_games)}"
                "  (rueda del mouse / flechas)", True, TEXT_DIM)
            self.screen.blit(info, (self.SAVED_X, self.SAVED_TOP + self.SAVED_ROWS * self.SAVED_ROW_H + 4))
        has_sel = self.selected_saved_game() is not None
        for label, bid, rect in self.saved_buttons():
            enabled = has_sel or bid == "back"
            if bid == "delete" and self.saved_confirm_delete is not None:
                label = "¿Borrar? Click de nuevo"
            hov = enabled and rect.collidepoint(mx, my)
            c = DANGER if bid == "delete" else ACCENT
            pygame.draw.rect(self.screen, c if hov else (50, 49, 46), rect, border_radius=8)
            ls = self.font_small.render(label, True, BG_COLOR if hov else (TEXT_COLOR if enabled else TEXT_DIM))
            self.screen.blit(ls, (rect.centerx - ls.get_width() // 2, rect.centery - ls.get_height() // 2))
        if self.pgn_saved_msg and (time.time() - self.pgn_saved_time) < 3:
            t = self.font_small.render(self.pgn_saved_msg, True, BG_COLOR)
            box = pygame.Rect(0, 0, t.get_width() + 24, 30)
            box.center = (WINDOW_W // 2, WINDOW_H - 30)
            pygame.draw.rect(self.screen, ACCENT, box, border_radius=6)
            self.screen.blit(t, (box.x + 12, box.centery - t.get_height() // 2))

    def handle_saved_click(self, pos):
        for i in range(min(self.SAVED_ROWS, len(self.saved_games) - self.saved_scroll)):
            if self.saved_row_rect(i).collidepoint(pos):
                idx = self.saved_scroll + i
                if idx == self.saved_sel and time.time() - getattr(self, "_saved_click_t", 0) < 0.4:
                    self.load_saved_game(self.saved_games[idx]["id"])     # doble click
                    return
                self.saved_sel = idx
                self.saved_confirm_delete = None
                self._saved_click_t = time.time()
                return
        for _label, bid, rect in self.saved_buttons():
            if rect.collidepoint(pos):
                self.saved_action(bid)
                return

    def handle_saved_key(self, key):
        n = len(self.saved_games)
        if key == pygame.K_ESCAPE:
            self.saved_action("back")
        elif key in (pygame.K_DOWN, pygame.K_UP) and n:
            cur = -1 if self.saved_sel is None else self.saved_sel
            self.saved_sel = max(0, min(n - 1, cur + (1 if key == pygame.K_DOWN else -1)))
            if self.saved_sel < self.saved_scroll:
                self.saved_scroll = self.saved_sel
            elif self.saved_sel >= self.saved_scroll + self.SAVED_ROWS:
                self.saved_scroll = self.saved_sel - self.SAVED_ROWS + 1
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.saved_action("open")
        elif key == pygame.K_DELETE:
            self.saved_action("delete")

    def saved_action(self, bid):
        game = self.selected_saved_game()
        if bid == "back":
            self.mode = "menu"
            return
        if game is None:
            return
        if bid == "open":
            self.load_saved_game(game["id"])
        elif bid == "export":
            date_str = game["played_at"][:10].replace("-", ".")
            self.save_pgn_text(game["pgn"], date_str)
        elif bid == "delete":
            if self.saved_confirm_delete != game["id"]:
                self.saved_confirm_delete = game["id"]
                return
            db = self.get_db()
            if db and db.delete_game(game["id"]):
                self.toast("Partida borrada")
            self.saved_confirm_delete = None
            self.refresh_saved_games()

    def load_saved_game(self, game_id):
        """Abre una partida de la base en modo análisis, congelada en su
        resultado, para revisarla jugada por jugada con el análisis del motor."""
        import io

        import chess.pgn
        db = self.get_db()
        row = db.get_game(game_id) if db else None
        if row is None:
            self.toast("No se encontró la partida")
            return False
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        if game is None:
            self.toast("PGN inválido")
            return False
        self.start_game("analysis")
        self.board = game.board()            # respeta [FEN] si no arrancó de la inicial
        self.loaded_game_id = game_id
        self._game_over_seen = True          # no abrir panel ni autoguardar
        self.silent = True                   # reconstruir sin sonidos
        try:
            for move in game.mainline_moves():
                if move not in self.board.legal_moves:
                    break
                self.execute_move(move)
            self.anim_move = None
            self.game_over = False            # forzar el resultado guardado
            self.end_game(row["termination"], row["result"])
        finally:
            self.silent = False
        self.particles = []
        self._game_over_seen = True
        self.game_over_panel = False
        self.review_index = 0 if self.board.move_stack else None
        self.loaded_names = (row["white"], row["black"])
        return True

    # ─── EVENTOS ────────────────────────────────────────────────────────────────
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.VIDEORESIZE:
                self.on_resize(event.w, event.h)
            elif event.type == getattr(pygame, "WINDOWSIZECHANGED", -1):
                self.on_resize(event.x, event.y)

            elif event.type == pygame.KEYDOWN and self.mode == "saved":
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                else:
                    self.handle_saved_key(event.key)

            elif event.type == pygame.MOUSEWHEEL and self.mode == "saved":
                self.saved_scroll = max(0, min(max(0, len(self.saved_games) - self.SAVED_ROWS),
                                               self.saved_scroll - event.y))

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11 or (
                        event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT):
                    self.toggle_fullscreen()
                elif event.key == pygame.K_ESCAPE:
                    if self.confirm:
                        self.close_confirm()
                    elif self.game_over and self.game_over_panel:
                        self.close_game_over_panel()
                    elif self.game_over and self.review_index is not None:
                        self.review_index = None
                    elif self.game_over:
                        # Partida terminada: Esc nunca la borra; reabre el panel
                        self.game_over_panel = True
                    elif self.premove_from is not None:
                        self.clear_premove()
                    elif self.mode != "menu":
                        self.go_menu()
                    else:
                        return False
                elif event.key == pygame.K_f:
                    self.flip_board()
                elif event.key == pygame.K_m:
                    self.toggle_sound()
                elif event.key == pygame.K_t:
                    self.cycle_board_theme()
                elif event.key == pygame.K_r:
                    self.reset_game()
                elif event.key == pygame.K_z and (event.mod & pygame.KMOD_CTRL):
                    self.undo_move()
                elif self.game_over and not self.game_over_panel:
                    if event.key == pygame.K_LEFT:
                        self.review_step(-1)
                    elif event.key == pygame.K_RIGHT:
                        self.review_step(1)
                    elif event.key == pygame.K_HOME:
                        self.review_step(to=0)
                    elif event.key == pygame.K_END:
                        self.review_index = None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.handle_click(self.to_logical(event.pos))
                elif event.button == 3:   # click derecho cancela premove
                    self.clear_premove()
                    self.selected_sq = None
                    self.legal_moves_from = []

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and self.dragging:
                    self.handle_drop(self.to_logical(event.pos))

            elif event.type == pygame.MOUSEMOTION:
                pos = self.to_logical(event.pos)
                if self.dragging:
                    self.drag_pos = pos
                mx, my = pos
                self.hover_sq = self.pixel_to_sq(mx, my)

        return True

    def handle_click(self, pos):
        mx, my = pos

        if self.mode == "menu":
            self.handle_menu_click(pos)
            return
        if self.mode == "saved":
            self.handle_saved_click(pos)
            return

        # Promo
        if self.promotion_pending:
            self.handle_promotion_click(pos)
            return

        # Panel de fin de partida
        if self.game_over and self.game_over_panel:
            self.handle_game_over_click(pos)
            return
        # Partida terminada, panel cerrado: barra de revisión
        if self.game_over and self.handle_review_click(pos):
            return

        # Diálogo de confirmación (abandonar / tablas)
        if self.confirm:
            self.handle_confirm_click(pos)
            return

        # Botones del panel
        for _icon, _color, action, rect in self.panel_buttons():
            if rect.collidepoint(mx, my):
                action()
                return

        # Con la partida terminada el tablero es solo para mirar
        if self.game_over:
            return

        sq = self.pixel_to_sq(mx, my)
        if sq is None:
            return

        piece = self.board.piece_at(sq)
        player_color = chess.WHITE if self.board.turn == chess.WHITE else chess.BLACK
        if self.mode == "vsai":
            player_color = chess.WHITE if self.ai_color == chess.BLACK else chess.BLACK

        is_my_turn = (self.board.turn == player_color)
        opponent_moving = not is_my_turn and not self.game_over

        # ── Es turno del jugador ──
        if is_my_turn and not self.ai_thinking:
            if self.selected_sq is not None:
                # Ya hay una pieza seleccionada
                if sq == self.selected_sq:
                    # Click en la misma pieza: deseleccionar
                    self.selected_sq = None
                    self.legal_moves_from = []
                    self.dragging = False
                elif piece and piece.color == self.board.turn:
                    # Click en otra pieza propia: cambiar selección
                    self.selected_sq = sq
                    self.legal_moves_from = [m for m in self.board.legal_moves
                                              if m.from_square == sq]
                    self.drag_piece = piece
                    self.drag_from = sq
                    self.drag_pos = pos
                    self.dragging = True
                else:
                    # Click en destino: intentar mover
                    move = self.find_move(self.selected_sq, sq)
                    if move:
                        self.dragging = False
                        self.drag_piece = None
                        self.drag_from = None
                        self.attempt_move(move)
                    else:
                        # Destino inválido: deseleccionar
                        self.selected_sq = None
                        self.legal_moves_from = []
                        self.dragging = False
            else:
                # Sin selección previa: seleccionar pieza propia e iniciar drag
                if piece and piece.color == self.board.turn:
                    self.clear_premove()
                    self.selected_sq = sq
                    self.legal_moves_from = [m for m in self.board.legal_moves
                                              if m.from_square == sq]
                    self.drag_piece = piece
                    self.drag_from = sq
                    self.drag_pos = pos
                    self.dragging = True
            return

        # ── No es turno del jugador: registrar premove ──
        if opponent_moving or self.ai_thinking:
            own_piece = piece and piece.color == player_color
            if self.premove_from is None:
                if own_piece:
                    self.premove_from = sq
                    self.premove_to = None
                    self.premove_piece = piece
            else:
                if sq == self.premove_from:
                    self.clear_premove()
                elif own_piece:
                    self.premove_from = sq
                    self.premove_to = None
                    self.premove_piece = piece
                else:
                    self.premove_to = sq

    def handle_drop(self, pos):
        self.dragging = False
        sq = self.pixel_to_sq(*pos)

        if self.drag_from is None:
            self.drag_piece = None
            return

        player_color = chess.WHITE if self.ai_color == chess.BLACK else chess.BLACK
        if self.mode != "vsai":
            player_color = self.board.turn

        is_my_turn = (self.board.turn == player_color)

        if is_my_turn:
            if sq is not None and sq != self.drag_from:
                # Soltar en casilla diferente: intentar mover
                move = self.find_move(self.drag_from, sq)
                if move:
                    self.selected_sq = None
                    self.legal_moves_from = []
                    self.attempt_move(move)
                else:
                    # Destino inválido: mantener selección para click-to-move
                    self.selected_sq = self.drag_from
                    self.legal_moves_from = [m for m in self.board.legal_moves
                                              if m.from_square == self.drag_from]
            # Si soltó en la misma casilla: la selección ya quedó activa desde handle_click
        else:
            # Drag en turno rival → premove destino
            if sq is not None and sq != self.drag_from:
                self.premove_from = self.drag_from
                self.premove_to = sq
                self.premove_piece = self.drag_piece
            else:
                self.clear_premove()

        self.drag_piece = None
        self.drag_from = None

    def handle_promotion_click(self, pos):
        mx, my = pos
        pieces = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        pw, ph = 200, 60
        px = WINDOW_W//2 - pw//2
        py = WINDOW_H//2 - (len(pieces)*ph + 40)//2
        for i, pt in enumerate(pieces):
            bx, by = px, py + 30 + i*ph
            brect = pygame.Rect(bx, by, pw, ph - 8)
            if brect.collidepoint(mx, my):
                # Buscar el movimiento de promoción con esta pieza
                for move in self.promotion_pending:
                    if move.promotion == pt:
                        self.promotion_pending = None
                        self.execute_move(move)
                        return

    GAME_OVER_CLICK_GRACE = 0.5   # s: evita que el click de la última jugada toque un botón

    def handle_game_over_click(self, pos):
        if time.time() - getattr(self, "game_over_time", 0) < self.GAME_OVER_CLICK_GRACE:
            return False
        for _label, action, rect in self.game_over_buttons():
            if rect.collidepoint(pos):
                action()
                return True
        return False

    def handle_review_click(self, pos):
        for bid, rect in self.review_buttons():
            if rect.collidepoint(pos):
                if bid == "first":
                    self.review_step(to=0)
                elif bid == "prev":
                    self.review_step(-1)
                elif bid == "next":
                    self.review_step(1)
                elif bid == "last":
                    self.review_index = None
                else:
                    self.game_over_panel = True
                return True
        return False

    def handle_menu_click(self, pos):
        mx, my = pos
        for _label, _icon, action, _color, rect in self.menu_main_buttons():
            if rect.collidepoint(mx, my):
                if action == "saved":
                    self.open_saved_games()
                else:
                    self.start_game(action)
                return

        setters = [
            lambda v: setattr(self, "ai_depth", v),
            lambda v: setattr(self, "player_color_choice", v),
            lambda v: setattr(self, "time_selected", v),
        ]
        for (_lbl, _y, _acc, options), setter in zip(self.menu_option_rows(), setters):
            for _text, rect, _sel, value in options:
                if rect.collidepoint(mx, my):
                    setter(value)
                    return

    def start_game(self, mode):
        self.mode = mode
        self.flipped = False
        if mode == "vsai":
            choice = self.player_color_choice
            if choice == "random":
                choice = random.choice(["white", "black"])
            self.ai_color = chess.BLACK if choice == "white" else chess.WHITE
            # El jugador siempre ve su bando abajo
            self.flipped = self.ai_color == chess.WHITE
        # Sin reloj en modo análisis
        self.use_timer = (mode != "analysis")
        # reset_game() también lanza la IA si arranca ella (jugador con negras)
        self.reset_game()

    def flag_fall(self, color):
        """Al bando `color` se le acabó el tiempo. Si el rival no tiene
        material para dar mate de ninguna forma, es tablas (regla FIDE 6.9)."""
        if color == chess.WHITE:
            self.time_white = 0
        else:
            self.time_black = 0
        self.end_game(*flag_end(self.board, color))

    # ─── LOOP PRINCIPAL ─────────────────────────────────────────────────────────
    def update(self):
        now = time.time()
        self.sync_game_over_panel()
        self.request_analysis()

        # Temporizador — corre siempre excepto en menú, fin de juego o promoción
        if self.game_over and self.final_times is not None:
            # Defensa extra: con la partida terminada los relojes no se mueven
            self.time_white, self.time_black = self.final_times
        elif (self.use_timer and self.mode in ("pvp", "vsai") and
                not self.game_over and not self.promotion_pending):
            dt = now - self.time_last
            # El reloj del bando que mueve corre siempre, también mientras
            # piensa la IA (antes se congelaba y la IA pensaba gratis).
            if self.board.turn == chess.WHITE:
                self.time_white = max(0, self.time_white - dt)
                if self.time_white == 0:
                    self.flag_fall(chess.WHITE)
            else:
                self.time_black = max(0, self.time_black - dt)
                if self.time_black == 0:
                    self.flag_fall(chess.BLACK)
            self.check_low_time()
        self.time_last = now

        # IA — el cálculo corre en un hilo aparte (start_ai_search); acá solo
        # esperamos que termine y que haya pasado el delay visual mínimo.
        if (self.ai_thinking and self.ai_move_ready
                and (now - self.ai_think_start) >= self.ai_delay):
            self.ai_move()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        pygame.quit()
        sys.exit()


def main():
    """Punto de entrada (`cabrechess`, `python -m cabrechess` y el .exe)."""
    CabreChess().run()
