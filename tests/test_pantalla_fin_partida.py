"""Ventana redimensionable (escalado/coordenadas), panel de fin de partida,
revisión de jugadas y guardado de PGN con ruta por defecto."""
import datetime
import io

import chess
import chess.pgn
import pygame

from cabrechess import pgn as pgn_mod
from cabrechess.constants import WINDOW_H, WINDOW_W
from cabrechess.display import MIN_H, MIN_W, clamp_window_size, compute_viewport, window_to_logical


# ─── Escalado / coordenadas ────────────────────────────────────────────────────
def test_viewport_tamano_original():
    assert compute_viewport(WINDOW_W, WINDOW_H) == (1.0, 0, 0, WINDOW_W, WINDOW_H)


def test_viewport_letterbox_horizontal():
    # Ventana más ancha: barras a los costados, escala por alto
    scale, x, y, w, h = compute_viewport(2200, 780)
    assert scale == 1.0 and y == 0 and (w, h) == (WINDOW_W, WINDOW_H)
    assert x == (2200 - WINDOW_W) // 2


def test_viewport_letterbox_vertical_y_proporcion():
    scale, x, y, w, h = compute_viewport(1920, 1920)
    assert x == 0 and w == 1920
    assert abs(w / h - WINDOW_W / WINDOW_H) < 0.01
    assert y == (1920 - h) // 2


def test_mapeo_de_mouse_ida_y_vuelta():
    vp = compute_viewport(1920, 1080)
    scale, x0, y0, _, _ = vp
    for lx, ly in [(0, 0), (60, 70), (700, 400), (WINDOW_W - 1, WINDOW_H - 1)]:
        wx, wy = x0 + (lx + 0.5) * scale, y0 + (ly + 0.5) * scale
        assert window_to_logical((wx, wy), vp) == (lx, ly)


def test_mouse_en_las_barras_negras():
    vp = compute_viewport(2200, 780)
    assert window_to_logical((5, 300), vp) == (-1, -1)
    assert window_to_logical((2195, 300), vp) == (-1, -1)


def test_tamano_minimo():
    assert clamp_window_size(300, 200) == (MIN_W, MIN_H)
    assert clamp_window_size(1500, 900) == (1500, 900)


def test_la_ventana_es_redimensionable(game):
    assert pygame.display.get_surface().get_flags() & pygame.RESIZABLE
    assert game.screen.get_size() == (WINDOW_W, WINDOW_H)
    game.present()   # no debe fallar


# ─── Fin de partida ────────────────────────────────────────────────────────────
def _mate_del_loco(game):
    game.mode = "pvp"
    game.reset_game()
    for san in ["f3", "e5", "g4", "Qh4#"]:
        game.execute_move(game.board.parse_san(san))
    game.sync_game_over_panel()
    game.game_over_time = 0      # saltear el período de gracia de los clicks


def test_panel_aparece_al_terminar(game):
    _mate_del_loco(game)
    assert game.game_over and game.game_over_panel
    labels = [b[0] for b in game.game_over_buttons()]
    assert labels == ["Guardar PGN", "Revisar / Analizar", "Nueva partida", "Cerrar"]


def test_cerrar_panel_deja_ver_el_tablero(game):
    _mate_del_loco(game)
    rect = dict((b[0], b[2]) for b in game.game_over_buttons())["Cerrar"]
    game.handle_click(rect.center)
    assert game.game_over and not game.game_over_panel
    game.sync_game_over_panel()          # no vuelve a abrirse solo
    assert not game.game_over_panel
    game.draw()                          # dibuja tablero + barra de revisión


def test_esc_cierra_el_panel(game):
    _mate_del_loco(game)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
    assert game.handle_events()
    assert not game.game_over_panel and game.mode == "pvp"


def test_tablero_bloqueado_con_partida_terminada(game):
    _mate_del_loco(game)
    game.close_game_over_panel()
    fen = game.board.fen()
    game.handle_click(game.center_of_sq(chess.E2))
    assert game.selected_sq is None and game.board.fen() == fen


def test_revisar_partida(game):
    _mate_del_loco(game)
    game.start_review()
    assert not game.game_over_panel and game.review_index is None
    game.review_step(-1)
    assert game.review_index == 3
    assert game.review_board().fen() == chess.Board(
        "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq g3 0 2").fen()
    game.review_step(to=0)
    assert game.review_board().fen() == chess.Board().fen()
    game.draw()                               # dibuja la posición revisada
    assert len(game.board.move_stack) == 4    # el tablero real no cambia
    game.review_step(10)
    assert game.review_index is None
    # Botón "Resultado" reabre el panel
    rect = dict(game.review_buttons())["result"]
    game.handle_click(rect.center)
    assert game.game_over_panel


def test_nueva_partida_desde_el_panel(game):
    _mate_del_loco(game)
    rect = dict((b[0], b[2]) for b in game.game_over_buttons())["Nueva partida"]
    game.handle_click(rect.center)
    assert not game.game_over and not game.game_over_panel
    assert game.board.fen() == chess.Board().fen()


# ─── Guardar PGN ───────────────────────────────────────────────────────────────
def test_default_pgn_path(tmp_path):
    p = pgn_mod.default_pgn_path(now=datetime.datetime(2026, 10, 20, 22, 5, 9), base_dir=tmp_path)
    assert p == tmp_path / "CabreChess_20261020_220509.pgn"


def test_guardar_sin_tkinter_usa_ruta_por_defecto(game, monkeypatch, tmp_path):
    _mate_del_loco(game)
    monkeypatch.setattr(game, "ask_pgn_filename", lambda date_str: None)
    monkeypatch.setattr("cabrechess.ui.default_pgn_path", lambda: tmp_path / "sub" / "partida.pgn")
    path = game.save_pgn()
    assert path == tmp_path / "sub" / "partida.pgn" and path.is_file()
    parsed = chess.pgn.read_game(io.StringIO(path.read_text(encoding="utf-8")))
    assert parsed.headers["Result"] == "0-1"
    assert "Guardado" in game.pgn_saved_msg


def test_guardar_cancelado_no_escribe(game, monkeypatch, tmp_path):
    _mate_del_loco(game)
    monkeypatch.setattr(game, "ask_pgn_filename", lambda date_str: "")
    monkeypatch.setattr("cabrechess.ui.default_pgn_path", lambda: tmp_path / "x.pgn")
    assert game.save_pgn() is None
    assert not (tmp_path / "x.pgn").exists()


def test_guardar_desde_el_panel(game, monkeypatch, tmp_path):
    _mate_del_loco(game)
    target = tmp_path / "elegido.pgn"
    monkeypatch.setattr(game, "ask_pgn_filename", lambda date_str: str(target))
    rect = dict((b[0], b[2]) for b in game.game_over_buttons())["Guardar PGN"]
    game.handle_click(rect.center)
    assert target.is_file()
    assert game.game_over_panel          # el panel sigue abierto tras guardar


def test_guardar_sin_jugadas(game):
    game.mode = "pvp"
    game.reset_game()
    assert game.save_pgn() is None
    assert "No hay movimientos" in game.pgn_saved_msg


def test_resize_y_pantalla_completa(game):
    game.on_resize(300, 200)                       # menor al mínimo
    assert pygame.display.get_surface().get_size() == (MIN_W, MIN_H)
    game.on_resize(1400, 900)
    assert game.windowed_size == (1400, 900)
    game.toggle_fullscreen()
    assert game.fullscreen
    game.present()
    game.toggle_fullscreen()
    assert not game.fullscreen
    assert pygame.display.get_surface().get_flags() & pygame.RESIZABLE
