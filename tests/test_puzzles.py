"""Puzzle del día (B10, parte 2): base de Lichess, validación y progreso."""

import datetime
import json

import chess
import pygame

from cabrechess import puzzles, settings
from cabrechess.puzzles import (
    Puzzle,
    PuzzleSession,
    current_streak,
    daily_index,
    load_progress,
    load_puzzles,
    puzzle_of_the_day,
    random_puzzle,
    record_solved,
    save_progress,
)

DAY = datetime.date(2026, 11, 18)


def _by_id(pid):
    return next(p for p in load_puzzles() if p.id == pid)


def _solve(session):
    while not session.solved:
        result = session.try_move(session.expected_move)
        assert result in ("correct", "solved")
        if result == "correct":
            session.opponent_reply()


# ─── carga ────────────────────────────────────────────────────────────────────
def test_carga_los_puzzles_de_lichess():
    ps = load_puzzles()
    assert 50 <= len(ps) <= 100
    assert len({p.id for p in ps}) == len(ps)
    for p in ps:
        assert 800 <= p.rating <= 2000
        assert p.game_url.startswith("https://lichess.org/")
        board = chess.Board(p.fen)
        for uci in p.moves:  # todas las jugadas son legales en orden
            move = chess.Move.from_uci(uci)
            assert move in board.legal_moves, (p.id, uci)
            board.push(move)
    themes = {t for p in ps for t in p.themes}
    assert {"mateIn1", "mateIn2", "fork", "pin"} <= themes


def test_el_csv_cita_la_fuente_cc0():
    head = puzzles.PUZZLES_CSV.read_text(encoding="utf-8").splitlines()[:2]
    assert "database.lichess.org" in head[0] and "CC0" in head[1]


def test_carga_ignora_filas_rotas(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text(
        "# comentario\nPuzzleId,FEN,Moves,Rating,Themes,GameUrl\n"
        "a,8/8/8/8/8/8/8/K6k w - - 0 1,a1a2,1000,x,u\n"  # una sola jugada
        "b,8/8/8/8/8/8/8/K6k w - - 0 1,a1a2 h1h2,mil,x,u\n"  # rating inválido
        "c,8/8/8/8/8/8/8/K6k w - - 0 1,a1a2 h1h2,1000,fork pin,u\n",
        encoding="utf-8",
    )
    ps = load_puzzles(f)
    assert [p.id for p in ps] == ["c"] and ps[0].themes == ("fork", "pin")


# ─── puzzle del día ───────────────────────────────────────────────────────────
def test_puzzle_del_dia_es_deterministico_y_rota():
    ps = load_puzzles()
    assert puzzle_of_the_day(ps, DAY) == puzzle_of_the_day(ps, DAY)
    assert puzzle_of_the_day(ps, DAY) != puzzle_of_the_day(ps, DAY + datetime.timedelta(days=1))
    week = {daily_index(DAY + datetime.timedelta(days=i), len(ps)) for i in range(len(ps))}
    assert week == set(range(len(ps)))  # en len(ps) días pasan todos


def test_otro_puzzle_prefiere_no_resueltos():
    ps = load_puzzles()[:3]
    import random

    rng = random.Random(1)
    for _ in range(20):
        assert random_puzzle(ps, solved={ps[0].id, ps[1].id}, rng=rng) == ps[2]
    # todos resueltos: igual devuelve uno distinto del actual
    assert random_puzzle(ps, solved={p.id for p in ps}, exclude=ps[0].id, rng=rng) != ps[0]


# ─── validación de jugadas ────────────────────────────────────────────────────
def test_rival_juega_la_primera_y_el_usuario_mueve():
    p = _by_id("1GKdV")  # mate en 2 de la base: b6d6 f4f7 g8h8 f7g7
    s = PuzzleSession(p)
    assert s.board.peek() == chess.Move.from_uci("b6d6")
    assert s.player_color == chess.WHITE and s.board.turn == chess.WHITE
    assert s.try_move(chess.Move.from_uci("f4f6")) == "wrong" and s.mistakes == 1
    assert s.try_move(chess.Move.from_uci("f4f7")) == "correct"
    assert s.awaiting_opponent
    assert s.try_move(chess.Move.from_uci("f7g7")) == "wrong"  # no es su turno
    assert s.opponent_reply() == chess.Move.from_uci("g8h8")
    assert s.try_move(chess.Move.from_uci("f7g7")) == "solved"
    assert s.board.is_checkmate() and s.solved and not s.clean


def test_todos_los_puzzles_se_pueden_resolver():
    for p in load_puzzles():
        s = PuzzleSession(p)
        _solve(s)
        assert s.clean


def test_acepta_otro_mate_en_1():
    # Posición de prueba (no es parte del set): Ta8# y Dd8# son mate.
    p = Puzzle("t", "7k/5ppp/8/8/8/8/5PPP/R2Q2K1 b - - 0 1", ("f7f6", "a1a8"), 1000, ("mateIn1",), "")
    s = PuzzleSession(p)
    assert s.try_move(chess.Move.from_uci("d1d8")) == "solved"
    assert s.board.is_checkmate()


def test_pista_solucion_y_coronacion():
    s = PuzzleSession(_by_id("1P3Fs"))  # e8c7 f2e3 d1d2 e2e1q (corona)
    assert s.player_color == chess.BLACK
    assert s.hint_square() == chess.F2 and s.hint_used
    assert s.try_move(chess.Move.from_uci("f2e3")) == "correct"
    s.opponent_reply()
    assert s.promotion_for(chess.E2, chess.E1) == chess.QUEEN
    assert s.show_solution() == chess.Move.from_uci("e2e1q") and s.solution_shown
    assert s.try_move(chess.Move.from_uci("e2e1q")) == "solved" and not s.clean


# ─── progreso / racha ─────────────────────────────────────────────────────────
def test_racha_y_resueltos():
    prog = puzzles.default_progress()
    prog = record_solved(prog, "a", daily=True, date=DAY)
    assert prog["streak"] == 1 and prog["solved"] == ["a"]
    prog = record_solved(prog, "a", daily=True, date=DAY)  # mismo día: no suma
    assert prog["streak"] == 1 and prog["solved"] == ["a"]
    prog = record_solved(prog, "b", daily=True, date=DAY + datetime.timedelta(days=1))
    assert prog["streak"] == 2 and prog["best_streak"] == 2
    prog = record_solved(prog, "c")  # otro puzzle: no toca la racha
    assert prog["streak"] == 2 and prog["solved"] == ["a", "b", "c"]
    prog = record_solved(prog, "d", daily=True, date=DAY + datetime.timedelta(days=5))
    assert prog["streak"] == 1 and prog["best_streak"] == 2
    assert current_streak(prog, DAY + datetime.timedelta(days=6)) == 1
    assert current_streak(prog, DAY + datetime.timedelta(days=7)) == 0


def test_progreso_se_guarda_en_settings_json(tmp_path):
    f = tmp_path / "settings.json"
    f.write_text(json.dumps({"sound": False}), encoding="utf-8")
    assert load_progress(f) == puzzles.default_progress()
    prog = record_solved(puzzles.default_progress(), "00008", daily=True, date=DAY)
    assert save_progress(prog, f)
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["sound"] is False  # conserva el resto
    assert load_progress(f) == prog
    f.write_text(json.dumps({"puzzles": {"solved": "x", "streak": "mal"}}), encoding="utf-8")
    assert load_progress(f) == puzzles.default_progress()
    assert settings.load_settings(f)["sound"] is True  # la clave no rompe load_settings


# ─── pantalla (pygame sin ventana) ────────────────────────────────────────────
def _click_sq(game, uci_sq):
    game.handle_click(game.center_of_sq(chess.parse_square(uci_sq)))


def test_menu_abre_el_puzzle_del_dia(game):
    game.handle_click(game.menu_puzzle_button()[1].center)
    assert game.mode == "puzzle" and game.puzzle_daily
    assert game.puzzle.puzzle == puzzle_of_the_day(game.puzzle_list())
    game.draw()  # smoke: dibuja sin errores
    game.handle_puzzle_key(pygame.K_ESCAPE)
    assert game.mode == "menu"


def test_pantalla_jugar_respuesta_y_resolver(game):
    game.open_puzzle(puzzle=_by_id("1GKdV"), today=DAY)
    assert not game.flipped and not game.puzzle_daily
    _click_sq(game, "f4")
    _click_sq(game, "f6")
    assert game.puzzle_feedback == "wrong"
    _click_sq(game, "f4")
    _click_sq(game, "f7")
    assert game.puzzle_feedback == "correct" and game.puzzle_reply_at is not None
    game.draw()
    game.puzzle_tick(now=game.puzzle_reply_at + 0.01)  # responde el rival
    assert game.puzzle.board.peek() == chess.Move.from_uci("g8h8")
    _click_sq(game, "f7")
    _click_sq(game, "g7")
    assert game.puzzle_feedback == "solved"
    assert "1GKdV" in load_progress()["solved"]
    game.draw()


def test_pantalla_pista_solucion_y_otro(game):
    game.open_puzzle(daily=True, today=DAY)
    first = game.puzzle.puzzle
    actions = {a: r for _l, a, _c, r in game.puzzle_buttons()}
    game.handle_click(actions["hint"].center)
    assert game.puzzle_hint_sq == game.puzzle.expected_move.from_square
    game.handle_click(actions["solution"].center)
    assert game.puzzle.solution_shown and game.puzzle_arrow is not None
    game.draw()
    game.handle_click(actions["next"].center)
    assert game.puzzle.puzzle != first and not game.puzzle_daily
    game.handle_click(actions["menu"].center)
    assert game.mode == "menu"


def test_negras_ven_su_bando_abajo(game):
    p = next(q for q in load_puzzles() if chess.Board(q.fen).turn == chess.WHITE)
    game.open_puzzle(puzzle=p)
    assert game.puzzle.player_color == chess.BLACK and game.flipped
