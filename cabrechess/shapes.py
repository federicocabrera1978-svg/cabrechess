# SPDX-License-Identifier: GPL-3.0-or-later
"""Flechas y círculos del usuario sobre el tablero (A8, como en Lichess).

Click derecho y soltar en la misma casilla = círculo; arrastrar con el click
derecho hasta otra casilla = flecha. Repetir la misma forma con el mismo color
la borra; con otro color la cambia de color. El color sale de las teclas que
se mantienen apretadas al empezar el trazo:

- sin teclas: verde
- Shift o Ctrl: rojo
- Alt: azul
- Shift + Alt (o Ctrl + Alt): amarillo

Las formas pertenecen a la posición en la que se dibujaron: al mover, deshacer
o revisar otra jugada desaparecen solas.
"""
from dataclasses import dataclass

# Colores de Lichess (RGBA, semitransparentes)
SHAPE_COLORS = {
    "green": (21, 120, 27, 175),
    "red": (136, 32, 32, 175),
    "blue": (0, 48, 136, 175),
    "yellow": (230, 143, 0, 175),
}


def color_from_mods(shift=False, ctrl=False, alt=False):
    """Color de la forma según los modificadores (mismo criterio que Lichess)."""
    red = shift or ctrl
    if red and alt:
        return "yellow"
    if red:
        return "red"
    if alt:
        return "blue"
    return "green"


@dataclass(frozen=True)
class Shape:
    orig: int
    dest: int
    color: str = "green"

    @property
    def is_circle(self):
        return self.orig == self.dest


class ShapeLayer:
    """Formas dibujadas sobre una posición concreta.

    ``key`` identifica la posición (por ejemplo FEN + jugada); si la posición que
    se muestra cambia, las formas se descartan.
    """

    def __init__(self):
        self.shapes = []
        self.key = None

    def for_position(self, key):
        """Formas de la posición ``key`` (si cambió la posición, quedan vacías)."""
        if key != self.key:
            self.shapes = []
            self.key = key
        return list(self.shapes)

    def toggle(self, key, orig, dest, color="green"):
        """Agrega, cambia de color o borra la forma orig→dest. Devuelve la lista."""
        self.for_position(key)
        for i, s in enumerate(self.shapes):
            if s.orig == orig and s.dest == dest:
                if s.color == color:
                    del self.shapes[i]
                else:
                    self.shapes[i] = Shape(orig, dest, color)
                return list(self.shapes)
        self.shapes.append(Shape(orig, dest, color))
        return list(self.shapes)

    def clear(self):
        self.shapes = []
