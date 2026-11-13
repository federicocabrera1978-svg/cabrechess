# SPDX-License-Identifier: GPL-3.0-or-later
"""Transiciones suaves entre pantallas (menú, ajustes, partida...).

Al cambiar de pantalla se dibuja la nueva y encima un velo oscuro que se
desvanece en TRANSITION_SECONDS. Funciones puras: se testean sin pantalla.
"""

TRANSITION_SECONDS = 0.22
TRANSITION_START_ALPHA = 200


def ease_out(t):
    """Curva suave (cuadrática) para t en [0, 1]."""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 2


def fade_alpha(elapsed, duration=TRANSITION_SECONDS, start=TRANSITION_START_ALPHA):
    """Opacidad del velo tras `elapsed` segundos: `start` al empezar y 0 al
    terminar (o si duration <= 0)."""
    if duration <= 0 or elapsed >= duration:
        return 0
    if elapsed <= 0:
        return int(start)
    return int(round(start * (1 - ease_out(elapsed / duration))))
