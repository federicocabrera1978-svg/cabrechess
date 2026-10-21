# SPDX-License-Identifier: GPL-3.0-or-later
"""Sonidos del juego: mover, capturar, jaque, enroque, fin de partida y reloj bajo.

Los sonidos se sintetizan en memoria al arrancar (sin archivos ni licencias de
terceros): son cortos golpes "de madera" y tonos suaves. Si no hay dispositivo de
audio (o pygame.mixer no arranca) todo queda en silencio sin errores.
"""
import math
from array import array

import pygame

LOW_TIME_SECONDS = 10   # aviso de reloj bajo al cruzar este umbral

# nombre -> lista de "notas" (frecuencia Hz, duración s, volumen 0-1, tipo)
_RECIPES = {
    "move":    [(520, 0.07, 0.55, "knock")],
    "capture": [(380, 0.06, 0.70, "knock"), (260, 0.09, 0.60, "knock")],
    "castle":  [(520, 0.06, 0.50, "knock"), (600, 0.07, 0.50, "knock")],
    "check":   [(880, 0.09, 0.40, "tone"), (1175, 0.14, 0.35, "tone")],
    "end":     [(523, 0.14, 0.35, "tone"), (659, 0.14, 0.35, "tone"),
                (784, 0.30, 0.35, "tone")],
    "low_time": [(1320, 0.05, 0.30, "tone"), (0, 0.06, 0, "rest"),
                 (1320, 0.05, 0.30, "tone")],
}


def _synth(notes, rate):
    """Devuelve muestras mono int16 para la receta `notes`."""
    out = array("h")
    for freq, dur, vol, kind in notes:
        n = int(rate * dur)
        for i in range(n):
            t = i / rate
            if kind == "rest":
                out.append(0)
                continue
            if kind == "knock":
                # golpe seco: decaimiento rápido + un armónico grave
                env = math.exp(-t * 60)
                s = math.sin(2 * math.pi * freq * t) + 0.5 * math.sin(math.pi * freq * t)
                s /= 1.5
            else:
                # tono suave con ataque y caída cortos (sin "clicks")
                attack = min(1.0, t / 0.005)
                env = attack * math.exp(-t * 8)
                s = math.sin(2 * math.pi * freq * t)
            out.append(int(max(-1.0, min(1.0, s * env * vol)) * 32767))
    return out


def sound_for_move(board_before, move, board_after):
    """Qué sonido corresponde a `move` (board_before = antes de jugarla)."""
    if board_after.is_checkmate() or board_after.is_stalemate():
        return "end"
    if board_after.is_check():
        return "check"
    if board_before.is_castling(move):
        return "castle"
    if board_before.is_capture(move):
        return "capture"
    return "move"


class SoundManager:
    def __init__(self, enabled=True):
        self.enabled = bool(enabled)
        self.sounds = {}
        self.available = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            init = pygame.mixer.get_init()
        except pygame.error:
            init = None
        if not init:
            return
        rate, size, channels = init
        if size != -16:          # solo armamos buffers de 16 bits con signo
            return
        try:
            for name, notes in _RECIPES.items():
                mono = _synth(notes, rate)
                if channels == 1:
                    data = mono
                else:
                    data = array("h")
                    for s in mono:
                        data.extend([s] * channels)
                self.sounds[name] = pygame.mixer.Sound(buffer=data.tobytes())
            self.available = True
        except (pygame.error, ValueError):
            self.sounds = {}

    def play(self, name):
        """Reproduce `name` si el sonido está activado. Devuelve True si sonó."""
        if not self.enabled or not self.available:
            return False
        snd = self.sounds.get(name)
        if snd is None:
            return False
        try:
            snd.play()
        except pygame.error:
            return False
        return True

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled
