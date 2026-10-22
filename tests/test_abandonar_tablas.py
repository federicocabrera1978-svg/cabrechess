"""Abandonar y ofrecer tablas (vs IA y 2 jugadores)."""
import chess

from cabrechess.endings import ai_accepts_draw, end_title, resign_end


def _start(game, mode="pvp", fen=None, ai_color=chess.BLACK):
    game.mode = mode
    game.ai_color = ai_color
    game.reset_game()
    game.cancel_ai_search()
    if fen:
        game.board = chess.Board(fen)


def _icons(game):
    return [icon for icon, _c, _a, _r in game.panel_buttons()]


def test_textos_y_resultados():
    assert resign_end(chess.WHITE) == ("resign", "0-1")
    assert resign_end(chess.BLACK) == ("resign", "1-0")
    assert end_title("resign", "1-0") == "Ganan las blancas por abandono"
    assert end_title("agreement", "1/2-1/2") == "Tablas por acuerdo"


def test_ia_acepta_tablas_solo_si_le_conviene():
    # La IA juega con negras: eval +300 (blancas ganan) -> acepta
    assert ai_accepts_draw(300, chess.BLACK, 10)
    # La IA va ganando -> nunca acepta
    assert not ai_accepts_draw(-300, chess.BLACK, 60)
    # Pareja: rechaza temprano, acepta desde la jugada 30
    assert not ai_accepts_draw(0, chess.BLACK, 5)
    assert ai_accepts_draw(10, chess.WHITE, 30)


def test_botones_solo_en_partida_en_curso(game):
    _start(game, "pvp")
    assert "flag" in _icons(game) and "draw" in _icons(game)
    _start(game, "analysis")
    assert "flag" not in _icons(game)
    _start(game, "pvp")
    game.end_game(*resign_end(chess.WHITE))
    assert "flag" not in _icons(game)
    # Los rects no se pisan y entran en el panel
    _start(game, "vsai")
    rects = [r for *_x, r in game.panel_buttons()]
    for a, b in zip(rects, rects[1:]):
        assert a.right < b.left


def test_abandonar_con_confirmacion_pvp(game):
    _start(game, "pvp")
    game.execute_move(chess.Move.from_uci("e2e4"))   # turno de negras
    game.ask_resign()
    assert game.confirm and "Las negras" in game.confirm["subtitle"]
    game.close_confirm()
    assert not game.game_over
    game.ask_resign()
    game.resign()
    game.update()
    assert game.game_over and game.result == "1-0"
    assert "Ganan las blancas por abandono" in game.game_over_msg
    assert game.confirm is None


def test_abandonar_vs_ia_jugando_con_negras(game):
    _start(game, "vsai", ai_color=chess.WHITE)
    game.ask_resign()
    game.resign()
    assert game.result == "1-0" and game.termination == "resign"


def test_click_en_boton_abandonar(game):
    _start(game, "vsai")
    rect = next(r for icon, _c, _a, r in game.panel_buttons() if icon == "flag")
    game.handle_click(rect.center)
    assert game.confirm is not None
    label, _action, brect = game.confirm_buttons()[0]
    assert label == "Abandonar"
    game.handle_click(brect.center)
    assert game.game_over and game.result == "0-1"


def test_tablas_pvp_aceptadas_y_rechazadas(game):
    _start(game, "pvp")
    game.offer_draw()
    assert "Las blancas ofrecen tablas" == game.confirm["title"]
    game.decline_draw()
    assert not game.game_over
    # Sin mover no se puede volver a ofrecer
    game.offer_draw()
    assert game.confirm is None and not game.can_offer_draw()
    game.execute_move(chess.Move.from_uci("e2e4"))
    game.offer_draw()
    assert "Las negras ofrecen tablas" == game.confirm["title"]
    game.accept_draw()
    assert game.game_over and game.result == "1/2-1/2"
    assert game.termination == "agreement"
    pgn, _ = game.build_pgn()
    assert '[Result "1/2-1/2"]' in pgn


def test_ia_rechaza_tablas_si_va_ganando(game):
    # Negras (IA) con dama de más
    _start(game, "vsai", fen="4k3/8/8/8/3q4/8/8/4K3 w - - 0 40")
    game.offer_draw()
    assert not game.game_over
    assert "rechaza" in game.pgn_saved_msg


def test_ia_acepta_tablas_si_va_perdiendo(game):
    _start(game, "vsai", fen="4k3/8/8/8/3Q4/8/8/4K3 w - - 0 12")
    game.offer_draw()
    assert game.game_over and game.result == "1/2-1/2"


def test_abandono_se_guarda_y_se_reabre(game):
    _start(game, "pvp")
    game.execute_move(chess.Move.from_uci("e2e4"))
    game.ask_resign()
    game.resign()
    game.update()                       # autoguarda
    gid = game.saved_game_id
    assert gid
    game.load_saved_game(gid)
    assert game.termination == "resign" and game.result == "1-0"


def test_render_con_dialogo(game):
    _start(game, "pvp")
    game.ask_resign()
    game.draw()
    game.close_confirm()
    game.offer_draw()
    game.draw()
