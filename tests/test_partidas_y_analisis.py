"""Relojes congelados en todos los finales, carteles de resultado, base de
partidas (autoguardado, listar, abrir, borrar, exportar) y análisis con
mejor jugada."""
import io
import time

import chess
import chess.pgn
import pytest

from cabrechess.analysis import Analyzer
from cabrechess.database import GameDB
from cabrechess.endings import detect_end, end_message, end_title, flag_end

# ─── Finales: (fen inicial, jugadas uci, terminación, resultado, título) ──────
FINALES = [
    ("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1", ["a1a8"], "checkmate", "1-0",
     "¡Jaque mate! Ganan las blancas"),
    ("rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq g3 0 2", ["d8h4"], "checkmate", "0-1",
     "¡Jaque mate! Ganan las negras"),
    ("7k/8/6Q1/8/8/8/8/K7 w - - 0 1", ["g6f7"], "stalemate", "1/2-1/2", "Tablas por ahogado"),
    ("7k/8/8/8/8/8/1q6/K7 w - - 0 1", ["a1b2"], "insufficient", "1/2-1/2",
     "Tablas por material insuficiente"),
    ("4k3/8/8/8/8/8/8/4K2R w - - 0 1", ["e1f1", "e8f8", "f1e1", "f8e8"] * 2, "threefold", "1/2-1/2",
     "Tablas por triple repetición"),
    ("4k3/8/8/8/8/8/8/R3K3 w - - 99 80", ["a1a2"], "fifty", "1/2-1/2",
     "Tablas por la regla de 50 movimientos"),
]


def _jugar(game, fen, ucis, mode="pvp"):
    game.start_game(mode)
    game.cancel_ai_search()
    game.board = chess.Board(fen)
    for u in ucis:
        if game.game_over:
            break
        game.execute_move(chess.Move.from_uci(u))
    game.update()


def _relojes_quietos(game, segundos=5):
    antes = (game.time_white, game.time_black)
    game.time_last = time.time() - segundos
    for _ in range(3):
        game.update()
        game.draw()
    game.close_game_over_panel()
    game.undo_move()                      # navegar la revisión
    game.time_last = time.time() - segundos
    game.update()
    game.draw()
    assert (game.time_white, game.time_black) == antes


@pytest.mark.parametrize("fen,ucis,term,result,title", FINALES)
def test_final_cartel_reloj_y_autoguardado(game, fen, ucis, term, result, title):
    n_antes = game.get_db().count()
    _jugar(game, fen, ucis)
    assert game.game_over and game.termination == term and game.result == result
    assert title in game.game_over_msg
    _relojes_quietos(game)
    # Autoguardado (una sola vez)
    assert game.saved_game_id is not None
    game.update()
    db = game.get_db()
    assert db.count() == n_antes + 1
    row = db.get_game(game.saved_game_id)
    assert row["result"] == result and row["termination"] == term
    assert row["mode"] == "pvp" and row["time_control"] == "180+3"
    parsed = chess.pgn.read_game(io.StringIO(row["pgn"]))
    assert parsed.headers["Result"] == result


def test_bandera_congela_y_guarda_resultado_por_tiempo(game):
    game.start_game("pvp")
    game.execute_move(chess.Move.from_uci("e2e4"))
    game.time_black = 0.01
    game.time_last = time.time() - 1
    game.update()
    game.update()
    assert game.termination == "timeout" and game.result == "1-0"
    assert "Ganan las blancas por tiempo" in game.game_over_msg
    assert game.time_black == 0
    _relojes_quietos(game)
    row = game.get_db().get_game(game.saved_game_id)
    pgn = chess.pgn.read_game(io.StringIO(row["pgn"]))
    assert pgn.headers["Result"] == "1-0"
    assert pgn.headers["Termination"] == "time forfeit"


def test_vs_ia_mate_congela_relojes_y_guarda(game):
    game.player_color_choice = "white"
    _jugar(game, "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq g3 0 2", [], mode="vsai")
    game.ai_result_move = chess.Move.from_uci("d8h4")
    game.ai_move()
    game.update()
    assert game.game_over and game.result == "0-1"
    _relojes_quietos(game)
    assert game.get_db().get_game(game.saved_game_id)["black"] == "CabreChess AI"


def test_jugada_final_no_suma_incremento(game):
    game.start_game("pvp")
    game.board = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
    tw = game.time_white
    game.execute_move(chess.Move.from_uci("a1a8"))
    assert game.time_white == tw              # sin +3 s en la jugada de mate


def test_analisis_no_autoguarda(game):
    n = game.get_db().count()
    _jugar(game, "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1", ["a1a8"], mode="analysis")
    assert game.game_over and game.get_db().count() == n


def test_barra_de_revision_visible_tras_revisar(game):
    _jugar(game, "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1", ["a1a8"])
    game.start_review()
    called = []
    game.draw_review_bar = lambda: called.append(True)
    game.draw()
    assert called, "la barra |< < > >| debe verse apenas se entra a revisar"


# ─── Textos ──────────────────────────────────────────────────────────────────
def test_textos_de_fin():
    assert end_title("timeout", "0-1") == "Ganan las negras por tiempo"
    assert end_title("seventyfive", "1/2-1/2") == "Tablas por la regla de 75 movimientos"
    assert "Resultado: 1-0" in end_message("checkmate", "1-0")
    assert flag_end(chess.Board("4k3/8/8/8/8/8/8/3QK3 w - - 0 1"), chess.WHITE) == ("timeout_draw", "1/2-1/2")
    assert detect_end(chess.Board()) is None


# ─── Base de datos ───────────────────────────────────────────────────────────
def _add(db, **kw):
    base = dict(mode="pvp", white="A", black="B", result="1-0", termination="checkmate",
                pgn='[Result "1-0"]\n\n1. e4 e5 1-0\n')
    base.update(kw)
    return db.add_game(**base)


def test_db_en_memoria_crud():
    db = GameDB(":memory:")
    a = _add(db, played_at="2026-10-20T10:00:00", eco="C20", opening="Apertura del peón rey")
    b = _add(db, played_at="2026-10-21T10:00:00", result="0-1")
    games = db.list_games()
    assert [g["id"] for g in games] == [b, a]          # más reciente primero
    assert db.get_game(a)["eco"] == "C20"
    assert db.delete_game(a) and not db.delete_game(a)
    assert db.count() == 1 and db.get_game(a) is None


def test_db_en_archivo_persiste(tmp_path):
    path = tmp_path / "sub" / "partidas.db"
    db = GameDB(path)
    gid = _add(db)
    db.close()
    assert GameDB(path).get_game(gid)["white"] == "A"


def test_ruta_por_defecto_respeta_data_dir(monkeypatch, tmp_path):
    from cabrechess import database, settings
    monkeypatch.setenv("CABRECHESS_DATA_DIR", str(tmp_path))
    assert database.default_db_path() == tmp_path / "partidas.db"
    monkeypatch.delenv("CABRECHESS_DATA_DIR")
    monkeypatch.setattr(settings.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    assert database.default_db_path() == tmp_path / "AppData" / "CabreChess" / "partidas.db"
    monkeypatch.setattr(settings.sys, "platform", "linux")
    assert settings.data_dir().name == ".cabrechess"


# ─── Pantalla "Partidas guardadas" ───────────────────────────────────────────
def _guardar_una(game):
    _jugar(game, "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq g3 0 2", ["d8h4"])
    return game.saved_game_id


def test_listar_abrir_en_analisis(game):
    gid = _guardar_una(game)
    game.open_saved_games()
    assert game.mode == "saved"
    idx = [g["id"] for g in game.saved_games].index(gid)
    game.saved_sel = idx
    game.draw()
    game.saved_action("open")
    assert game.mode == "analysis" and game.loaded_game_id == gid
    assert game.game_over and game.result == "0-1" and not game.game_over_panel
    assert game.review_index == 0
    n = game.get_db().count()
    game.update()
    assert game.get_db().count() == n            # abrir no vuelve a guardar
    game.review_step(1)
    game.draw()


def test_borrar_pide_confirmacion(game):
    gid = _guardar_una(game)
    game.open_saved_games()
    game.saved_sel = [g["id"] for g in game.saved_games].index(gid)
    game.saved_action("delete")
    assert game.get_db().get_game(gid) is not None     # primer click: confirmar
    game.saved_action("delete")
    assert game.get_db().get_game(gid) is None


def test_exportar_pgn(game, monkeypatch, tmp_path):
    gid = _guardar_una(game)
    game.open_saved_games()
    game.saved_sel = [g["id"] for g in game.saved_games].index(gid)
    target = tmp_path / "exportada.pgn"
    monkeypatch.setattr(game, "ask_pgn_filename", lambda d: str(target))
    game.saved_action("export")
    assert chess.pgn.read_game(io.StringIO(target.read_text(encoding="utf-8"))).headers["Result"] == "0-1"


def test_menu_tiene_partidas_guardadas(game):
    labels = [b[0] for b in game.menu_main_buttons()]
    assert "Partidas guardadas" in labels
    rect = [b[4] for b in game.menu_main_buttons() if b[0] == "Partidas guardadas"][0]
    game.mode = "menu"
    game.handle_click(rect.center)
    assert game.mode == "saved"
    import pygame
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
    game.handle_events()
    assert game.mode == "menu"


# ─── Análisis: mejor jugada ──────────────────────────────────────────────────
@pytest.mark.parametrize("fen,best", [
    ("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1", "a1a8"),                          # mate del pasillo
    ("r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "h5f7"),  # pastor
    ("4k3/8/8/8/8/8/3q4/3QK3 w - - 0 1", "d1d2 e1d2"),                      # capturar la dama
])
def test_mejor_jugada_posiciones_conocidas(fen, best):
    res = Analyzer(depth=2).analyse_now(chess.Board(fen))
    assert res.move.uci() in best.split() and res.san


def test_analisis_en_segundo_plano_y_mate():
    a = Analyzer(depth=2)
    board = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
    a.request(board)
    res = a.wait(board, timeout=30)
    assert res.move.uci() == "a1a8" and res.mate == 1 and res.score_text() == "#"
    a.stop()


def test_analisis_en_la_ui(game):
    game.start_game("analysis")
    game.execute_move(chess.Move.from_uci("e2e4"))
    game.update()
    res = game.get_analyzer().wait(game.board, timeout=60)
    assert res is not None and res.move in game.board.legal_moves
    game.draw()                                   # flecha + "Mejor: ..."


def test_stockfish_mal_configurado_cae_al_motor_propio():
    a = Analyzer(depth=1, stockfish_path="/no/existe/stockfish")
    res = a.analyse_now(chess.Board())
    assert res.engine == "CabreChess" and res.move is not None
    assert "Stockfish no disponible" in a.error


def test_pgn_desde_posicion_con_negras(game):
    _jugar(game, "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq g3 0 2", ["d8h4"])
    text, _ = game.build_pgn()
    assert "2... Qh4#" in text and '[FEN "' in text
    parsed = chess.pgn.read_game(io.StringIO(text))
    assert not parsed.errors and parsed.end().board().is_checkmate()
