"""Menú renovado (A7): pantalla de Ajustes y transiciones suaves."""
import json

import pygame

from cabrechess import settings, transitions
from cabrechess.constants import BOARD_THEMES


def _click_option(game, label, value):
    for lbl, _y, _acc, options, _setter in game.settings_rows():
        if lbl == label:
            for _t, rect, _sel, v in options:
                if v == value:
                    game.handle_click(rect.center)
                    return
    raise AssertionError(f"no está la opción {label}={value}")


def _cfg():
    return json.loads(settings.settings_path().read_text(encoding="utf-8"))


def test_fade_alpha_baja_hasta_cero():
    assert transitions.fade_alpha(0) == transitions.TRANSITION_START_ALPHA
    vals = [transitions.fade_alpha(t / 100) for t in range(0, 30)]
    assert vals == sorted(vals, reverse=True)
    assert transitions.fade_alpha(transitions.TRANSITION_SECONDS) == 0
    assert transitions.fade_alpha(5) == 0
    assert transitions.fade_alpha(0.1, duration=0) == 0


def test_player_color_se_guarda_y_se_sanea(tmp_path):
    assert settings.load_settings(tmp_path / "x.json")["player_color"] == "white"
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"player_color": "verde"}))
    assert settings.load_settings(p)["player_color"] == "white"
    p.write_text(json.dumps({"player_color": "black"}))
    assert settings.load_settings(p)["player_color"] == "black"


def test_boton_ajustes_abre_y_esc_vuelve(game):
    game.mode = "menu"
    game.handle_click(game.menu_settings_button()[1].center)
    assert game.mode == "settings"
    game.draw()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
    assert game.handle_events()
    assert game.mode == "menu"
    game.mode = "settings"
    game.handle_click(game.settings_back_button()[1].center)
    assert game.mode == "menu"


def test_ajustes_cambian_y_se_recuerdan(game):
    game.mode = "settings"
    _click_option(game, "Tablero", "verde")
    assert game.board_theme == "verde" and _cfg()["board_theme"] == "verde"
    _click_option(game, "Sonido", False)
    assert not game.sound.enabled and _cfg()["sound"] is False
    _click_option(game, "Sonido", True)
    assert game.sound.enabled
    _click_option(game, "Color contra la IA", "black")
    assert game.player_color_choice == "black" and _cfg()["player_color"] == "black"
    _click_option(game, "Aviso de Ko-fi", 0)
    assert game.support_prompt_every == 0 and _cfg()["support_prompt_every"] == 0
    game.draw_settings()   # se dibuja sin errores


def test_color_del_menu_tambien_se_recuerda(game):
    game.mode = "menu"
    for lbl, _y, _acc, options in game.menu_option_rows():
        if lbl.startswith("Color"):
            rect = next(r for _t, r, _s, v in options if v == "random")
            game.handle_click(rect.center)
    assert game.player_color_choice == "random"
    assert _cfg()["player_color"] == "random"


def test_controles_de_ajustes_no_se_pisan(game):
    game.stockfish_path = "x"    # con la fila "Rival IA"
    rects = [o[1] for *_x, options, _s in game.settings_rows() for o in options]
    rects += [game.settings_back_button()[1], game.settings_preview_rect()]
    screen = game.screen.get_rect()
    for i, a in enumerate(rects):
        assert screen.contains(a)
        assert not any(a.colliderect(b) for b in rects[i + 1:])
    assert len(game.settings_rows()) == 5
    assert {o[3] for o in game.settings_rows()[0][3]} == set(BOARD_THEMES)


def test_boton_ajustes_del_menu_no_pisa_otros(game):
    rect = game.menu_settings_button()[1]
    otros = [r for *_x, r in game.menu_main_buttons()] + [r for *_x, r in game.menu_load_buttons()]
    otros.append(game.menu_support_button()[1])
    for *_x, options in game.menu_option_rows():
        otros += [o[1] for o in options]
    assert not any(rect.colliderect(o) for o in otros)
    assert game.screen.get_rect().contains(rect)


def test_transicion_al_cambiar_de_pantalla(game):
    game.mode = "menu"
    assert game.draw_transition(now=100.0) == 0          # primera pantalla: sin velo
    game.mode = "settings"
    assert game.draw_transition(now=100.0) == transitions.TRANSITION_START_ALPHA
    mid = game.draw_transition(now=100.0 + transitions.TRANSITION_SECONDS / 2)
    assert 0 < mid < transitions.TRANSITION_START_ALPHA
    assert game.draw_transition(now=101.0) == 0
    assert game.transition_start is None
    game.mode = "pvp"
    game.draw_transition(now=200.0)
    game.mode = "vsai"                                    # entre partidas no hay velo
    assert game.draw_transition(now=200.5) == 0
