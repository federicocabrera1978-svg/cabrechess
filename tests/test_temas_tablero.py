"""Temas de tablero: colores, tecla T y preferencia en settings.json."""
import json

import pygame

from cabrechess.constants import BOARD_THEMES, DEFAULT_THEME, SQUARE_SIZE
from cabrechess.settings import load_settings, settings_path


def test_temas_disponibles_y_por_defecto():
    assert list(BOARD_THEMES)[0] == DEFAULT_THEME == "marron"
    assert {"marron", "azul", "verde", "gris"} <= set(BOARD_THEMES)
    for nombre, clara, oscura in BOARD_THEMES.values():
        assert nombre and clara != oscura


def test_tema_invalido_en_settings_vuelve_al_defecto(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"board_theme": "rosa"}), encoding="utf-8")
    assert load_settings(p)["board_theme"] == DEFAULT_THEME
    p.write_text(json.dumps({"board_theme": "azul"}), encoding="utf-8")
    assert load_settings(p)["board_theme"] == "azul"


def test_tablero_se_pinta_con_el_tema(game):
    for key, (_, clara, oscura) in BOARD_THEMES.items():
        assert game.set_board_theme(key, save=False)
        # a8 (arriba a la izquierda en la superficie) es clara; b8 oscura
        assert game.board_surf.get_at((2, 2))[:3] == clara
        assert game.board_surf.get_at((SQUARE_SIZE + 2, 2))[:3] == oscura
    assert game.set_board_theme("inexistente", save=False) is False


def test_tecla_t_cicla_y_guarda(game):
    game.set_board_theme(DEFAULT_THEME, save=False)
    keys = list(BOARD_THEMES)
    vistos = [game.cycle_board_theme() for _ in keys]
    assert vistos == keys[1:] + keys[:1]
    assert json.loads(settings_path().read_text(encoding="utf-8"))["board_theme"] == DEFAULT_THEME
    game.cycle_board_theme()
    assert load_settings()["board_theme"] == keys[1]
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t, mod=0))
    game.handle_events()
    assert game.board_theme == keys[2]
