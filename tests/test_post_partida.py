"""Después del final: deshacer no toca la partida (ni relojes ni resultado),
solo navega la revisión; ECO visible en la revisión."""
import time

import chess
import pygame


def _terminar(game, mode="pvp"):
    game.start_game(mode)
    if mode == "vsai":
        game.cancel_ai_search()
    for san in ["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6", "Qxf7#"]:
        game.execute_move(game.board.parse_san(san))
    game.update()
    game.game_over_time = 0
    assert game.game_over and game.game_over_panel


def _foto(game):
    return (game.board.fen(), len(game.board.move_stack), game.game_over,
            game.game_over_msg, game.time_white, game.time_black,
            list(game.move_history_san))


def test_deshacer_tras_el_final_no_deshace(game):
    _terminar(game)
    antes = _foto(game)
    game.undo_move()
    game.update()
    assert _foto(game) == antes
    assert game.review_index == 6          # retrocedió en la revisión


def test_relojes_congelados(game):
    _terminar(game)
    tw, tb = game.time_white, game.time_black
    game.time_last = time.time() - 30       # aunque pase el tiempo
    for _ in range(3):
        game.undo_move()
        game.update()
    assert (game.time_white, game.time_black) == (tw, tb)


def test_ctrl_z_y_boton_navegan(game):
    _terminar(game)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z, mod=pygame.KMOD_CTRL))
    game.handle_events()
    assert game.review_index == 6 and game.game_over
    # botón deshacer del panel lateral (tercer botón)
    from cabrechess.constants import BOARD_SIZE, BOARD_Y, PANEL_W, PANEL_X
    bw = (PANEL_W - 20) // 5
    game.handle_click((PANEL_X + 5 + 2 * bw + 5, BOARD_Y + BOARD_SIZE - 42 + 10))
    assert game.review_index == 5
    assert len(game.board.move_stack) == 7


def test_navegacion_completa(game):
    _terminar(game)
    for _ in range(20):
        game.undo_move()
    assert game.review_index == 0
    assert game.review_board().fen() == chess.Board().fen()
    game.review_step(3)
    assert game.review_index == 3
    game.review_step(99)
    assert game.review_index is None        # posición final
    game.draw()


def test_vs_ia_tampoco_deshace(game):
    game.player_color_choice = "white"
    _terminar(game, mode="vsai")
    antes = _foto(game)
    game.undo_move()
    assert _foto(game) == antes


def test_deshacer_en_juego_sigue_funcionando(game):
    game.start_game("pvp")
    game.execute_move(game.board.parse_san("e4"))
    game.undo_move()
    assert game.board.move_stack == []


def test_eco_visible_en_revision(game):
    _terminar(game)
    final = game.opening_text(400)
    game.review_step(to=2)                  # 1.e4 e5
    seen = {}
    orig = game.opening_text
    def spy(max_w):
        seen["txt"] = orig(max_w)
        return seen["txt"]
    game.opening_text = spy
    game.draw()
    assert seen.get("txt"), "la apertura debe mostrarse en la revisión"
    assert final
