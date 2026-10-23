# SPDX-License-Identifier: GPL-3.0-or-later
"""Constantes de ventana, colores y glifos."""
import chess

# ─── CONSTANTES ────────────────────────────────────────────────────────────────
WINDOW_W, WINDOW_H = 1100, 780
BOARD_SIZE = 640
SQUARE_SIZE = BOARD_SIZE // 8
BOARD_X = 60
BOARD_Y = 70

# Colores Lichess
BG_COLOR        = (22,  21,  18)
PANEL_COLOR     = (30,  29,  26)
LIGHT_SQ        = (240, 217, 181)
DARK_SQ         = (181, 136,  99)
HIGHLIGHT_SQ    = (205, 210,  106)

# Temas de tablero (colores de Lichess): clave -> (nombre, clara, oscura).
# El primero es el de siempre y el que se usa por defecto.
BOARD_THEMES = {
    "marron": ("Marrón", (240, 217, 181), (181, 136,  99)),
    "azul":   ("Azul",   (222, 227, 230), (140, 162, 173)),
    "verde":  ("Verde",  (255, 255, 221), (134, 166, 102)),
    "gris":   ("Gris",   (220, 220, 220), (171, 171, 171)),
}
DEFAULT_THEME = "marron"
SELECTED_SQ     = (246, 246, 105)
LEGAL_DOT       = (0,   0,   0,  80)
CHECK_SQ        = (220,  50,  50, 180)
LAST_MOVE       = (170, 162,  58, 180)
HOVER_COLOR     = (255, 255, 255,  25)
TEXT_COLOR      = (186, 186, 186)
TEXT_BRIGHT     = (255, 255, 255)
TEXT_DIM        = (100, 100, 100)
ACCENT          = (138, 196,  33)    # verde Lichess
ACCENT2         = ( 81, 150, 200)    # azul
DANGER          = (220,  55,  55)
BORDER_COLOR    = ( 55,  54,  50)
PREMOVE_SQ      = (200,  80,  80)    # rojo-naranja para premove (igual Lichess)
PREMOVE_ALPHA   = 170
MOVE_BG         = ( 38,  37,  34)
MOVE_ACTIVE     = ( 55,  54,  50)
PANEL_W         = WINDOW_W - BOARD_X - BOARD_SIZE - 20
PANEL_X         = BOARD_X + BOARD_SIZE + 16

# Layout del menú principal (filas de opciones)
MENU_OPT_X      = WINDOW_W // 2 - 200      # columna de etiquetas
MENU_BTN_X      = WINDOW_W // 2 - 80       # primera columna de botones
MENU_ROW_Y      = (560, 598, 636)          # dificultad / color / tiempo

# Piezas Unicode
PIECE_UNICODE = {
    (chess.KING,   chess.WHITE): '♔',
    (chess.QUEEN,  chess.WHITE): '♕',
    (chess.ROOK,   chess.WHITE): '♖',
    (chess.BISHOP, chess.WHITE): '♗',
    (chess.KNIGHT, chess.WHITE): '♘',
    (chess.PAWN,   chess.WHITE): '♙',
    (chess.KING,   chess.BLACK): '♚',
    (chess.QUEEN,  chess.BLACK): '♛',
    (chess.ROOK,   chess.BLACK): '♜',
    (chess.BISHOP, chess.BLACK): '♝',
    (chess.KNIGHT, chess.BLACK): '♞',
    (chess.PAWN,   chess.BLACK): '♟',
}
