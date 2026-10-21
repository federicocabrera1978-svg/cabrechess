# SPDX-License-Identifier: GPL-3.0-or-later
"""Lógica pura del reloj: formato y resultado por bandera."""

TIME_OPTIONS = [60, 180, 300, 600]   # 1/3/5/10 min en segundos
TIME_INCREMENT = 3                    # +3s por movimiento (Fischer)


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
