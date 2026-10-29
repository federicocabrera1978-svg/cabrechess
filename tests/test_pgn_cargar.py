"""B6: cargar PGN/FEN y exportar con chess.pgn."""
import io

import chess
import chess.pgn

from cabrechess.pgn import (
    parse_fen,
    parse_pgn,
    moves_from_game,
    read_pgn_file,
    write_pgn,
)


SAMPLE = """[Event "Test"]
[Site "CabreChess"]
[Date "2026.10.28"]
[White "A"]
[Black "B"]
[Result "1-0"]
[TimeControl "180+3"]
[Termination "normal"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0
"""


def test_parse_pgn_ok():
    game, err = parse_pgn(SAMPLE)
    assert err is None
    assert game.headers["White"] == "A"
    assert game.headers["Result"] == "1-0"
    assert len(moves_from_game(game)) == 7


def test_parse_pgn_vacio():
    game, err = parse_pgn("   ")
    assert game is None and "vacío" in err


def test_parse_fen_ok():
    board, err = parse_fen(chess.STARTING_FEN)
    assert err is None
    assert board.fen() == chess.STARTING_FEN


def test_parse_fen_invalido():
    board, err = parse_fen("no-es-un-fen")
    assert board is None and "inválido" in err.lower()


def test_build_pgn_incluye_timecontrol_y_termination(game):
    game.mode = "vsai"
    game.reset_game()
    game.execute_move(chess.Move.from_uci("e2e4"))
    game.execute_move(chess.Move.from_uci("e7e5"))
    game.end_game("timeout", "1-0")
    text, _ = game.build_pgn()
    parsed = chess.pgn.read_game(io.StringIO(text))
    assert parsed.headers["Result"] == "1-0"
    assert "TimeControl" in parsed.headers
    assert parsed.headers.get("Termination")


def test_build_pgn_roundtrip_moves(game):
    game.mode = "pvp"
    game.reset_game()
    for san in ["e4", "c5", "Nf3", "d6"]:
        game.execute_move(game.board.parse_san(san))
    text, _ = game.build_pgn()
    parsed = chess.pgn.read_game(io.StringIO(text))
    assert [m.uci() for m in parsed.mainline_moves()] == [
        m.uci() for m in game.board.move_stack
    ]


def test_load_pgn_text_abre_analisis(game, tmp_path):
    path = tmp_path / "m.pgn"
    write_pgn(SAMPLE, path)
    text, err = read_pgn_file(path)
    assert err is None
    assert game.load_pgn_text(text) is True
    assert game.mode == "analysis"
    assert game.board.is_checkmate()
    assert game.review_index == 0
    assert game.loaded_names == ("A", "B")


def test_load_fen_text(game):
    fen = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"
    assert game.load_fen_text(fen) is True
    assert game.mode == "analysis"
    assert game.board.fen() == chess.Board(fen).fen()
    assert game.review_index is None
