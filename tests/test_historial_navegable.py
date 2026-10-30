"""Historial navegable (B8): clic en una jugada, rueda del mouse y copiar
FEN/PGN al portapapeles."""
import random

import chess
import pygame

from cabrechess import clipboard


def _tranquila(board, move):
    """Jugada que no da jaque, no captura y no termina la partida."""
    if board.gives_check(move) or board.is_capture(move):
        return False
    b = board.copy()
    b.push(move)
    return not b.is_game_over(claim_draw=False)


def _partida_larga(game, plies=60, terminar=True):
    game.start_game("pvp")
    rng = random.Random(7)
    for _ in range(plies):
        moves = [m for m in game.board.legal_moves if _tranquila(game.board, m)]
        game.execute_move(rng.choice(moves or list(game.board.legal_moves)))
        if game.game_over:
            break
    if terminar and not game.game_over:
        game.resign()
    game.update()
    game.game_over_time = 0
    game.game_over_panel = False


def test_clic_en_jugada_muestra_esa_posicion(game):
    _partida_larga(game, plies=10)
    rects = dict(game.history_move_rects())
    assert 3 in rects
    assert game.handle_click(rects[3].center) is None
    assert game.review_index == 4
    esperado = chess.Board()
    for m in game.board.move_stack[:4]:
        esperado.push(m)
    assert game.displayed_board().fen() == esperado.fen()
    # la partida no cambia
    assert game.game_over


def test_clic_en_la_ultima_vuelve_a_la_posicion_final(game):
    _partida_larga(game, plies=10)
    game.review_step(to=0)
    ultimo = len(game.move_history_san) - 1
    rect = dict(game.history_move_rects())[ultimo]
    game.handle_click(rect.center)
    assert game.review_index is None


def test_clic_en_historial_no_hace_nada_con_partida_en_curso(game):
    game.start_game("pvp")
    for san in ["e4", "e5", "Nf3"]:
        game.execute_move(game.board.parse_san(san))
    rect = dict(game.history_move_rects())[0]
    assert not game.handle_history_click(rect.center)
    assert game.review_index is None


def test_rueda_del_mouse_scrollea_y_vuelve_al_auto(game):
    _partida_larga(game, plies=70)
    game.draw_side_panel()
    visibles, total = game.history_rows()
    assert total > visibles
    final = game.history_scroll
    assert final > 0                      # auto-scroll: se ve la última jugada
    game.scroll_history(3)                # rueda hacia arriba
    game.draw_side_panel()
    assert game.history_scroll == max(0, final - 3)
    game.scroll_history(100)
    game.draw_side_panel()
    assert game.history_scroll == 0
    game.scroll_history(-1000)
    game.draw_side_panel()
    assert game.history_scroll == total - visibles
    # al cambiar la jugada activa vuelve el auto-scroll
    game.scroll_history(100)
    game.review_step(-1)
    game.draw_side_panel()
    assert game.history_scroll_manual is None


def test_evento_mousewheel_sobre_la_lista(game, monkeypatch):
    _partida_larga(game, plies=70)
    game.draw_side_panel()
    antes = game.history_scroll
    clip, _rh, _top = game.history_layout()
    monkeypatch.setattr(game, "mouse_pos", lambda: clip.center)
    pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=2))
    game.handle_events()
    game.draw_side_panel()
    assert game.history_scroll == max(0, antes - 2)


def test_jugadas_clickeables_quedan_dentro_de_la_lista(game):
    _partida_larga(game, plies=70)
    game.draw_side_panel()
    clip, _rh, _top = game.history_layout()
    rects = game.history_move_rects()
    assert rects
    assert all(clip.contains(r) for _p, r in rects)


def test_copiar_fen_de_la_posicion_vista(game, monkeypatch):
    copiado = []
    monkeypatch.setattr("cabrechess.ui.copy_text", lambda t: copiado.append(t) or True)
    _partida_larga(game, plies=10)
    game.review_step(to=2)
    fen = game.copy_fen()
    assert copiado == [fen] == [game.review_board().fen()]
    assert "FEN copiado" in game.pgn_saved_msg


def test_tecla_c_y_shift_c(game, monkeypatch):
    copiado = []
    monkeypatch.setattr("cabrechess.ui.copy_text", lambda t: copiado.append(t) or True)
    game.start_game("pvp")
    for san in ["e4", "e5"]:
        game.execute_move(game.board.parse_san(san))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c, mod=0))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c, mod=pygame.KMOD_SHIFT))
    game.handle_events()
    assert copiado[0] == game.board.fen()
    assert "1. e4 e5" in copiado[1] and "[Event" in copiado[1]


def test_copiar_pgn_sin_jugadas(game, monkeypatch):
    monkeypatch.setattr("cabrechess.ui.copy_text", lambda t: True)
    game.start_game("pvp")
    assert game.copy_pgn() is None
    assert "No hay movimientos" in game.pgn_saved_msg


def test_portapapeles_que_falla_avisa(game, monkeypatch):
    monkeypatch.setattr("cabrechess.ui.copy_text", lambda t: False)
    game.start_game("pvp")
    assert game.copy_fen() is None
    assert "portapapeles" in game.pgn_saved_msg


def test_copy_text_prueba_el_siguiente_metodo():
    llamados = []

    def roto(t):
        llamados.append("roto")
        raise RuntimeError("sin portapapeles")

    def bueno(t):
        llamados.append(t)
        return True

    assert clipboard.copy_text("hola", backends=(roto, bueno))
    assert llamados == ["roto", "hola"]
    assert not clipboard.copy_text("x", backends=(roto,))
