"""Tests del reloj (incremento y bandera) y del deshacer completo."""
import chess


def jugar(g, *sans):
    for san in sans:
        g.execute_move(g.board.parse_san(san))


# ─── Reloj ──────────────────────────────────────────────────────────────────

def test_incremento_en_la_primera_jugada(game):
    game.start_game("pvp")
    game.time_white = 100.0
    jugar(game, "e4")
    assert game.time_white == 100.0 + game.time_increment


def test_incremento_sin_tope(game):
    game.start_game("pvp")
    game.time_white = game.time_selected + 60      # el tope viejo
    jugar(game, "e4")
    assert game.time_white == game.time_selected + 60 + game.time_increment


def test_bandera_con_material_gana(game):
    game.start_game("pvp")
    game.flag_fall(chess.WHITE)
    assert game.game_over
    assert "Ganan las negras por tiempo" in game.game_over_msg


def test_bandera_contra_material_insuficiente_es_tablas(game):
    game.start_game("pvp")
    # Blancas: rey y dama. Negras: rey solo. A blancas se les cae la bandera:
    # negras no pueden dar mate nunca, así que es tablas.
    game.board = chess.Board("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")
    game.flag_fall(chess.WHITE)
    assert game.game_over
    assert "Tablas por tiempo" in game.game_over_msg
    # Al revés: a negras se les cae y blancas tienen dama, ganan blancas.
    game.reset_game()
    game.board = chess.Board("4k3/8/8/8/8/8/8/3QK3 b - - 0 1")
    game.flag_fall(chess.BLACK)
    assert "Ganan las blancas por tiempo" in game.game_over_msg


def test_bandera_desde_update(game):
    game.start_game("pvp")
    game.time_white = 0.0001
    game.time_last -= 1
    game.update()
    assert game.game_over and "Ganan las negras por tiempo" in game.game_over_msg


# ─── Deshacer ───────────────────────────────────────────────────────────────

def test_deshacer_restaura_capturas_y_relojes(game):
    game.start_game("pvp")
    jugar(game, "e4", "d5")
    tw, tb = game.time_white, game.time_black
    jugar(game, "exd5")
    assert len(game.captured_black) == 1
    assert game.time_white != tw
    game.undo_move()
    assert game.captured_black == []
    assert game.time_white == tw and game.time_black == tb
    assert game.move_history_san == ["e4", "d5"]
    assert len(game.undo_stack) == 2


def test_deshacer_borra_premove(game):
    game.start_game("pvp")
    jugar(game, "e4", "e5")
    game.premove_from, game.premove_to = chess.E2, chess.E4
    game.undo_move()
    assert game.premove_from is None and game.premove_to is None


def test_deshacer_tras_el_mate_no_reabre_la_partida(game):
    game.start_game("pvp")
    jugar(game, "f3", "e5", "g4", "Qh4#")
    assert game.game_over
    msg = game.game_over_msg
    game.undo_move()
    assert game.game_over and game.game_over_msg == msg
    assert len(game.board.move_stack) == 4


def test_deshacer_en_analisis_restaura_evaluacion(game):
    game.start_game("analysis")
    jugar(game, "e4", "e5", "Qh5", "Nc6")
    hist = list(game.eval_history)
    score = game.eval_score
    jugar(game, "Qxf7#")
    assert len(game.eval_history) == 5 and len(game.captured_black) == 1
    game.undo_move()
    assert game.eval_history == hist
    assert game.eval_score == score
    assert game.captured_black == []


def test_deshacer_vs_ia_vuelve_al_turno_del_jugador(game):
    game.player_color_choice = "white"
    game.start_game("vsai")
    jugar(game, "e4")
    # Simular la respuesta de la IA sin esperar al hilo
    game.ai_thinking = False
    game.ai_search_id += 1
    jugar(game, "e5")
    game.ai_thinking = False
    game.undo_move()
    assert game.board.move_stack == []
    assert game.board.turn == chess.WHITE
    assert not game.ai_thinking


def test_deshacer_mientras_piensa_la_ia_cancela_la_busqueda(game):
    game.player_color_choice = "white"
    game.start_game("vsai")
    jugar(game, "e4")             # lanza la búsqueda de la IA
    assert game.ai_thinking
    search_id = game.ai_search_id
    game.undo_move()
    assert game.ai_search_id > search_id     # el resultado viejo se descarta
    assert not game.ai_thinking
    assert game.board.move_stack == []


def test_reiniciar_vacia_la_pila_de_deshacer(game):
    game.start_game("pvp")
    jugar(game, "e4", "e5")
    game.reset_game()
    assert game.undo_stack == []


def test_deshacer_con_negras_vuelve_a_jugar_la_ia(game):
    game.player_color_choice = "black"
    game.start_game("vsai")
    assert game.ai_color == chess.WHITE and game.ai_thinking
    game.ai_thinking = False
    game.ai_search_id += 1
    jugar(game, "d4")             # "jugada de la IA"
    jugar(game, "d5")             # jugada del jugador -> lanza la IA
    game.undo_move()
    # Vuelve a la posición después de 1.d4, con el turno del jugador (negras)
    assert [m.uci() for m in game.board.move_stack] == ["d2d4"]
    assert game.board.turn == chess.BLACK and not game.ai_thinking
