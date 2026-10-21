# SPDX-License-Identifier: GPL-3.0-or-later
"""Base de datos local de partidas terminadas (SQLite, sin servidor)."""
import datetime
import sqlite3
from pathlib import Path

from .settings import data_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    played_at    TEXT NOT NULL,
    mode         TEXT NOT NULL,
    white        TEXT NOT NULL,
    black        TEXT NOT NULL,
    result       TEXT NOT NULL,
    termination  TEXT NOT NULL,
    eco          TEXT NOT NULL DEFAULT '',
    opening      TEXT NOT NULL DEFAULT '',
    time_control TEXT NOT NULL DEFAULT '-',
    num_moves    INTEGER NOT NULL DEFAULT 0,
    pgn          TEXT NOT NULL
)
"""
COLUMNS = ("id", "played_at", "mode", "white", "black", "result", "termination",
           "eco", "opening", "time_control", "num_moves", "pgn")


def default_db_path():
    return data_dir() / "partidas.db"


class GameDB:
    """Acceso a partidas.db. path=":memory:" sirve para tests."""

    def __init__(self, path=None):
        self.path = str(path or default_db_path())
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        with self.conn:
            self.conn.execute(SCHEMA)

    def close(self):
        self.conn.close()

    def add_game(self, *, mode, white, black, result, termination, pgn,
                 eco="", opening="", time_control="-", num_moves=0, played_at=None):
        played_at = played_at or datetime.datetime.now().isoformat(timespec="seconds")
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO games (played_at, mode, white, black, result, termination,"
                " eco, opening, time_control, num_moves, pgn)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (played_at, mode, white, black, result, termination,
                 eco or "", opening or "", time_control, num_moves, pgn))
        return cur.lastrowid

    def list_games(self, limit=500):
        rows = self.conn.execute(
            "SELECT * FROM games ORDER BY played_at DESC, id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]

    def get_game(self, game_id):
        row = self.conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        return dict(row) if row else None

    def delete_game(self, game_id):
        with self.conn:
            cur = self.conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
        return cur.rowcount > 0

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
