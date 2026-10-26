"""Tests de la búsqueda nueva del motor: límite de tiempo, quietud y MVV-LVA."""
import threading
import time

import chess

from cabrechess.engine import AI_TIME_LIMITS, SimpleEngine, ai_time_budget

# Medio juego de la auditoría (1.e4 e5 2.Cf3 Cc6 3.Ac4 Ac5 4.c3 Cf6 5.d4 exd4 6.cxd4 Ab4+)
MIDDLEGAME = "r1bqk2r/pppp1ppp/2n2n2/8/1bBPP3/5N2/PP3PPP/RNBQK2R w KQkq - 1 7"


def test_respeta_el_limite_de_tiempo():
    board = chess.Board(MIDDLEGAME)
    start = time.perf_counter()
    move = SimpleEngine().get_best_move(board, depth=8, time_limit=0.5)
    elapsed = time.perf_counter() - start
    assert move in board.legal_moves
    assert elapsed < 1.5, f"tardó {elapsed:.2f} s con límite de 0,5 s"


def test_dificil_no_tarda_mas_que_su_tope():
    board = chess.Board(MIDDLEGAME)
    start = time.perf_counter()
    move = SimpleEngine().get_best_move(board, depth=5, time_limit=AI_TIME_LIMITS[5])
    assert move in board.legal_moves
    assert time.perf_counter() - start < AI_TIME_LIMITS[5] + 1.0


def test_stop_event_corta_la_busqueda():
    board = chess.Board(MIDDLEGAME)
    stop = threading.Event()
    stop.set()
    start = time.perf_counter()
    move = SimpleEngine().get_best_move(board, depth=8, stop_event=stop)
    assert move in board.legal_moves      # siempre devuelve una jugada legal
    assert time.perf_counter() - start < 0.5


def test_no_modifica_el_tablero():
    board = chess.Board(MIDDLEGAME)
    fen = board.fen()
    SimpleEngine().search(board, depth=3, time_limit=0.3)
    assert board.fen() == fen


def test_quietud_no_cambia_dama_por_peon_defendido():
    # Dxd5 parece ganar un peón a profundidad 1, pero exd5 se come la dama.
    board = chess.Board("4k3/8/4p3/3p4/8/8/8/3QK3 w - - 0 1")
    for _ in range(5):
        assert SimpleEngine().get_best_move(board, depth=1) != chess.Move.from_uci("d1d5")


def test_come_la_pieza_colgada():
    board = chess.Board("4k3/8/8/3q4/8/8/8/3RK3 w - - 0 1")
    assert SimpleEngine().get_best_move(board, depth=1) == chess.Move.from_uci("d1d5")


def test_mvv_lva_ordena_las_capturas_primero():
    # Blancas pueden comer la dama con el peón o con la torre, o un peón con la torre.
    board = chess.Board("4k3/8/8/3q4/2P5/7p/8/3RK2R w - - 0 1")
    ordered = SimpleEngine().order_moves(board, list(board.legal_moves))
    assert ordered[0] == chess.Move.from_uci("c4d5")   # dama con peón
    assert ordered[1] == chess.Move.from_uci("d1d5")   # dama con torre
    assert board.is_capture(ordered[2])                # después el peón


def test_analyse_reporta_mate_desde_las_negras():
    board = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq g3 0 2")
    score, mate, move = SimpleEngine().analyse(board, depth=2)
    assert move == chess.Move.from_uci("d8h4")
    assert mate == -1 and score < 0


def test_elige_el_mate_mas_corto():
    # Ta8# es mate en 1; el motor no debe demorarlo aunque busque más profundo.
    board = chess.Board("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1")
    assert SimpleEngine().get_best_move(board, depth=4) == chess.Move.from_uci("a1a8")


def test_presupuesto_de_tiempo():
    assert ai_time_budget(1) == AI_TIME_LIMITS[1]
    assert ai_time_budget(5) == AI_TIME_LIMITS[5]
    # Con mucho reloj manda el tope del nivel.
    assert ai_time_budget(5, remaining=600, increment=3) == AI_TIME_LIMITS[5]
    # Con poco reloj piensa menos que lo que le queda.
    assert ai_time_budget(5, remaining=2, increment=3) <= 0.8
    assert ai_time_budget(5, remaining=0.01, increment=0) == 0.05
