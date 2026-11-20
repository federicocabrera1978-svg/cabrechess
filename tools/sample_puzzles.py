# SPDX-License-Identifier: GPL-3.0-or-later
"""Arma cabrechess/assets/puzzles/lichess_puzzles.csv a partir de la base
pública de puzzles de Lichess (CC0, https://database.lichess.org/#puzzles).

Uso (con un CSV ya descomprimido, o un tramo inicial de él):

    curl -sL https://database.lichess.org/lichess_db_puzzle.csv.zst \\
        | zstd -dc | head -n 300001 > /tmp/puz.csv
    python tools/sample_puzzles.py /tmp/puz.csv

La selección es determinística: puzzles populares y bien calificados entre
800 y 2000 de rating, repartidos por tema y por franja de rating. No se
inventa nada: cada fila es una fila real de la base de Lichess.
"""

import csv
import random
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "cabrechess" / "assets" / "puzzles" / "lichess_puzzles.csv"
THEMES = (
    "mateIn1",
    "mateIn2",
    "backRankMate",
    "fork",
    "pin",
    "skewer",
    "discoveredAttack",
    "hangingPiece",
    "sacrifice",
    "deflection",
    "trappedPiece",
    "promotion",
)
BANDS = ((800, 1100), (1100, 1400), (1400, 1700), (1700, 2001))
PER_CELL = 2  # puzzles por (tema, franja)
FIELDS = ("PuzzleId", "FEN", "Moves", "Rating", "Themes", "GameUrl")
HEADER = (
    "# Puzzles de la base pública de Lichess (https://database.lichess.org/#puzzles),\n"
    "# dominio público (CC0). Generado con tools/sample_puzzles.py; no editar a mano.\n"
)


def good(row):
    try:
        rating = int(row["Rating"])
        return (
            800 <= rating <= 2000
            and int(row["RatingDeviation"]) <= 80
            and int(row["Popularity"]) >= 90
            and int(row["NbPlays"]) >= 1000
            and len(row["Moves"].split()) <= 8
        )
    except (KeyError, ValueError):
        return False


def main(src):
    with open(src, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if good(r)]
    rng = random.Random(2026)
    rng.shuffle(rows)
    chosen, seen = [], set()
    for theme in THEMES:
        for lo, hi in BANDS:
            cell = [
                r
                for r in rows
                if theme in r["Themes"].split() and lo <= int(r["Rating"]) < hi and r["PuzzleId"] not in seen
            ][:PER_CELL]
            for r in cell:
                seen.add(r["PuzzleId"])
                chosen.append(r)
    rng.shuffle(chosen)  # orden fijo pero mezclado: el puzzle del día varía de tema y rating
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        f.write(HEADER)
        w = csv.writer(f, lineterminator="\n")
        w.writerow(FIELDS)
        for r in chosen:
            w.writerow([r[k] for k in FIELDS])
    print(f"{len(chosen)} puzzles -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/puz.csv")
