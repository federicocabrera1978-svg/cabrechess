"""Chess960 / Fischer Random (B11, parte 2): posiciones, enroque 960, PGN,
menú, IA, estadísticas y dibujo."""
import random
import sys
import time
from pathlib import Path

import chess
import pygame
import pytest

from cabrechess import chess960, stats
from cabrechess.animation import Slide, plan_animation
from cabrechess.engine import SimpleEngine
from cabrechess.pgn import build_pgn, moves_from_game, parse_fen, parse_pgn
from cabrechess.settings import load_settings

FAKE = Path(__file__).with_name("fake_uci.py")

# Posición 237: NRQBKNBR. Con estas jugadas los dos bandos pueden enrocar:
# blancas corto (rey e1 → g1, torre h1 → f1) y negras largo (rey e8 → c8,
# torre b8 → d8).
POS = 237
PREP = "h2h3 d7d6 f1g3 c8d7 g1h2 e7e5 e2e4 d8e7".split()


def _prepared():
    board = chess960.new_board(POS)
    for uci in PREP:
        board.push_uci(uci)
    return board


def _click(game, sq):
    game.handle_click(game.center_of_sq(sq))


# ── posiciones ──
def test_las_960_posiciones_son_validas_y_distintas():
    vistas = set()
    for n in range(chess960.POSITIONS):
        b = chess960.new_board(n)
        assert b.chess960 and b.is_valid()
        assert chess960.position_number(b) == n
        fila = b.board_fen().split("/")[-1]
        # Alfiles en casillas de distinto color y rey entre las torres
        alfiles = [i for i, c in enumerate(fila) if c == "B"]
        assert (alfiles[0] + alfiles[1]) % 2 == 1
        torres = [i for i, c in enumerate(fila) if c == "R"]
        assert torres[0] < fila.index("K") < torres[1]
        # Las negras son el espejo de las blancas
        assert b.board_fen().split("/")[0] == fila.lower()
        assert b.castling_rights == (chess.BB_SQUARES[torres[0]] | chess.BB_SQUARES[torres[1]]
                                     | chess.BB_SQUARES[56 + torres[0]] | chess.BB_SQUARES[56 + torres[1]])
        vistas.add(fila)
    assert len(vistas) == 960
    # La 518 es la posición clásica
    assert chess960.new_board(chess960.STANDARD_POSITION).board_fen() == chess.Board().board_fen()


def test_posicion_al_azar_y_fuera_de_rango():
    rng = random.Random(7)
    nums = {chess960.random_position(rng) for _ in range(200)}
    assert all(0 <= n < 960 for n in nums) and len(nums) > 100
    assert chess960.position_number(chess960.new_board(rng=random.Random(1))) is not None
    with pytest.raises(ValueError):
        chess960.new_board(960)
    assert chess960.position_number(chess.Board()) is None
    assert chess960.variant_label(chess.Board()) == ""
    assert chess960.variant_label(chess960.new_board(42)) == "Chess960 · posición 42"


# ── enroque 960 ──
def test_enroque_corto_960_rey_a_la_torre_o_a_g1():
    b = _prepared()
    por_torre = chess960.castling_move_to(b, chess.E1, chess.H1)
    por_destino = chess960.castling_move_to(b, chess.E1, chess.G1)
    assert por_torre == por_destino == chess.Move.from_uci("e1h1")
    assert b.is_kingside_castling(por_torre) and b.san(por_torre) == "O-O"
    assert chess960.castling_squares(b, por_torre) == (chess.E1, chess.G1, chess.H1, chess.F1)
    b.push(por_torre)
    assert b.piece_at(chess.G1) == chess.Piece(chess.KING, chess.WHITE)
    assert b.piece_at(chess.F1) == chess.Piece(chess.ROOK, chess.WHITE)
    assert b.piece_at(chess.E1) is None and b.piece_at(chess.H1) is None


def test_enroque_largo_960_negras():
    b = _prepared()
    b.push_uci("e1h1")
    move = chess960.castling_move_to(b, chess.E8, chess.C8)
    assert move == chess960.castling_move_to(b, chess.E8, chess.B8) == chess.Move.from_uci("e8b8")
    assert b.is_queenside_castling(move) and b.san(move) == "O-O-O"
    b.push(move)
    assert b.piece_at(chess.C8) == chess.Piece(chess.KING, chess.BLACK)
    assert b.piece_at(chess.D8) == chess.Piece(chess.ROOK, chess.BLACK)
    assert b.piece_at(chess.B8) is None and b.piece_at(chess.E8) is None


def test_animacion_del_enroque_960_mueve_rey_y_torre():
    b = _prepared()
    plan = plan_animation(b, chess.Move.from_uci("e1h1"))
    assert plan.slides == (
        Slide(chess.Piece(chess.KING, chess.WHITE), chess.E1, chess.G1),
        Slide(chess.Piece(chess.ROOK, chess.WHITE), chess.H1, chess.F1),
    )
    assert plan.captured is None and plan.hidden_squares() == {chess.G1, chess.F1}


def test_enroque_con_rey_que_no_se_mueve_y_jugada_normal_gana():
    # Rey b1 y torre a1: el enroque largo deja rey c1 / torre d1, pero b1c1
    # también es una jugada normal del rey; soltar en c1 es la jugada normal.
    b = chess.Board("rk6/8/8/8/8/8/8/RK6 w Aa - 0 1", chess960=True)
    assert chess960.castling_move_to(b, chess.B1, chess.A1) == chess.Move.from_uci("b1a1")
    # Rey g1, torre h1: el rey no se mueve al enrocar corto (solo la torre a f1)
    b = chess.Board("6kr/8/8/8/8/8/8/6KR w Hh - 0 1", chess960=True)
    move = chess960.castling_move_to(b, chess.G1, chess.H1)
    assert move is not None and b.is_castling(move)
    plan = plan_animation(b, move)
    assert plan.slides[0] == Slide(chess.Piece(chess.KING, chess.WHITE), chess.G1, chess.G1)
    assert plan.slides[1] == Slide(chess.Piece(chess.ROOK, chess.WHITE), chess.H1, chess.F1)


def test_ui_jugada_normal_tiene_prioridad_sobre_el_enroque(game):
    game.start_game("pvp")
    game.board = chess.Board("rk6/8/8/8/8/8/8/RK6 w Aa - 0 1", chess960=True)
    assert game.find_move(chess.B1, chess.C1) == chess.Move.from_uci("b1c1")
    assert game.find_move(chess.B1, chess.A1) == chess.Move.from_uci("b1a1")


def test_ui_enroque_clic_rey_y_torre_y_arrastre_a_destino(game):
    game.set_variant("chess960", save=False)
    game.start_game("pvp")
    game.board = chess960.new_board(POS)
    for uci in PREP:
        game.execute_move(chess.Move.from_uci(uci))
    # Blancas: clic en el rey, clic en su torre → O-O
    _click(game, chess.E1)
    assert game.selected_sq == chess.E1
    _click(game, chess.H1)
    assert game.board.move_stack[-1] == chess.Move.from_uci("e1h1")
    assert game.move_history_san[-1] == "O-O"
    assert len(game.anim_plan.slides) == 2
    game.draw()                                   # animación a mitad
    game.anim_start -= 10
    game.draw()
    # Negras: arrastrar el rey a c8 (casilla final) → O-O-O
    _click(game, chess.E8)
    assert game.dragging and game.drag_from == chess.E8
    game.draw()                                   # marca c8 y la torre b8
    game.handle_drop(game.center_of_sq(chess.C8))
    assert game.move_history_san[-1] == "O-O-O"
    assert game.board.piece_at(chess.C8).piece_type == chess.KING
    assert game.board.piece_at(chess.D8).piece_type == chess.ROOK
    # Deshacer vuelve a dejar rey y torre en su lugar
    game.undo_move()
    assert game.board.piece_at(chess.E8).piece_type == chess.KING
    assert game.board.piece_at(chess.B8).piece_type == chess.ROOK


def test_clasico_clic_en_torre_con_rey_elegido_cambia_seleccion(game):
    game.start_game("pvp")
    for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6"]:
        game.execute_move(chess.Move.from_uci(uci))
    _click(game, chess.E1)
    _click(game, chess.H1)                        # en clásico: selecciona la torre
    assert game.selected_sq == chess.H1 and not game.board.is_check()
    assert game.find_move(chess.E1, chess.G1) == chess.Move.from_uci("e1g1")


# ── PGN ──
def test_pgn_ida_y_vuelta_con_enroques():
    b = _prepared()
    b.push_uci("e1h1")
    b.push_uci("e8b8")
    sans = []
    replay = b.root()
    for m in b.move_stack:
        sans.append(replay.san(m))
        replay.push(m)
    text, _ = build_pgn(b, sans, "pvp", "A", "B")
    assert '[Variant "Chess960"]' in text
    assert f'[FEN "{b.root().fen()}"]' in text and '[SetUp "1"]' in text
    assert "O-O O-O-O" in text and "ECO" not in text
    game, err = parse_pgn(text)
    assert err is None
    board = game.board()
    assert board.chess960 and chess960.position_number(board) == POS
    assert moves_from_game(game) == list(b.move_stack)


def test_pgn_de_la_518_lleva_fen_y_variante():
    b = chess960.new_board(chess960.STANDARD_POSITION)
    b.push_san("e4")
    text, _ = build_pgn(b, [], "pvp", "A", "B")
    assert '[Variant "Chess960"]' in text and '[FEN "' in text and '[SetUp "1"]' in text
    assert parse_pgn(text)[0].board().chess960
    # Una partida clásica sigue sin FEN ni Variant
    text, _ = build_pgn(chess.Board(), ["e4"], "pvp", "A", "B")
    assert "Variant" not in text and "FEN" not in text


def test_cargar_pgn_960_en_la_app(game):
    b = _prepared()
    b.push_uci("e1h1")
    text, _ = build_pgn(b, [], "pvp", "A", "B", result="*")
    assert game.load_pgn_text(text)
    assert game.board.chess960
    assert chess960.variant_label(game.board) == f"Chess960 · posición {POS}"
    assert "posición 237" in game.pgn_saved_msg
    assert game.move_history_san[-1] == "O-O"
    game.review_step(to=len(PREP) + 1)
    game.draw()
    # La partida exportada de nuevo sigue siendo 960
    assert '[Variant "Chess960"]' in game.build_pgn()[0]


def test_fen_960_activa_las_reglas_960():
    board, err = parse_fen("nrqbknbr/pppppppp/8/8/8/8/PPPPPPPP/NRQBKNBR w KQkq - 0 1")
    assert err is None and board.chess960
    board, err = parse_fen("nrqbknbr/pppppppp/8/8/8/8/PPPPPPPP/NRQBKNBR w HBhb - 0 1")
    assert err is None and board.chess960
    board, _ = parse_fen(chess.STARTING_FEN)
    assert not board.chess960


# ── menú y ajustes ──
def test_fila_variante_en_el_menu_y_se_recuerda(game):
    game.stockfish_path = "x"
    rows = game.menu_option_rows()
    labels = [r[0] for r in rows]
    assert labels == ["Nivel IA:", "Color (vs IA):", "Tiempo:", "Variante:", "Rival IA:"]
    ys = [r[1] for r in rows]
    assert ys == sorted(set(ys))
    _lbl, _y, _acc, options = rows[3]
    rect = next(r for text, r, _s, _v in options if text == "Chess960")
    game.handle_click(rect.center)
    assert game.variant == "chess960"
    assert load_settings()["variant"] == "chess960"
    screen = game.screen.get_rect()
    todos = [r for *_x, r in game.menu_main_buttons()] + [r for *_x, r in game.menu_load_buttons()]
    for *_x, opts in game.menu_option_rows():
        todos += [o[1] for o in opts]
    for i, a in enumerate(todos):
        assert screen.contains(a)
        assert not any(a.colliderect(b) for b in todos[i + 1:])
    game.draw_menu()
    game.set_variant("standard")
    assert load_settings()["variant"] == "standard"


def test_variante_invalida_en_settings(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text('{"variant": "atomic"}', encoding="utf-8")
    assert load_settings(p)["variant"] == "standard"


def test_partida_nueva_960_en_pvp_y_vs_ia_pero_no_en_analisis(game):
    game.set_variant("chess960", save=False)
    game.start_game("pvp")
    assert game.board.chess960 and chess960.position_number(game.board) is not None
    game.start_game("analysis")
    assert not game.board.chess960
    game.player_color_choice = "white"
    game.start_game("vsai")
    assert game.board.chess960
    game.set_variant("standard", save=False)
    game.reset_game()
    assert not game.board.chess960 and game.board.fen() == chess.STARTING_FEN


# ── IA ──
def test_motor_propio_juega_y_enroca_en_960():
    b = _prepared()
    move = SimpleEngine().get_best_move(b, depth=2)
    assert move in b.legal_moves
    # Desde muchas posiciones al azar siempre devuelve una jugada legal
    for n in random.Random(3).sample(range(960), 5):
        b = chess960.new_board(n)
        assert SimpleEngine().get_best_move(b, depth=1) in b.legal_moves


def _wait_ai(game, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        with game.ai_lock:
            ready = game.ai_move_ready
        if ready:
            game.ai_move()
            return True
        time.sleep(0.02)
    return False


def test_vs_ia_960_la_ia_responde(game):
    game.set_variant("chess960", save=False)
    game.ai_level = 1
    game.player_color_choice = "black"            # la IA (blancas) arranca
    game.start_game("vsai")
    assert game.board.chess960
    assert _wait_ai(game)
    assert len(game.board.move_stack) == 1


def test_stockfish_recibe_uci_chess960(game, tmp_path, monkeypatch):
    log = tmp_path / "uci.log"
    monkeypatch.setenv("FAKE_UCI_LOG", str(log))
    game.stockfish_path = [sys.executable, str(FAKE)]
    game.ai_engine = "stockfish"
    game.set_variant("chess960", save=False)
    game.player_color_choice = "black"
    game.start_game("vsai")
    try:
        assert game.uses_stockfish()
        assert _wait_ai(game)
        assert "UCI_Chess960 value true" in log.read_text(encoding="utf-8")
        assert len(game.board.move_stack) == 1 and not game.sf_failed
    finally:
        game.close_stockfish()


# ── estadísticas ──
def test_estadisticas_cuentan_960_y_las_muestran_aparte(tmp_path, monkeypatch):
    monkeypatch.setenv("CABRECHESS_DATA_DIR", str(tmp_path))
    stats.record_game("win", 3, "white")
    stats.record_game("loss", 3, "black", variant="chess960")
    stats.record_game("draw", 2, "white", variant="otra")      # inválida = clásica
    games = stats.load_stats()["games"]
    assert "variant" not in games[0] and games[1]["variant"] == "chess960"
    assert "variant" not in games[2]
    s = stats.summarize(stats.load_stats())
    assert s["totals"]["played"] == 3          # cuentan igual para totales y Elo
    assert s["by_level"][3]["played"] == 2
    assert s["chess960"]["played"] == 1 and s["chess960"]["loss"] == 1


def test_partida_960_vs_ia_se_registra_como_960(game, tmp_path, monkeypatch):
    monkeypatch.setenv("CABRECHESS_DATA_DIR", str(tmp_path))
    game.set_variant("chess960", save=False)
    game.player_color_choice = "white"
    game.start_game("vsai")
    game.cancel_ai_search()
    game.result = "1-0"
    game.termination = "resign"
    game.record_game_stats()
    g = stats.load_stats()["games"][-1]
    assert g["variant"] == "chess960" and g["result"] == "win"
    game.open_stats()
    rows = game._stats_rows(game.stats_summary)
    assert rows[-1][0] == "960"
    game.draw_stats()


# ── dibujo (smoke, SDL dummy) ──
def test_render_partida_960(game):
    game.set_variant("chess960", save=False)
    game.start_game("pvp")
    game.board = chess960.new_board(POS)
    for uci in PREP + ["e1h1"]:
        game.execute_move(chess.Move.from_uci(uci))
    game.anim_move = None
    game.selected_sq = chess.E8
    game.legal_moves_from = [m for m in game.board.legal_moves if m.from_square == chess.E8]
    game.draw()
    assert isinstance(game.screen, pygame.Surface)
    game.flip_board()
    game.draw()


def test_premove_de_enroque_960_a_la_casilla_del_rey(game):
    game.start_game("pvp")
    game.board = _prepared()
    game.premove_from, game.premove_to = chess.E1, chess.G1
    game.try_execute_premove()
    assert game.board.move_stack[-1] == chess.Move.from_uci("e1h1")
    assert game.premove_from is None
