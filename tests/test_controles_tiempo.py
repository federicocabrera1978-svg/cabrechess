"""Tests de los controles de tiempo estilo Lichess (B10, parte 1)."""
import json

import pytest

from cabrechess.clock import (
    DEFAULT_TIME_CONTROL, TIME_CONTROLS, parse_time_control, time_category,
    time_control_label,
)
from cabrechess.settings import load_settings, settings_path


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    """Cada test con su propio settings.json, para no contagiar a los demás."""
    monkeypatch.setenv("CABRECHESS_DATA_DIR", str(tmp_path / "datos"))


@pytest.mark.parametrize("texto, esperado", [
    ("3+2", (180, 2)), ("1+0", (60, 0)), ("15+10", (900, 10)), (" 7+4 ", (420, 4)),
])
def test_parse_validos(texto, esperado):
    assert parse_time_control(texto) == esperado


@pytest.mark.parametrize("texto", ["", "3", "3+", "a+2", "0+2", "181+0", "3+61", "3+-1", None, 5])
def test_parse_invalidos(texto):
    assert parse_time_control(texto) is None


def test_etiqueta_ida_y_vuelta():
    for label, base, inc in TIME_CONTROLS:
        assert time_control_label(base, inc) == label
        assert parse_time_control(label) == (base, inc)
    assert time_control_label(90, 0) == "1.5+0"


@pytest.mark.parametrize("base, inc, cat", [
    (60, 0, "Bala"), (120, 1, "Bala"), (180, 2, "Blitz"), (300, 3, "Blitz"),
    (600, 5, "Rápida"), (900, 10, "Rápida"), (1800, 0, "Clásica"),
])
def test_categorias_como_lichess(base, inc, cat):
    assert time_category(base, inc) == cat


def test_por_defecto_3_mas_2(game):
    assert DEFAULT_TIME_CONTROL == "3+2"
    assert (game.time_selected, game.time_increment) == (180, 2)


def fila_tiempo(game):
    return next(r for r in game.menu_option_rows_with_setters() if r[0] == "Tiempo:")


def test_menu_muestra_los_seis_controles(game):
    _l, _y, _c, options, _s = fila_tiempo(game)
    assert [o[0] for o in options] == [label for label, _b, _i in TIME_CONTROLS]
    assert sum(o[2] for o in options) == 1          # uno solo seleccionado
    # Los botones no se pisan y entran en la ventana
    from cabrechess.constants import WINDOW_W
    rects = [o[1] for o in options]
    assert all(a.right < b.left for a, b in zip(rects, rects[1:]))
    assert rects[-1].right <= WINDOW_W


def test_elegir_control_cambia_reloj_e_incremento(game):
    _l, _y, _c, options, setter = fila_tiempo(game)
    value = next(o[3] for o in options if o[0] == "10+5")
    setter(value)
    assert (game.time_selected, game.time_increment) == (600, 5)
    game.start_game("pvp")
    assert game.time_white == game.time_black == 600
    game.execute_move(game.board.parse_san("e4"))
    assert game.time_white == 605
    assert game.time_control() == "600+5"          # PGN: segundos+segundos
    assert "Rápida 10+5" in game.time_control_text()


def test_bala_sin_incremento(game):
    game.set_time_control((60, 0))
    game.start_game("pvp")
    game.execute_move(game.board.parse_san("e4"))
    assert game.time_white == 60
    assert "sin incremento" in game.time_control_text()


def test_el_control_se_recuerda(game):
    game.set_time_control((300, 3))
    data = json.loads(settings_path().read_text(encoding="utf-8"))
    assert data["time_control"] == "5+3"
    assert load_settings()["time_control"] == "5+3"
    import cabrechess
    otro = cabrechess.CabreChess()
    assert (otro.time_selected, otro.time_increment) == (300, 3)


def test_personalizado_desde_settings(game):
    game.set_time_control((420, 4))                  # "7+4", no es preset
    import cabrechess
    otro = cabrechess.CabreChess()
    options = fila_tiempo(otro)[3]
    assert options[-1][0] == "7+4" and options[-1][2]
    assert len(options) == len(TIME_CONTROLS) + 1


def test_setting_invalido_vuelve_al_defecto(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"time_control": "9000+1"}), encoding="utf-8")
    assert load_settings(p)["time_control"] == "3+2"


def test_set_time_control_rechaza_basura(game):
    assert not game.set_time_control("x")
    assert not game.set_time_control((0, 2))
    assert (game.time_selected, game.time_increment) == (180, 2)
