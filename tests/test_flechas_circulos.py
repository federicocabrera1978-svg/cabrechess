"""Flechas y círculos del usuario con click derecho (A8, como en Lichess)."""
import chess
import pygame

from cabrechess.shapes import Shape, ShapeLayer, color_from_mods


def _evento(tipo, game, sq, button=3):
    # los eventos traen coordenadas de ventana (la superficie lógica va escalada)
    x, y = game.center_of_sq(sq)
    scale, ox, oy, _w, _h = game.viewport()
    pos = (round(x * scale + ox), round(y * scale + oy))
    assert game.pixel_to_sq(*game.to_logical(pos)) == sq
    return pygame.event.Event(tipo, button=button, pos=pos)


def _trazar(game, orig, dest, mods=0):
    game.start_shape(game.center_of_sq(orig), mods)
    game.finish_shape(game.center_of_sq(dest))


def test_color_segun_modificadores():
    assert color_from_mods() == "green"
    assert color_from_mods(shift=True) == "red"
    assert color_from_mods(ctrl=True) == "red"
    assert color_from_mods(alt=True) == "blue"
    assert color_from_mods(shift=True, alt=True) == "yellow"


def test_capa_agrega_cambia_color_y_borra():
    capa = ShapeLayer()
    assert capa.toggle("k", 12, 28) == [Shape(12, 28, "green")]
    assert capa.toggle("k", 12, 28, "red") == [Shape(12, 28, "red")]
    assert capa.toggle("k", 12, 28, "red") == []
    capa.toggle("k", 4, 4)
    assert capa.for_position("k")[0].is_circle
    # otra posición: se descartan
    assert capa.for_position("otra") == []


def test_click_derecho_dibuja_circulo_y_flecha(game):
    game.start_game("pvp")
    _trazar(game, chess.E4, chess.E4)
    _trazar(game, chess.G1, chess.F3, pygame.KMOD_SHIFT)
    formas = game.current_shapes()
    assert Shape(chess.E4, chess.E4, "green") in formas
    assert Shape(chess.G1, chess.F3, "red") in formas
    # repetir la misma flecha con el mismo color la borra
    _trazar(game, chess.G1, chess.F3, pygame.KMOD_SHIFT)
    assert game.current_shapes() == [Shape(chess.E4, chess.E4, "green")]
    game.draw()  # se dibuja sin errores


def test_soltar_fuera_del_tablero_no_dibuja(game):
    game.start_game("pvp")
    game.start_shape(game.center_of_sq(chess.E2))
    game.finish_shape((2, 2))
    assert game.current_shapes() == []


def test_mover_borra_las_formas(game):
    game.start_game("pvp")
    _trazar(game, chess.E2, chess.E4)
    assert game.current_shapes()
    game.execute_move(chess.Move.from_uci("e2e4"))
    assert game.current_shapes() == []


def test_click_izquierdo_en_el_tablero_borra(game):
    game.start_game("pvp")
    game.draw()
    _trazar(game, chess.D2, chess.D4)
    pygame.event.post(_evento(pygame.MOUSEBUTTONDOWN, game, chess.A3, button=1))
    game.handle_events()
    assert game.current_shapes() == []


def test_eventos_de_click_derecho(game):
    game.start_game("pvp")
    game.draw()
    pygame.event.post(_evento(pygame.MOUSEBUTTONDOWN, game, chess.C2))
    pygame.event.post(_evento(pygame.MOUSEBUTTONUP, game, chess.C4))
    game.handle_events()
    assert game.current_shapes() == [Shape(chess.C2, chess.C4, "green")]


def test_tablero_girado_usa_la_casilla_correcta(game):
    game.start_game("pvp")
    game.flip_board()
    _trazar(game, chess.H7, chess.H5)
    assert game.current_shapes() == [Shape(chess.H7, chess.H5, "green")]


def test_en_el_menu_no_se_dibuja(game):
    game.mode = "menu"
    game.start_shape((game.center_of_sq(chess.E4)))
    assert game.shape_start is None


def test_formas_en_revision_quedan_en_esa_posicion(game):
    game.start_game("pvp")
    for san in ["e4", "e5", "Nf3"]:
        game.execute_move(game.board.parse_san(san))
    game.resign()
    game.game_over_panel = False
    game.review_step(to=1)
    _trazar(game, chess.D7, chess.D5)
    assert game.current_shapes()
    game.review_step(1)
    assert game.current_shapes() == []
