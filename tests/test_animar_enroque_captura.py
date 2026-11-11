"""Animación del enroque con las dos piezas y de la pieza capturada (A8)."""
import chess

from cabrechess.animation import Slide, captured_square, plan_animation


def _board(fen):
    return chess.Board(fen)


def test_jugada_normal_desliza_una_pieza():
    b = chess.Board()
    plan = plan_animation(b, chess.Move.from_uci("g1f3"))
    assert plan.slides == (Slide(chess.Piece(chess.KNIGHT, chess.WHITE), chess.G1, chess.F3),)
    assert plan.captured is None
    assert plan.hidden_squares() == {chess.F3}


def test_enroque_corto_mueve_rey_y_torre():
    b = _board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    plan = plan_animation(b, chess.Move.from_uci("e1g1"))
    assert plan.slides == (
        Slide(chess.Piece(chess.KING, chess.WHITE), chess.E1, chess.G1),
        Slide(chess.Piece(chess.ROOK, chess.WHITE), chess.H1, chess.F1),
    )
    assert plan.hidden_squares() == {chess.G1, chess.F1}
    assert plan.captured is None


def test_enroque_largo_negro_mueve_rey_y_torre():
    b = _board("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1")
    plan = plan_animation(b, chess.Move.from_uci("e8c8"))
    assert plan.slides == (
        Slide(chess.Piece(chess.KING, chess.BLACK), chess.E8, chess.C8),
        Slide(chess.Piece(chess.ROOK, chess.BLACK), chess.A8, chess.D8),
    )


def test_captura_desvanece_la_pieza_capturada():
    b = _board("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
    plan = plan_animation(b, chess.Move.from_uci("e4d5"))
    assert plan.captured == chess.Piece(chess.PAWN, chess.BLACK)
    assert plan.captured_square == chess.D5


def test_captura_al_paso_usa_la_casilla_del_peon():
    b = _board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    move = chess.Move.from_uci("e5d6")
    assert captured_square(b, move) == chess.D5
    plan = plan_animation(b, move)
    assert plan.captured == chess.Piece(chess.PAWN, chess.BLACK)
    assert plan.captured_square == chess.D5


def test_enroque_en_juego_oculta_ambas_casillas_y_dibuja(game):
    game.start_game("pvp")
    for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6"]:
        game.execute_move(chess.Move.from_uci(uci))
    game.execute_move(chess.Move.from_uci("e1g1"))
    assert game.anim_move is not None
    assert game.anim_hidden_squares() == {chess.G1, chess.F1}
    # a mitad de la animación se dibuja sin errores y no termina
    game.draw()
    game.anim_start -= 10  # ya terminó
    game.draw()
    assert game.anim_move is None


def test_captura_al_paso_suma_al_material_y_se_desvanece(game):
    game.start_game("pvp")
    for uci in ["e2e4", "a7a6", "e4e5", "d7d5"]:
        game.execute_move(chess.Move.from_uci(uci))
    antes = len(game.captured_black)
    game.execute_move(chess.Move.from_uci("e5d6"))
    assert len(game.captured_black) == antes + 1
    assert game.anim_plan.captured_square == chess.D5
    game.draw()
