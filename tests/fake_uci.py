# SPDX-License-Identifier: GPL-3.0-or-later
"""Motor UCI de mentira para los tests del rival Stockfish (B4).

Responde lo mínimo del protocolo UCI y juega siempre la primera jugada legal
(en orden UCI). Anota en FAKE_UCI_LOG los "setoption" que recibe."""
import os
import sys

import chess

board = chess.Board()
log = os.environ.get("FAKE_UCI_LOG")


def out(line):
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


for raw in sys.stdin:
    line = raw.strip()
    if line == "uci":
        out("id name FakeFish")
        out("option name Skill Level type spin default 20 min 0 max 20")
        out("uciok")
    elif line == "isready":
        out("readyok")
    elif line.startswith("setoption") and log:
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    elif line.startswith("position"):
        parts = line.split()
        if parts[1] == "startpos":
            board = chess.Board()
            rest = parts[2:]
        else:
            idx = parts.index("moves") if "moves" in parts else len(parts)
            board = chess.Board(" ".join(parts[2:idx]))
            rest = parts[idx:]
        if rest and rest[0] == "moves":
            for uci in rest[1:]:
                board.push_uci(uci)
    elif line.startswith("go"):
        moves = sorted(board.legal_moves, key=lambda m: m.uci())
        out(f"bestmove {moves[0].uci() if moves else '0000'}")
    elif line == "quit":
        break
