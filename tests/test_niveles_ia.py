# SPDX-License-Identifier: GPL-3.0-or-later
"""B3, parte 2: PST para todas las piezas y 6 niveles de IA."""
import random

import chess
import pytest

from cabrechess.engine import AI_LEVELS, AI_TIME_LIMITS, DEFAULT_AI_LEVEL, SimpleEngine, ai_level, ai_time_budget


def test_hay_seis_niveles_ordenados():
    assert sorted(AI_LEVELS) == [1, 2, 3, 4, 5, 6]
    depths = [AI_LEVELS[n]["depth"] for n in range(1, 7)]
    times = [AI_LEVELS[n]["time"] for n in range(1, 7)]
    noises = [AI_LEVELS[n]["noise"] for n in range(1, 7)]
    assert depths == sorted(depths) and times == sorted(times)
    assert noises == sorted(noises, reverse=True)
    assert AI_LEVELS[6]["noise"] == 0
    assert len({cfg["name"] for cfg in AI_LEVELS.values()}) == 6


def test_nivel_desconocido_usa_el_por_defecto():
    assert ai_level(99) == AI_LEVELS[DEFAULT_AI_LEVEL]
    assert ai_time_budget(99) == AI_TIME_LIMITS[DEFAULT_AI_LEVEL]


def test_pst_cubre_todas_las_piezas():
    for piece_type in chess.PIECE_TYPES:
        assert len(SimpleEngine.PST[piece_type]) == 64
    assert len(SimpleEngine.KING_ENDGAME_PST) == 64


def test_pst_es_simetrica_para_ambos_colores():
    engine = SimpleEngine()
    board = chess.Board()
    assert engine._material_pst(board) == 0
    board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    assert engine._material_pst(board) == -engine._material_pst(board.mirror())


def test_alfil_centralizado_vale_mas_que_en_el_rincon():
    engine = SimpleEngine()
    centro = chess.Board("4k3/8/8/8/3B4/8/8/4K3 w - - 0 1")
    rincon = chess.Board("4k3/8/8/8/8/8/8/B3K3 w - - 0 1")
    assert engine._material_pst(centro) > engine._material_pst(rincon)


def test_rey_va_al_centro_en_el_final_y_se_esconde_en_el_medio_juego():
    engine = SimpleEngine()
    final = chess.Board("4k3/8/8/8/3K4/8/8/8 w - - 0 1")
    assert SimpleEngine.is_endgame(final)
    assert engine._material_pst(final) > engine._material_pst(chess.Board("4k3/8/8/8/8/8/8/K7 w - - 0 1"))
    medio = chess.Board()
    assert not SimpleEngine.is_endgame(medio)
    enrocado = chess.Board("r1bq1rk1/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 w - - 6 5")
    sin_enrocar = chess.Board("r1bq1rk1/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPPKPPP/RNBQ3R w - - 6 5")
    assert engine._material_pst(enrocado) > engine._material_pst(sin_enrocar)


@pytest.mark.parametrize("level", range(1, 7))
def test_todos_los_niveles_dan_jugada_legal_sin_tocar_el_tablero(level):
    board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    fen = board.fen()
    move = SimpleEngine().play_level(board, level, time_limit=0.2, rng=random.Random(level))
    assert move in board.legal_moves
    assert board.fen() == fen


@pytest.mark.parametrize("level", range(1, 7))
def test_todos_los_niveles_dan_mate_en_uno(level):
    # El ruido de los niveles bajos no alcanza para tapar un mate.
    board = chess.Board("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1")
    for seed in range(5):
        move = SimpleEngine().play_level(board, level, time_limit=0.3, rng=random.Random(seed))
        assert move == chess.Move.from_uci("a1a8")


def test_niveles_bajos_varian_y_altos_no_tiran_material():
    # Posición donde capturar la dama es claramente lo mejor.
    board = chess.Board("4k3/8/8/3q4/8/8/8/3QK3 w - - 0 1")
    best = chess.Move.from_uci("d1d5")
    for seed in range(5):
        assert SimpleEngine().play_level(board, 6, time_limit=0.3, rng=random.Random(seed)) == best
    start = chess.Board()
    jugadas = {SimpleEngine().play_level(start, 1, rng=random.Random(seed)) for seed in range(12)}
    assert len(jugadas) >= 3, "el nivel 1 debería variar sus aperturas"


def test_ruido_cero_no_cambia_la_busqueda():
    board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    e = SimpleEngine()
    s1 = e.search(board, 2, noise=0, rng=random.Random(1))[0]
    s2 = e.search(board, 2, rng=random.Random(2))[0]
    assert s1 == s2


def test_menu_tiene_seis_botones_de_nivel(game):
    label, _y, _acc, options = game.menu_option_rows()[0]
    assert label == "Nivel IA:"
    assert [value for _t, _r, _s, value in options] == [1, 2, 3, 4, 5, 6]
    assert [sel for _t, _r, sel, _v in options] == [v == DEFAULT_AI_LEVEL for v in range(1, 7)]
    game.handle_menu_click(options[5][1].center)
    assert game.ai_level == 6
    game.mode = "vsai"
    assert game.mode_label() == "vs IA (nivel 6)"
