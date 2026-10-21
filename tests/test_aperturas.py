"""Nombres de aperturas: tabla, transposiciones, PGN y panel lateral."""
import io

import chess
import chess.pgn

from cabrechess.openings import OPENINGS, opening_for_board, opening_label


def _board(sans):
    board = chess.Board()
    for san in sans.split():
        board.push_san(san)
    return board


def test_tabla_valida_y_sin_posiciones_repetidas():
    keys = set()
    for eco, name, line in OPENINGS:
        assert len(eco) == 3 and eco[0] in "ABCDE" and eco[1:].isdigit()
        assert name
        keys.add(_board(line).epd())   # falla si alguna jugada es ilegal
    assert len(keys) == len(OPENINGS)


def test_posicion_inicial_sin_apertura():
    assert opening_for_board(chess.Board()) is None
    assert opening_label(chess.Board()) == ""


def test_reconoce_aperturas_conocidas():
    assert opening_for_board(_board("e4 c5")) == ("B20", "Defensa Siciliana")
    assert opening_for_board(_board("e4 e5 Nf3 Nc6 Bb5"))[0] == "C60"
    assert opening_for_board(_board("e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6"))[1] == \
        "Defensa Siciliana: Variante Najdorf"
    assert opening_for_board(_board("d4 Nf6 c4 e6 Nc3 Bb4"))[1] == "Defensa Nimzo-India"


def test_se_queda_con_la_ultima_apertura_conocida():
    # Después de salir de la tabla se mantiene el último nombre reconocido
    board = _board("e4 c5 Nf3 d6 h3 a6 a3")
    assert opening_for_board(board) == ("B50", "Defensa Siciliana")


def test_transposicion():
    # 1.Nf3 d5 2.d4 Nf6 3.Bf4 llega al Sistema Londres de 1.d4 d5 2.Nf3 Nf6 3.Bf4
    assert opening_for_board(_board("Nf3 d5 d4 Nf6 Bf4")) == ("D02", "Sistema Londres")


def test_posicion_desde_fen_no_inventa_apertura():
    board = chess.Board("8/8/8/4k3/8/8/4P3/4K3 w - - 0 1")
    board.push_san("e4")
    assert opening_for_board(board) is None


def test_label():
    assert opening_label(_board("e4 e6")) == "C00 · Defensa Francesa"


def test_pgn_lleva_eco_y_opening(game):
    game.mode = "pvp"
    game.reset_game()
    for san in ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"]:
        game.execute_move(game.board.parse_san(san))
    pgn_text, _ = game.build_pgn()
    parsed = chess.pgn.read_game(io.StringIO(pgn_text))
    assert not parsed.errors
    assert parsed.headers["ECO"] == "C50"
    assert parsed.headers["Opening"] == "Apertura Italiana: Giuoco Piano"


def test_pgn_sin_apertura_no_agrega_headers(game):
    game.mode = "pvp"
    game.reset_game()
    pgn_text, _ = game.build_pgn()
    assert "[ECO" not in pgn_text and "[Opening" not in pgn_text


def test_panel_muestra_y_recorta_la_apertura(game):
    game.mode = "pvp"
    game.reset_game()
    assert game.opening_text(500) == ""
    for san in ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"]:
        game.execute_move(game.board.parse_san(san))
    full = game.opening_text(10_000)
    assert full == "B90 · Defensa Siciliana: Variante Najdorf"
    short = game.opening_text(120)
    assert short.endswith("…") and game.font_tiny.size(short)[0] <= 120
    game.draw()   # no rompe el dibujado del panel
