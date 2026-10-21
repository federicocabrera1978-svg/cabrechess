"""Todos los finales de partida terminan en el panel nuevo (nunca en el menú),
y ajustes de ventana para Windows."""
import time

import chess
import pygame

from cabrechess.display import MIN_H, MIN_W, initial_window_size
from cabrechess.constants import WINDOW_H, WINDOW_W


def _setup(game, fen, mode="pvp"):
    game.mode = mode
    game.reset_game()
    game.board = chess.Board(fen)


def _fin(game):
    game.update()                 # el loop real muestra el panel en update()
    assert game.game_over, "la partida debería haber terminado"
    assert game.game_over_panel
    assert game.mode != "menu"


def test_mate(game):
    _setup(game, "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
    game.execute_move(chess.Move.from_uci("a1a8"))
    _fin(game)
    assert "¡Jaque mate! Ganan las blancas" in game.game_over_msg


def test_ahogado(game):
    _setup(game, "7k/8/6Q1/8/8/8/8/K7 w - - 0 1")
    game.execute_move(chess.Move.from_uci("g6f7"))
    _fin(game)
    assert "Tablas por ahogado" in game.game_over_msg


def test_material_insuficiente(game):
    _setup(game, "7k/8/8/8/8/8/1q6/K7 w - - 0 1")
    game.execute_move(chess.Move.from_uci("a1b2"))
    _fin(game)
    assert "Tablas por material insuficiente" in game.game_over_msg


def test_triple_repeticion(game):
    _setup(game, "4k3/8/8/8/8/8/8/4K2R w - - 0 1")
    for uci in ["e1f1", "e8f8", "f1e1", "f8e8"] * 2:
        if game.game_over:
            break
        game.execute_move(chess.Move.from_uci(uci))
    _fin(game)
    assert "Tablas por triple repetición" in game.game_over_msg


def test_regla_50_movimientos(game):
    _setup(game, "4k3/8/8/8/8/8/8/R3K3 w - - 99 80")
    game.execute_move(chess.Move.from_uci("a1a2"))
    _fin(game)
    assert "Tablas por la regla de 50 movimientos" in game.game_over_msg


def test_bandera(game):
    _setup(game, "4k3/8/8/8/8/8/8/3QK3 b - - 0 1")
    game.use_timer = True
    game.time_black = 0.01
    game.time_last = time.time() - 1
    game.update()
    _fin(game)
    assert "Ganan las blancas por tiempo" in game.game_over_msg


def test_bandera_de_la_ia_cancela_la_busqueda(game):
    _setup(game, chess.STARTING_FEN, mode="vsai")
    game.ai_color = chess.WHITE
    game.ai_thinking = True
    game.use_timer = True
    game.time_white = 0.01
    game.time_last = time.time() - 1
    game.update()
    _fin(game)
    assert not game.ai_thinking


def test_la_ia_da_mate(game):
    _setup(game, "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq g3 0 2", mode="vsai")
    game.ai_color = chess.BLACK
    game.ai_result_move = chess.Move.from_uci("d8h4")
    game.ai_move()
    _fin(game)


def test_esc_dos_veces_no_borra_la_partida(game):
    _setup(game, "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
    game.execute_move(chess.Move.from_uci("a1a8"))
    game.update()
    for _ in range(3):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
        game.handle_events()
    assert game.mode == "pvp" and game.game_over
    assert len(game.board.move_stack) == 1


def test_click_inmediato_no_toca_el_panel(game):
    _setup(game, "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
    game.execute_move(chess.Move.from_uci("a1a8"))
    game.update()
    rect = dict((b[0], b[2]) for b in game.game_over_buttons())["Nueva partida"]
    game.handle_click(rect.center)            # dentro del período de gracia
    assert game.game_over and game.game_over_panel


def test_tamano_inicial_segun_escritorio():
    w, h = initial_window_size((1920, 1080))
    assert h <= 1080 * 0.85 + 1 and abs(w / h - WINDOW_W / WINDOW_H) < 0.01
    assert initial_window_size((800, 600)) == (MIN_W, MIN_H)


def test_windowsizechanged(game):
    pygame.event.post(pygame.event.Event(pygame.WINDOWSIZECHANGED, x=300, y=200))
    game.handle_events()
    assert pygame.display.get_surface().get_size() == (MIN_W, MIN_H)


def test_pantalla_completa_usa_el_escritorio(game):
    game.toggle_fullscreen()
    assert pygame.display.get_surface().get_size() == game.desktop_size()
    game.toggle_fullscreen()
