# SPDX-License-Identifier: GPL-3.0-or-later
"""B4: Stockfish opcional como rival en "Jugar contra IA".

Se prueba con un motor UCI de mentira (tests/fake_uci.py) para no depender de
tener Stockfish instalado."""
import sys
import time
from pathlib import Path

import chess
import pytest

from cabrechess.constants import STOCKFISH_SKILL
from cabrechess.settings import load_settings

FAKE = Path(__file__).with_name("fake_uci.py")


def fake_engine_cmd(tmp_path):
    """Ejecutable que lanza el motor falso (python-chess acepta lista de args)."""
    return [sys.executable, str(FAKE)]


def wait_ai(game, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        with game.ai_lock:
            ready = game.ai_move_ready
        if ready:
            game.ai_move()
            return True
        time.sleep(0.02)
    return False


def test_skill_level_crece_con_el_nivel():
    skills = [STOCKFISH_SKILL[n] for n in range(1, 7)]
    assert skills == sorted(skills) and skills[0] == 0 and skills[-1] == 20


def test_settings_ai_engine_por_defecto_y_valor_invalido(tmp_path):
    p = tmp_path / "settings.json"
    assert load_settings(p)["ai_engine"] == "cabrechess"
    p.write_text('{"ai_engine": "lc0"}', encoding="utf-8")
    assert load_settings(p)["ai_engine"] == "cabrechess"
    p.write_text('{"ai_engine": "stockfish"}', encoding="utf-8")
    assert load_settings(p)["ai_engine"] == "stockfish"


def test_sin_ruta_no_hay_fila_de_rival_ni_stockfish(game):
    assert game.stockfish_path == ""
    labels = [r[0] for r in game.menu_option_rows()]
    assert "Rival IA:" not in labels
    game.set_ai_engine("stockfish")         # sin ruta se ignora
    assert game.ai_engine == "cabrechess"
    game.player_color_choice = "white"
    game.start_game("vsai")
    assert not game.uses_stockfish()


def test_con_ruta_aparece_la_fila_y_el_click_elige_stockfish(game):
    game.stockfish_path = "stockfish"
    rows = game.menu_option_rows()
    assert [r[0] for r in rows][-1] == "Rival IA:"
    _lbl, _y, _acc, options = rows[-1]
    sf_rect = next(rect for text, rect, _sel, _v in options if text == "Stockfish")
    game.handle_menu_click(sf_rect.center)
    assert game.ai_engine == "stockfish"
    assert load_settings()["ai_engine"] == "stockfish"
    # Las filas no se pisan entre sí
    ys = [r[1] for r in game.menu_option_rows()]
    assert ys == sorted(set(ys))
    game.handle_menu_click(next(r for t, r, _s, _v in options if t == "CabreChess").center)
    assert game.ai_engine == "cabrechess"


def test_stockfish_juega_contra_el_humano(game, tmp_path, monkeypatch):
    log = tmp_path / "uci.log"
    monkeypatch.setenv("FAKE_UCI_LOG", str(log))
    game.stockfish_path = fake_engine_cmd(tmp_path)
    game.ai_engine = "stockfish"
    game.ai_level = 2
    game.player_color_choice = "black"      # la IA (blancas) arranca
    game.start_game("vsai")
    try:
        assert game.uses_stockfish()
        assert game.mode_label().startswith("vs Stockfish")
        assert wait_ai(game)
        # El motor falso juega la primera jugada legal en orden UCI: a2a3
        assert game.board.move_stack[0] == chess.Move.from_uci("a2a3")
        assert f"Skill Level value {STOCKFISH_SKILL[2]}" in log.read_text(encoding="utf-8")
        white, _black = game.player_names()
        assert white == "Stockfish (nivel 2)"
        assert game.ai_name() == "Stockfish"
        game.draw()                     # panel del jugador con el nombre nuevo
    finally:
        game.close_stockfish()


def test_si_stockfish_falla_juega_el_motor_propio(game, tmp_path):
    game.stockfish_path = str(tmp_path / "no-existe.exe")
    game.ai_engine = "stockfish"
    game.ai_level = 1
    game.player_color_choice = "black"
    game.start_game("vsai")
    assert wait_ai(game)
    assert len(game.board.move_stack) == 1          # igual movió
    assert game.sf_failed and not game.uses_stockfish()
    assert "Stockfish" in game.pgn_saved_msg
    assert game.player_names()[0] == "CabreChess AI"


@pytest.mark.parametrize("level", [1, 6])
def test_tope_de_tiempo_se_respeta_con_stockfish(game, tmp_path, level):
    game.stockfish_path = fake_engine_cmd(tmp_path)
    game.ai_engine = "stockfish"
    game.ai_level = level
    game.player_color_choice = "black"
    t0 = time.time()
    game.start_game("vsai")
    try:
        assert wait_ai(game)
        assert time.time() - t0 < 10
    finally:
        game.close_stockfish()
