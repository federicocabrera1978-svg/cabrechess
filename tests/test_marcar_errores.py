"""Marcar errores al terminar la partida (B9): ?!, ?, ?? con los umbrales de
Lichess, resumen por bando, lista de jugadas y NAGs en el PGN."""
import chess

from cabrechess import review
from cabrechess.pgn import build_pgn


def test_chances_de_ganar_simetricas_y_acotadas():
    assert review.winning_chances(0) == 0
    assert review.winning_chances(300) == -review.winning_chances(-300)
    assert 1 > review.winning_chances(review.CP_CAP) > 0.99
    assert review.winning_chances(10**6) == review.winning_chances(review.CP_CAP)


def test_clasificacion_por_caida_de_chances():
    W, B = chess.WHITE, chess.BLACK
    assert review.classify(0, -20, W) == ""
    assert review.classify(0, -60, W) == "?!"
    assert review.classify(0, -120, W) == "?"
    assert review.classify(0, -300, W) == "??"
    # Para negras, subir la evaluación es lo malo
    assert review.classify(0, 300, B) == "??"
    assert review.classify(0, -300, B) == ""
    # Posición ya perdida por mucho: perder 300 más no es error grave
    assert review.classify(-1200, -1500, W) == ""


def test_annotate_y_resumen_alternan_bandos():
    evals = [0, 0, 400, -400, -400]   # 1... ?? de negras, 2. ?? de blancas
    marks = review.annotate(evals)
    assert marks == ["", "??", "??", ""]
    s = review.summary(marks)
    assert s[chess.WHITE]["??"] == 1 and s[chess.BLACK]["??"] == 1
    # Si arranca con negras (FEN), la primera jugada es de negras
    assert review.annotate([0, 400], chess.BLACK) == ["??"]


def _jugar(game, sans):
    game.start_game("pvp")
    for san in sans:
        game.execute_move(game.board.parse_san(san))


def test_regalar_la_dama_se_marca_como_error_grave(game):
    # 1.e4 e5 2.Qg4 d5 3.Qd7+?? Bxd7: la dama blanca se regala
    _jugar(game, ["e4", "e5", "Qg4", "d5", "Qd7+", "Bxd7"])
    game.resign()
    rv = game.maybe_start_review()
    assert rv is not None
    assert rv.wait(60)
    assert game.move_mark(4) == "??"
    assert rv.summary()[chess.WHITE]["??"] >= 1
    nags = rv.nags()
    assert nags[4] == review.NAGS["??"]
    pgn, _ = game.build_pgn()
    assert "3. Qd7+ $4 Bxd7" in pgn


def test_revision_se_reinicia_con_partida_nueva(game):
    _jugar(game, ["f3", "e5", "g4", "Qh4#"])
    assert game.game_over
    game.update()
    assert game.game_review is not None
    game.game_review.wait(60)
    assert game.move_mark(2) == "??"   # 2.g4?? permite el mate
    game.reset_game()
    assert game.game_review is None
    assert game.move_mark(2) == ""


def test_resumen_y_dibujo_sin_errores(game):
    _jugar(game, ["f3", "e5", "g4", "Qh4#"])
    game.update()
    game.game_review.wait(60)
    game.game_over_panel = False
    parts = game.review_summary_parts()
    textos = [t for t, _c in parts]
    assert "Blancas:" in textos and "Negras:" in textos
    game.draw()   # dibuja lista con marcas + resumen sin romper


def test_mientras_analiza_muestra_progreso(game):
    _jugar(game, ["f3", "e5", "g4", "Qh4#"])
    rv = review.GameReview(game.board)   # sin arrancar: 0%
    game.game_review = rv
    assert game.review_summary_parts()[0][0].startswith("Buscando errores")
    assert game.move_mark(2) == ""


def test_build_pgn_con_nags():
    board = chess.Board()
    for san in ["f3", "e5", "g4", "Qh4#"]:
        board.push_san(san)
    pgn, _ = build_pgn(board, [], "pvp", "A", "B", nags={2: 4, 0: 6})
    assert "1. f3 $6 e5 2. g4 $4 Qh4#" in pgn or "1. f3?! e5 2. g4?? Qh4#" in pgn


def test_pgn_cargado_tambien_se_revisa_y_grafico_no_pisa_la_barra(game):
    pgn = "1. f3 e5 2. g4 Qh4# 0-1\n"
    assert game.load_pgn_text(pgn)
    game.update()
    assert game.game_review is not None and game.game_review.wait(60)
    assert game.move_mark(2) == "??"
    assert game.eval_graph_above_review()
    clip, _row_h, _top = game.history_layout()
    assert clip.bottom <= game.review_buttons()[0][1].top - 70
    game.draw()
