# SPDX-License-Identifier: GPL-3.0-or-later
"""Escalado de la ventana: el juego dibuja en una superficie lógica de tamaño
fijo (WINDOW_W x WINDOW_H) que se escala a la ventana real manteniendo la
proporción, con barras negras (letterbox) si sobra espacio."""
from .constants import WINDOW_H, WINDOW_W

MIN_W, MIN_H = 770, 546          # ~70% del tamaño lógico


def compute_viewport(win_w, win_h, logical_w=WINDOW_W, logical_h=WINDOW_H):
    """Devuelve (scale, x, y, w, h): dónde y a qué tamaño va la superficie
    lógica dentro de una ventana de win_w x win_h."""
    win_w, win_h = max(1, win_w), max(1, win_h)
    scale = min(win_w / logical_w, win_h / logical_h)
    w = max(1, round(logical_w * scale))
    h = max(1, round(logical_h * scale))
    return scale, (win_w - w) // 2, (win_h - h) // 2, w, h


def window_to_logical(pos, viewport, logical_w=WINDOW_W, logical_h=WINDOW_H):
    """Convierte una posición del mouse en la ventana a coordenadas lógicas.
    Fuera del área del juego (en las barras negras) devuelve (-1, -1), que
    no coincide con ningún botón ni casilla."""
    scale, x0, y0, w, h = viewport
    x, y = pos
    if not (x0 <= x < x0 + w and y0 <= y < y0 + h):
        return (-1, -1)
    lx = min(logical_w - 1, int((x - x0) / scale))
    ly = min(logical_h - 1, int((y - y0) / scale))
    return (lx, ly)


def clamp_window_size(w, h):
    """Respeta el tamaño mínimo de la ventana."""
    return max(MIN_W, w), max(MIN_H, h)


def enable_windows_dpi_awareness():
    """En Windows con escalado (125%/150%...), sin esto el sistema estira la
    ventana como un bitmap (se ve borrosa) y SDL recibe tamaños "virtuales".
    Hay que llamarlo antes de crear la ventana. En otros sistemas no hace nada.
    Devuelve True si se pudo activar."""
    import sys
    if sys.platform != "win32":
        return False
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # per-monitor
        return True
    except (AttributeError, OSError):
        pass
    try:
        return bool(ctypes.windll.user32.SetProcessDPIAware())   # Vista/7
    except (AttributeError, OSError):
        return False


def initial_window_size(desktop_size, fraction=0.85):
    """Tamaño inicial: la mayor ventana con la proporción del juego que entre
    en `fraction` del escritorio (nunca menos que el mínimo)."""
    dw, dh = desktop_size
    scale = min(dw * fraction / WINDOW_W, dh * fraction / WINDOW_H)
    return clamp_window_size(round(WINDOW_W * scale), round(WINDOW_H * scale))
