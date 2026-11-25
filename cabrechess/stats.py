# SPDX-License-Identifier: GPL-3.0-or-later
"""Estadísticas locales de las partidas contra la IA (stats.json).

El archivo vive en la misma carpeta de datos que settings.json (ver
``settings.data_dir``: %APPDATA%\\CabreChess, ~/.cabrechess o
CABRECHESS_DATA_DIR). Formato::

    {"version": 1,
     "games": [{"date": "2026-11-23T10:15:00", "result": "win", "level": 3,
                "engine": "cabrechess", "color": "white", "time_control": "3+2",
                "termination": "checkmate"}, ...]}

Las partidas de Chess960 llevan además ``"variant": "chess960"`` (sin la clave
= clásica, así los stats.json viejos siguen valiendo). Cuentan igual para los
totales, la tabla por nivel y el Elo (el rival es el mismo nivel de IA), y
``summarize`` las resume también aparte en ``"chess960"``.

Se guarda solo la lista de partidas; los totales y el Elo se recalculan al
leerla, así nunca quedan desincronizados. Si el archivo está roto se aparta
como ``stats.json.corrupto`` (no se pierde) y se empieza de cero.

Elo estimado: fórmula estándar de Elo con K fijo (``K_FACTOR``), partiendo de
``START_ELO`` y jugando cada partida, en orden, contra el Elo asignado al nivel
de la IA (``AI_LEVEL_ELO`` / ``STOCKFISH_LEVEL_ELO``). Es una referencia local,
no un rating oficial.
"""

import datetime
import json
import os
from pathlib import Path

from .settings import data_dir

STATS_VERSION = 1
START_ELO = 1200  # Elo inicial del jugador
K_FACTOR = 32  # K fijo (el de FIDE para jugadores nuevos es 40; 32 es el clásico)
PROVISIONAL_GAMES = 10  # con menos partidas el Elo se muestra como provisional

# Elo aproximado de cada nivel del motor propio (engine.AI_LEVELS). Calibrado a
# ojo según profundidad y "ruido" de cada nivel: el 1 regala piezas seguido y
# el 6 busca a profundidad 12 sin ruido.
AI_LEVEL_ELO = {
    1: 600,  # Principiante: profundidad 1, ruido 200 cp
    2: 900,  # Novato: profundidad 2, ruido 100 cp
    3: 1200,  # Aficionado: profundidad 3, ruido 50 cp
    4: 1500,  # Club: profundidad 4, ruido 20 cp
    5: 1800,  # Fuerte: profundidad 6, sin ruido
    6: 2000,  # Experto: profundidad 12, sin ruido
}

# Elo aproximado de Stockfish según el Skill Level que usa cada nivel del menú
# (constants.STOCKFISH_SKILL: 0, 3, 6, 10, 15, 20) con poco tiempo por jugada.
STOCKFISH_LEVEL_ELO = {1: 1300, 2: 1500, 3: 1700, 4: 2000, 5: 2300, 6: 2800}

ENGINES = ("cabrechess", "stockfish")
VARIANTS = ("standard", "chess960")
RESULTS = ("win", "draw", "loss")
COLORS = ("white", "black")
SCORE = {"win": 1.0, "draw": 0.5, "loss": 0.0}


def stats_path():
    return data_dir() / "stats.json"


def empty_stats():
    return {"version": STATS_VERSION, "games": []}


# ── resultado de una partida ──
def player_result(result, player_is_white):
    """ "1-0" / "0-1" / "1/2-1/2" -> "win" / "loss" / "draw" desde el lado del
    jugador. None si la partida no terminó ("*")."""
    if result == "1/2-1/2":
        return "draw"
    if result == "1-0":
        return "win" if player_is_white else "loss"
    if result == "0-1":
        return "loss" if player_is_white else "win"
    return None


def opponent_elo(level, engine="cabrechess"):
    table = STOCKFISH_LEVEL_ELO if engine == "stockfish" else AI_LEVEL_ELO
    return table.get(level, table[3])


# ── Elo ──
def expected_score(rating, opponent):
    """Puntaje esperado (0..1) de ``rating`` contra ``opponent``."""
    return 1.0 / (1.0 + 10 ** ((opponent - rating) / 400.0))


def update_elo(rating, opponent, score, k=K_FACTOR):
    """Nuevo Elo tras una partida: R' = R + K·(S − E). score: 1, 0.5 o 0."""
    return rating + k * (score - expected_score(rating, opponent))


def elo_history(games, start=START_ELO, k=K_FACTOR):
    """Elo tras cada partida (lista, sin el inicial)."""
    rating, out = float(start), []
    for g in games:
        rating = update_elo(rating, opponent_elo(g["level"], g["engine"]), SCORE[g["result"]], k)
        out.append(rating)
    return out


def estimated_elo(games, start=START_ELO, k=K_FACTOR):
    hist = elo_history(games, start, k)
    return round(hist[-1]) if hist else start


# ── validación / carga / guardado ──
def _clean_game(g):
    """Partida válida normalizada, o None si el registro está roto."""
    if not isinstance(g, dict):
        return None
    result, level = g.get("result"), g.get("level")
    if result not in RESULTS or isinstance(level, bool) or not isinstance(level, int):
        return None
    if level not in AI_LEVEL_ELO:
        return None
    engine = g.get("engine", "cabrechess")
    color = g.get("color", "white")
    clean = {
        "date": str(g.get("date", "")),
        "result": result,
        "level": level,
        "engine": engine if engine in ENGINES else "cabrechess",
        "color": color if color in COLORS else "white",
        "time_control": str(g.get("time_control", "") or ""),
        "termination": str(g.get("termination", "") or ""),
    }
    if g.get("variant") == "chess960":
        clean["variant"] = "chess960"
    return clean


def is_chess960(game):
    return game.get("variant") == "chess960"


def _read(path):
    """(stats, corrupto). Ausente = vacío y no corrupto."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return empty_stats(), False
    except OSError:
        return empty_stats(), True
    try:
        data = json.loads(text)
    except ValueError:
        return empty_stats(), True
    if not isinstance(data, dict) or not isinstance(data.get("games"), list):
        return empty_stats(), True
    games = [c for c in (_clean_game(g) for g in data["games"]) if c is not None]
    return {"version": STATS_VERSION, "games": games}, False


def load_stats(path=None):
    """Lee stats.json. Nunca falla: ausente o roto = estadísticas vacías."""
    return _read(Path(path) if path else stats_path())[0]


def save_stats(stats, path=None):
    """Escribe stats.json de forma atómica. True si se pudo."""
    path = Path(path) if path else stats_path()
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        return False
    return True


def _set_aside(path):
    """Aparta un stats.json roto para no pisarlo (stats.json.corrupto)."""
    try:
        os.replace(path, path.with_name(path.name + ".corrupto"))
    except OSError:
        pass


def record_game(result, level, color, engine="cabrechess", time_control="", termination="", date=None, path=None,
                variant="standard"):
    """Agrega una partida terminada contra la IA. ``result`` es "win" / "draw"
    / "loss" desde el jugador. Devuelve las estadísticas actualizadas (o None
    si los datos no son válidos)."""
    path = Path(path) if path else stats_path()
    date = date or datetime.datetime.now()
    game = _clean_game(
        {
            "date": date.isoformat(timespec="seconds") if hasattr(date, "isoformat") else str(date),
            "result": result,
            "level": level,
            "engine": engine,
            "color": color,
            "time_control": time_control,
            "termination": termination,
            "variant": variant,
        }
    )
    if game is None:
        return None
    stats, corrupt = _read(path)
    if corrupt:
        _set_aside(path)
    stats["games"].append(game)
    save_stats(stats, path)
    return stats


def reset_stats(path=None):
    """Borra todas las estadísticas. True si se pudo."""
    return save_stats(empty_stats(), path)


# ── resúmenes para la pantalla ──
def _counts(games):
    c = {r: 0 for r in RESULTS}
    for g in games:
        c[g["result"]] += 1
    played = len(games)
    c["played"] = played
    c["score_pct"] = round(100 * (c["win"] + 0.5 * c["draw"]) / played) if played else 0
    return c


def summarize(stats):
    """Totales, tabla por nivel (motor propio), Stockfish aparte y Elo."""
    games = stats.get("games", [])
    own = [g for g in games if g["engine"] == "cabrechess"]
    sf = [g for g in games if g["engine"] == "stockfish"]
    by_level = {}
    for lvl in sorted(AI_LEVEL_ELO):
        row = _counts([g for g in own if g["level"] == lvl])
        row["elo"] = AI_LEVEL_ELO[lvl]
        by_level[lvl] = row
    hist = elo_history(games)
    return {
        "totals": _counts(games),
        "by_level": by_level,
        "stockfish": _counts(sf),
        "chess960": _counts([g for g in games if is_chess960(g)]),
        "elo": round(hist[-1]) if hist else START_ELO,
        "elo_peak": round(max(hist)) if hist else START_ELO,
        "provisional": len(games) < PROVISIONAL_GAMES,
        "recent": list(reversed(games[-5:])),
    }
