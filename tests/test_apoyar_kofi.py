"""Apoyar en Ko-fi: botón del menú y aviso discreto tras las partidas."""
import json

import chess

from cabrechess import settings, support


def test_should_prompt_cada_n_partidas():
    assert [n for n in range(1, 16) if support.should_prompt(n, 5)] == [5, 10, 15]
    assert support.should_prompt(1, 1)
    assert not support.should_prompt(5, 0)        # 0 = apagado
    assert not support.should_prompt(0, 5)
    assert not support.should_prompt("x", 5)


def test_open_kofi_usa_la_url_y_no_lanza():
    abiertas = []
    assert support.open_kofi(lambda url: abiertas.append(url) or True)
    assert abiertas == ["https://ko-fi.com/federicocabrera"]

    def roto(url):
        raise RuntimeError("sin navegador")
    assert support.open_kofi(roto) is False


def test_settings_por_defecto_y_saneados(tmp_path):
    cfg = settings.load_settings(tmp_path / "no-existe.json")
    assert cfg["support_prompt_every"] == 5 and cfg["support_games"] == 0
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"support_prompt_every": "abc", "support_games": -3}))
    cfg = settings.load_settings(p)
    assert cfg["support_prompt_every"] == 5 and cfg["support_games"] == 0


def test_boton_del_menu_abre_kofi(game, monkeypatch):
    abiertas = []
    monkeypatch.setattr("cabrechess.ui.open_kofi", lambda: abiertas.append(1) or True)
    game.mode = "menu"
    _label, rect = game.menu_support_button()
    game.handle_click(rect.center)
    assert abiertas == [1]
    assert "Ko-fi" in game.pgn_saved_msg
    game.draw_menu()   # se dibuja sin errores


def test_boton_del_menu_no_pisa_otros_controles(game):
    _label, rect = game.menu_support_button()
    game.stockfish_path = "x"   # con la fila extra "Rival IA"
    otros = [r for *_x, r in game.menu_main_buttons()] + [r for *_x, r in game.menu_load_buttons()]
    for *_x, options in game.menu_option_rows():
        otros += [o[1] for o in options]
    assert not any(rect.colliderect(o) for o in otros)
    assert game.screen.get_rect().contains(rect)


def test_si_no_abre_el_navegador_copia_el_link(game, monkeypatch):
    copiado = []
    monkeypatch.setattr("cabrechess.ui.open_kofi", lambda: False)
    monkeypatch.setattr("cabrechess.ui.copy_text", lambda t: copiado.append(t) or True)
    game.support_kofi()
    assert copiado == [support.KOFI_URL]
    assert "copiado" in game.pgn_saved_msg


def _terminar(game):
    game.start_game("pvp")
    for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
        game.execute_move(chess.Move.from_uci(uci))
    assert game.game_over
    game.update()


def test_aviso_cada_n_partidas_y_se_cierra(game, monkeypatch):
    monkeypatch.setattr("cabrechess.ui.save_setting", lambda *a: True)
    monkeypatch.setattr(game, "autosave_game", lambda: None)
    game.support_prompt_every, game.support_games = 2, 0
    _terminar(game)
    assert game.support_games == 1 and not game.support_prompt
    _terminar(game)
    assert game.support_games == 2 and game.support_prompt and game.game_over_panel
    game.draw_game()   # panel + aviso se dibujan sin errores
    game.game_over_time = 0   # pasar el margen anti doble click
    _strip, _apoyar, ahora_no = game.support_prompt_rects()
    game.handle_click(ahora_no.center)
    assert not game.support_prompt and game.game_over_panel   # el panel sigue


def test_aviso_apoyar_abre_kofi(game, monkeypatch):
    abiertas = []
    monkeypatch.setattr("cabrechess.ui.save_setting", lambda *a: True)
    monkeypatch.setattr("cabrechess.ui.open_kofi", lambda: abiertas.append(1) or True)
    monkeypatch.setattr(game, "autosave_game", lambda: None)
    game.support_prompt_every, game.support_games = 1, 0
    _terminar(game)
    game.game_over_time = 0
    _strip, apoyar, _later = game.support_prompt_rects()
    game.handle_click(apoyar.center)
    assert abiertas == [1] and not game.support_prompt


def test_aviso_apagado_y_esc_lo_cierra(game, monkeypatch):
    monkeypatch.setattr("cabrechess.ui.save_setting", lambda *a: True)
    monkeypatch.setattr(game, "autosave_game", lambda: None)
    game.support_prompt_every = 0
    _terminar(game)
    assert not game.support_prompt
    game.support_prompt_every = 1
    game.reset_game()
    _terminar(game)
    assert game.support_prompt
    game.close_game_over_panel()
    assert not game.support_prompt


def test_contador_se_guarda_en_settings(game, monkeypatch):
    guardados = []
    monkeypatch.setattr("cabrechess.ui.save_setting", lambda k, v: guardados.append((k, v)) or True)
    monkeypatch.setattr(game, "autosave_game", lambda: None)
    game.support_games = 7
    _terminar(game)
    assert ("support_games", 8) in guardados


def test_analisis_no_cuenta(game):
    game.start_game("analysis")
    assert game.count_finished_game() is False
