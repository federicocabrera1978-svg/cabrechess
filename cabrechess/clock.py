# SPDX-License-Identifier: GPL-3.0-or-later
"""Lógica pura del reloj: formato y resultado por bandera."""

# Controles de tiempo estilo Lichess: (etiqueta, base en segundos, incremento).
TIME_CONTROLS = [
    ("1+0", 60, 0),
    ("2+1", 120, 1),
    ("3+2", 180, 2),
    ("5+3", 300, 3),
    ("10+5", 600, 5),
    ("15+10", 900, 10),
]
DEFAULT_TIME_CONTROL = "3+2"
TIME_OPTIONS = [base for _l, base, _i in TIME_CONTROLS]
TIME_INCREMENT = 2                    # incremento del control por defecto (3+2)
MAX_BASE_MINUTES = 180
MAX_INCREMENT = 60


def parse_time_control(text):
    """"M+S" (minutos + segundos de incremento) -> (base_segundos, incremento).
    Devuelve None si el texto no es válido. Ej.: "3+2" -> (180, 2)."""
    if not isinstance(text, str):
        return None
    parts = text.strip().split("+")
    if len(parts) != 2:
        return None
    try:
        minutes, inc = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (1 <= minutes <= MAX_BASE_MINUTES and 0 <= inc <= MAX_INCREMENT):
        return None
    return minutes * 60, inc


def time_control_label(base, inc):
    """(180, 2) -> "3+2". Bases que no son minutos enteros se muestran en
    minutos con decimales (90 s -> "1.5+0")."""
    minutes = base / 60
    m = str(int(minutes)) if minutes == int(minutes) else f"{minutes:g}"
    return f"{m}+{int(inc)}"


def time_category(base, inc):
    """Categoría como en Lichess, por la duración estimada base + 40 × incremento:
    Bala (< 3 min), Blitz (< 8 min), Rápida (< 25 min) o Clásica."""
    total = base + 40 * inc
    if total < 180:
        return "Bala"
    if total < 480:
        return "Blitz"
    if total < 1500:
        return "Rápida"
    return "Clásica"


def format_clock(t):
    """Formato estilo Lichess: m:ss, con décimas si queda menos de 1 minuto."""
    mins = int(t) // 60
    secs = int(t) % 60
    tenths = int((t - int(t)) * 10)
    if t < 60:
        return f"{mins}:{secs:02d}.{tenths}"
    return f"{mins}:{secs:02d}"


def flag_fall_message(board, color):
    """Mensaje de fin de partida cuando a `color` se le acabó el tiempo
    (ver cabrechess.endings)."""
    from .endings import end_message, flag_end
    return end_message(*flag_end(board, color))
