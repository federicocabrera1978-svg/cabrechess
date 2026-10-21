"""Tests de los módulos puros (reloj, PGN) y de la ubicación de assets."""
import datetime

import chess

from cabrechess import sprites
from cabrechess.clock import flag_fall_message, format_clock
from cabrechess.pgn import build_pgn, game_result


def test_format_clock():
    assert format_clock(180) == "3:00"
    assert format_clock(61.9) == "1:01"
    assert format_clock(59.95) == "0:59.9"
    assert format_clock(0) == "0:00.0"


def test_flag_fall_message():
    # Al rival le alcanza el material: gana
    board = chess.Board("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")
    assert "Ganan las blancas por tiempo" in flag_fall_message(board, chess.BLACK)
    # Rival con rey solo: tablas
    assert "Tablas por tiempo" in flag_fall_message(board, chess.WHITE)


def test_game_result():
    assert game_result(chess.Board()) == "*"
    assert game_result(chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")) == "1/2-1/2"


def test_build_pgn_headers():
    text, date_str = build_pgn(chess.Board(), ["e4", "e5"], "pvp", "A", "B",
                               now=datetime.datetime(2026, 10, 20))
    assert date_str == "2026.10.20"
    assert '[White "A"]' in text and '[Black "B"]' in text
    assert "1. e4 e5 *" in text


def test_assets_dentro_del_paquete():
    assert (sprites.ASSETS_DIR / "pieces" / "cburnett" / "wK.png").is_file()
    assert (sprites.ASSETS_DIR / "logo" / "cabrechess_64.png").is_file()
    assert sprites.ASSETS_DIR.parent.name == "cabrechess"
