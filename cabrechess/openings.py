# SPDX-License-Identifier: GPL-3.0-or-later
"""Nombres de aperturas (código ECO + nombre en castellano).

La tabla es chica y curada a mano: cubre las aperturas y variantes más
jugadas. La búsqueda es por posición (no por orden de jugadas), así que
reconoce transposiciones: 1.Nf3 d5 2.d4 llega a la misma apertura que
1.d4 d5 2.Nf3.
"""
from functools import lru_cache

import chess

# (código ECO, nombre, jugadas en SAN desde la posición inicial)
OPENINGS = [
    # 1.e4 e5
    ("B00", "Apertura del peón de rey", "e4"),
    ("C20", "Partida abierta", "e4 e5"),
    ("C21", "Gambito del centro", "e4 e5 d4 exd4"),
    ("C23", "Apertura del alfil", "e4 e5 Bc4"),
    ("C25", "Apertura Vienesa", "e4 e5 Nc3"),
    ("C30", "Gambito de rey", "e4 e5 f4"),
    ("C33", "Gambito de rey aceptado", "e4 e5 f4 exf4"),
    ("C40", "Apertura del caballo de rey", "e4 e5 Nf3"),
    ("C40", "Gambito Letón", "e4 e5 Nf3 f5"),
    ("C41", "Defensa Philidor", "e4 e5 Nf3 d6"),
    ("C42", "Defensa Petrov", "e4 e5 Nf3 Nf6"),
    ("C44", "Apertura del caballo de rey", "e4 e5 Nf3 Nc6"),
    ("C44", "Apertura Escocesa", "e4 e5 Nf3 Nc6 d4"),
    ("C45", "Apertura Escocesa", "e4 e5 Nf3 Nc6 d4 exd4 Nxd4"),
    ("C46", "Apertura de los tres caballos", "e4 e5 Nf3 Nc6 Nc3"),
    ("C47", "Apertura de los cuatro caballos", "e4 e5 Nf3 Nc6 Nc3 Nf6"),
    ("C50", "Apertura Italiana", "e4 e5 Nf3 Nc6 Bc4"),
    ("C50", "Apertura Italiana: Giuoco Piano", "e4 e5 Nf3 Nc6 Bc4 Bc5"),
    ("C51", "Gambito Evans", "e4 e5 Nf3 Nc6 Bc4 Bc5 b4"),
    ("C53", "Apertura Italiana: Giuoco Piano, 4.c3", "e4 e5 Nf3 Nc6 Bc4 Bc5 c3"),
    ("C55", "Defensa de los dos caballos", "e4 e5 Nf3 Nc6 Bc4 Nf6"),
    ("C57", "Defensa de los dos caballos: 4.Cg5", "e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5"),
    ("C60", "Apertura Española (Ruy López)", "e4 e5 Nf3 Nc6 Bb5"),
    ("C63", "Apertura Española: Gambito Schliemann", "e4 e5 Nf3 Nc6 Bb5 f5"),
    ("C65", "Apertura Española: Defensa Berlinesa", "e4 e5 Nf3 Nc6 Bb5 Nf6"),
    ("C68", "Apertura Española: Variante del cambio", "e4 e5 Nf3 Nc6 Bb5 a6 Bxc6"),
    ("C70", "Apertura Española: Defensa Morphy", "e4 e5 Nf3 Nc6 Bb5 a6"),
    ("C77", "Apertura Española: Defensa Morphy", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6"),
    # 1.e4, otras respuestas
    ("B01", "Defensa Escandinava", "e4 d5"),
    ("B02", "Defensa Alekhine", "e4 Nf6"),
    ("B06", "Defensa Moderna", "e4 g6"),
    ("B07", "Defensa Pirc", "e4 d6 d4 Nf6 Nc3 g6"),
    ("B10", "Defensa Caro-Kann", "e4 c6"),
    ("B12", "Defensa Caro-Kann: Variante del avance", "e4 c6 d4 d5 e5"),
    ("B13", "Defensa Caro-Kann: Variante del cambio", "e4 c6 d4 d5 exd5 cxd5"),
    ("B15", "Defensa Caro-Kann", "e4 c6 d4 d5 Nc3 dxe4 Nxe4"),
    ("B18", "Defensa Caro-Kann: Variante clásica", "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Bf5"),
    ("B20", "Defensa Siciliana", "e4 c5"),
    ("B21", "Defensa Siciliana: Gambito Smith-Morra", "e4 c5 d4 cxd4 c3"),
    ("B22", "Defensa Siciliana: Variante Alapin", "e4 c5 c3"),
    ("B23", "Defensa Siciliana: Variante cerrada", "e4 c5 Nc3"),
    ("B30", "Defensa Siciliana", "e4 c5 Nf3 Nc6"),
    ("B33", "Defensa Siciliana: Variante Sveshnikov", "e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 Nf6 Nc3 e5"),
    ("B40", "Defensa Siciliana", "e4 c5 Nf3 e6"),
    ("B50", "Defensa Siciliana", "e4 c5 Nf3 d6"),
    ("B70", "Defensa Siciliana: Variante del Dragón", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 g6"),
    ("B90", "Defensa Siciliana: Variante Najdorf", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6"),
    ("C00", "Defensa Francesa", "e4 e6"),
    ("C01", "Defensa Francesa: Variante del cambio", "e4 e6 d4 d5 exd5"),
    ("C02", "Defensa Francesa: Variante del avance", "e4 e6 d4 d5 e5"),
    ("C03", "Defensa Francesa: Variante Tarrasch", "e4 e6 d4 d5 Nd2"),
    ("C10", "Defensa Francesa", "e4 e6 d4 d5 Nc3"),
    ("C11", "Defensa Francesa: Variante clásica", "e4 e6 d4 d5 Nc3 Nf6"),
    ("C15", "Defensa Francesa: Variante Winawer", "e4 e6 d4 d5 Nc3 Bb4"),
    # 1.d4
    ("A40", "Apertura del peón de dama", "d4"),
    ("D00", "Apertura del peón de dama", "d4 d5"),
    ("D00", "Sistema Londres", "d4 d5 Bf4"),
    ("D02", "Sistema Londres", "d4 d5 Nf3 Nf6 Bf4"),
    ("D06", "Gambito de dama", "d4 d5 c4"),
    ("D07", "Gambito de dama: Defensa Chigorin", "d4 d5 c4 Nc6"),
    ("D08", "Gambito de dama: Contragambito Albin", "d4 d5 c4 e5"),
    ("D10", "Defensa Eslava", "d4 d5 c4 c6"),
    ("D20", "Gambito de dama aceptado", "d4 d5 c4 dxc4"),
    ("D30", "Gambito de dama rehusado", "d4 d5 c4 e6"),
    ("D43", "Defensa Semieslava", "d4 d5 c4 c6 Nf3 Nf6 Nc3 e6"),
    ("A45", "Defensa India", "d4 Nf6"),
    ("A45", "Sistema Londres", "d4 Nf6 Bf4"),
    ("A50", "Defensa India", "d4 Nf6 c4"),
    ("A56", "Defensa Benoni", "d4 Nf6 c4 c5"),
    ("A57", "Gambito Benko", "d4 Nf6 c4 c5 d5 b5"),
    ("A60", "Defensa Benoni Moderna", "d4 Nf6 c4 c5 d5 e6"),
    ("D80", "Defensa Grünfeld", "d4 Nf6 c4 g6 Nc3 d5"),
    ("E00", "Apertura Catalana", "d4 Nf6 c4 e6 g3"),
    ("E11", "Defensa Bogo-India", "d4 Nf6 c4 e6 Nf3 Bb4+"),
    ("E12", "Defensa India de dama", "d4 Nf6 c4 e6 Nf3 b6"),
    ("E20", "Defensa Nimzo-India", "d4 Nf6 c4 e6 Nc3 Bb4"),
    ("E60", "Defensa India de rey", "d4 Nf6 c4 g6"),
    ("E61", "Defensa India de rey", "d4 Nf6 c4 g6 Nc3 Bg7"),
    ("A80", "Defensa Holandesa", "d4 f5"),
    # Aperturas de flanco
    ("A00", "Apertura Polaca", "b4"),
    ("A01", "Apertura Larsen", "b3"),
    ("A02", "Apertura Bird", "f4"),
    ("A04", "Apertura Réti", "Nf3"),
    ("A09", "Apertura Réti", "Nf3 d5 c4"),
    ("A10", "Apertura Inglesa", "c4"),
    ("A20", "Apertura Inglesa: Siciliana invertida", "c4 e5"),
    ("A30", "Apertura Inglesa: Variante simétrica", "c4 c5"),
]

# Más allá de esta jugada no buscamos (la tabla no es más profunda).
MAX_PLY = 24


def _key(board):
    """Clave de posición: piezas, turno y enroques (sin contadores)."""
    return board.epd()


def _build_index():
    index = {}
    for eco, name, line in OPENINGS:
        board = chess.Board()
        for san in line.split():
            board.push_san(san)
        index[_key(board)] = (eco, name)
    return index


_INDEX = _build_index()


def opening_for_moves(moves):
    """Apertura de la posición más avanzada que figure en la tabla.

    `moves` es una secuencia de chess.Move desde la posición inicial.
    Devuelve (eco, nombre) o None si no se reconoce ninguna.
    """
    return _lookup(tuple(m.uci() for m in list(moves)[:MAX_PLY]))


@lru_cache(maxsize=256)
def _lookup(ucis):
    board = chess.Board()
    found = None
    for uci in ucis:
        board.push_uci(uci)
        hit = _INDEX.get(_key(board))
        if hit:
            found = hit
    return found


def opening_for_board(board):
    """Apertura de una partida a partir de su chess.Board (usa move_stack).

    Si el tablero no arrancó de la posición inicial, devuelve None.
    """
    if board.root() != chess.Board():
        return None
    return opening_for_moves(board.move_stack)


def opening_label(board):
    """Texto corto para la UI, p. ej. "B20 · Defensa Siciliana", o ""."""
    hit = opening_for_board(board)
    return f"{hit[0]} · {hit[1]}" if hit else ""
