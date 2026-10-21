"""Tests del motor (SimpleEngine) y de la exportación PGN."""
import io
import random

import chess
import chess.pgn
import pytest

import cabrechess

MATE_IN_ONE = [
    # Mate del pasillo: Ra8#
    ("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1", "a1a8"),
    # Mate del pastor: Qxf7#
    ("r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "h5f7"),
    # Negras dan mate: Qh4# (mate del loco)
    ("rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq g3 0 2", "d8h4"),
]


@pytest.mark.parametrize("fen,expected", MATE_IN_ONE)
@pytest.mark.parametrize("depth", [1, 2, 3])
def test_engine_finds_mate_in_one(fen, expected, depth):
    board = chess.Board(fen)
    move = cabrechess.SimpleEngine().get_best_move(board, depth=depth)
    assert move is not None
    board.push(move)
    assert board.is_checkmate(), f"{move.uci()} no da mate (esperado {expected})"


def test_engine_never_returns_illegal_move():
    rng = random.Random(1234)
    engine = cabrechess.SimpleEngine()
    for _ in range(15):
        board = chess.Board()
        for _ in range(rng.randint(0, 40)):
            if board.is_game_over():
                break
            board.push(rng.choice(list(board.legal_moves)))
        if board.is_game_over():
            continue
        fen = board.fen()
        move = engine.get_best_move(board, depth=2)
        assert board.fen() == fen, "el motor no debe modificar el tablero"
        assert move in board.legal_moves


def test_engine_handles_promotion_position():
    board = chess.Board("8/P6k/8/8/8/8/8/K7 w - - 0 1")
    move = cabrechess.SimpleEngine().get_best_move(board, depth=2)
    assert move in board.legal_moves
    assert move.promotion == chess.QUEEN


def _play(game, sans):
    for san in sans:
        move = game.board.parse_san(san)
        game.execute_move(move)


def test_exported_pgn_reparses(game):
    game.mode = "pvp"
    game.reset_game()
    sans = ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "O-O", "Nf6", "d3", "d6"]
    _play(game, sans)
    pgn_text, _ = game.build_pgn()
    parsed = chess.pgn.read_game(io.StringIO(pgn_text))
    assert parsed is not None
    assert not parsed.errors
    assert [m for m in parsed.mainline_moves()] == list(game.board.move_stack)
    assert parsed.headers["Result"] == "*"


def test_exported_pgn_checkmate_result(game):
    game.mode = "pvp"
    game.reset_game()
    _play(game, ["f3", "e5", "g4", "Qh4#"])
    pgn_text, _ = game.build_pgn()
    parsed = chess.pgn.read_game(io.StringIO(pgn_text))
    assert parsed.headers["Result"] == "0-1"
    assert parsed.end().board().is_checkmate()
