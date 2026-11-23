"""Estadísticas locales (B11, parte 1): stats.json, Elo estimado y pantalla."""

import datetime
import json

import chess
import pygame
import pytest

from cabrechess import stats


@pytest.fixture
def datos(tmp_path, monkeypatch):
    """Carpeta de datos propia para cada test (stats.json vacío)."""
    monkeypatch.setenv("CABRECHESS_DATA_DIR", str(tmp_path))
    return tmp_path


def _partida(result="win", level=3, engine="cabrechess"):
    return {
        "date": "2026-11-23T10:00:00",
        "result": result,
        "level": level,
        "engine": engine,
        "color": "white",
        "time_control": "3+2",
        "termination": "checkmate",
    }


# ── Elo ──
def test_esperado_y_actualizacion_elo():
    assert stats.expected_score(1200, 1200) == pytest.approx(0.5)
    assert stats.expected_score(1600, 1200) == pytest.approx(0.909, abs=1e-3)
    # Mismo Elo: ganar suma K/2, perder resta K/2, tablas no cambia
    assert stats.update_elo(1200, 1200, 1) == pytest.approx(1200 + stats.K_FACTOR / 2)
    assert stats.update_elo(1200, 1200, 0) == pytest.approx(1200 - stats.K_FACTOR / 2)
    assert stats.update_elo(1200, 1200, 0.5) == pytest.approx(1200)
    # Ganarle a uno más fuerte suma más que a uno más débil
    assert stats.update_elo(1200, 1800, 1) - 1200 > stats.update_elo(1200, 600, 1) - 1200


def test_elo_estimado_por_partidas_y_niveles():
    assert stats.estimated_elo([]) == stats.START_ELO
    # Nivel 3 vale lo mismo que el Elo inicial: una victoria = +16
    assert stats.estimated_elo([_partida("win", 3)]) == 1216
    assert stats.estimated_elo([_partida("loss", 3)]) == 1184
    # Los niveles tienen Elo creciente y documentado
    elos = [stats.AI_LEVEL_ELO[lvl] for lvl in sorted(stats.AI_LEVEL_ELO)]
    assert elos == sorted(elos) and len(elos) == 6
    assert stats.opponent_elo(6, "stockfish") == stats.STOCKFISH_LEVEL_ELO[6]
    # El orden importa (se juega partida por partida)
    hist = stats.elo_history([_partida("win", 6), _partida("loss", 1)])
    assert len(hist) == 2 and hist[0] > 1200 and hist[1] < hist[0]


def test_resultado_desde_el_jugador():
    assert stats.player_result("1-0", True) == "win"
    assert stats.player_result("1-0", False) == "loss"
    assert stats.player_result("0-1", False) == "win"
    assert stats.player_result("1/2-1/2", True) == "draw"
    assert stats.player_result("*", True) is None


# ── persistencia ──
def test_ida_y_vuelta(datos):
    assert stats.stats_path() == datos / "stats.json"
    assert stats.load_stats() == stats.empty_stats()  # ausente = vacío
    fecha = datetime.datetime(2026, 11, 23, 9, 30, 5)
    stats.record_game("win", 2, "black", time_control="5+3", termination="checkmate", date=fecha)
    stats.record_game("draw", 4, "white", engine="stockfish", time_control="3+2")
    data = stats.load_stats()
    assert len(data["games"]) == 2
    g = data["games"][0]
    assert g == {
        "date": "2026-11-23T09:30:05",
        "result": "win",
        "level": 2,
        "engine": "cabrechess",
        "color": "black",
        "time_control": "5+3",
        "termination": "checkmate",
    }
    assert data["games"][1]["engine"] == "stockfish"
    assert json.loads((datos / "stats.json").read_text(encoding="utf-8"))["version"] == 1
    assert stats.reset_stats()
    assert stats.load_stats()["games"] == []


def test_datos_invalidos_no_se_registran(datos):
    assert stats.record_game("ganó", 3, "white") is None
    assert stats.record_game("win", 9, "white") is None
    assert not (datos / "stats.json").exists()


@pytest.mark.parametrize("contenido", ["{roto", "[]", '{"games": 3}', "\x00\x01"])
def test_archivo_corrupto(datos, contenido):
    p = datos / "stats.json"
    p.write_text(contenido, encoding="utf-8")
    assert stats.load_stats() == stats.empty_stats()  # nunca falla
    stats.record_game("loss", 1, "white")
    assert len(stats.load_stats()["games"]) == 1
    # El archivo roto no se pierde: queda apartado
    assert (datos / "stats.json.corrupto").read_text(encoding="utf-8") == contenido


def test_registros_rotos_se_descartan(datos):
    (datos / "stats.json").write_text(
        json.dumps(
            {
                "games": [
                    _partida("win", 3),
                    {"result": "win"},
                    "basura",
                    _partida("empate", 2),
                    _partida("draw", True),
                    {**_partida("loss", 5), "engine": "otro", "color": "azul"},
                ]
            }
        ),
        encoding="utf-8",
    )
    games = stats.load_stats()["games"]
    assert [g["result"] for g in games] == ["win", "loss"]
    assert games[1]["engine"] == "cabrechess" and games[1]["color"] == "white"


def test_resumen_por_nivel():
    s = stats.summarize(
        {"games": [_partida("win", 1), _partida("draw", 1), _partida("loss", 6), _partida("win", 3, "stockfish")]}
    )
    assert s["totals"] == {"win": 2, "draw": 1, "loss": 1, "played": 4, "score_pct": 62}
    assert s["by_level"][1]["played"] == 2 and s["by_level"][1]["score_pct"] == 75
    assert s["by_level"][6]["loss"] == 1 and s["by_level"][2]["played"] == 0
    assert s["by_level"][3]["played"] == 0  # la de Stockfish va aparte
    assert s["stockfish"]["win"] == 1
    assert s["provisional"] and s["elo"] == stats.estimated_elo(
        [_partida("win", 1), _partida("draw", 1), _partida("loss", 6), _partida("win", 3, "stockfish")]
    )
    assert s["recent"][0]["engine"] == "stockfish"  # la más nueva primero


# ── registro al terminar la partida ──
def _mate_de_blancas(game, ai_color=chess.BLACK):
    game.mode = "vsai"
    game.ai_color = ai_color
    game.ai_level = 4
    game.reset_game()
    game.board = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
    game.execute_move(chess.Move.from_uci("a1a8"))
    game.update()
    assert game.game_over and game.game_over_panel


def test_registra_victoria_vs_ia(game, datos):
    _mate_de_blancas(game)
    games = stats.load_stats()["games"]
    assert len(games) == 1
    g = games[0]
    assert (g["result"], g["level"], g["color"], g["engine"]) == ("win", 4, "white", "cabrechess")
    assert g["time_control"] == "3+2" and g["termination"] == "checkmate"
    game.update()  # no se cuenta dos veces
    game.undo_move()
    game.update()
    assert len(stats.load_stats()["games"]) == 1


def test_registra_derrota_con_negras_y_abandono(game, datos):
    _mate_de_blancas(game, ai_color=chess.WHITE)  # la IA (blancas) da mate
    game.mode = "vsai"
    game.ai_color = chess.BLACK
    game.reset_game()
    game.resign()
    game.update()
    results = [(g["result"], g["color"]) for g in stats.load_stats()["games"]]
    assert results == [("loss", "black"), ("loss", "white")]


def test_no_registra_pvp_ni_partidas_cargadas(game, datos):
    game.mode = "pvp"
    game.reset_game()
    game.board = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
    game.execute_move(chess.Move.from_uci("a1a8"))
    game.update()
    assert game.game_over
    game.mode = "vsai"
    game.load_pgn_text('[Result "1-0"]\n\n1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0')
    game.update()
    assert not (datos / "stats.json").exists()


# ── pantalla ──
def test_boton_menu_abre_pantalla_y_esc_vuelve(game, datos):
    game.mode = "menu"
    game.draw()
    game.handle_click(game.menu_stats_button()[1].center)
    assert game.mode == "stats"
    game.draw()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
    assert game.handle_events()
    assert game.mode == "menu"


def test_smoke_render_con_datos(game, datos):
    for i, (res, lvl) in enumerate([("win", 1), ("win", 2), ("draw", 3), ("loss", 5), ("win", 3)]):
        stats.record_game(res, lvl, "white" if i % 2 else "black", time_control="3+2")
    stats.record_game("loss", 6, "white", engine="stockfish")
    game.open_stats()
    game.draw()
    assert game.stats_summary["totals"]["played"] == 6
    labels = [r[1] for r in game._stats_rows(game.stats_summary)]
    assert labels[-1] == "Stockfish (todos)" and len(labels) == 7
    # Con el diálogo de confirmación abierto también dibuja
    game.ask_reset_stats()
    game.draw()


def test_pantalla_vacia(game, datos):
    game.open_stats()
    game.draw()
    game.ask_reset_stats()  # nada para borrar: no abre diálogo
    assert game.confirm is None


def test_reiniciar_pide_confirmacion(game, datos):
    stats.record_game("win", 3, "white")
    game.open_stats()
    reset = {a: r for _l, a, _c, r in game.stats_buttons()}["reset"]
    game.handle_click(reset.center)
    assert game.confirm and "Reiniciar" in game.confirm["title"]
    # Cancelar no borra
    cancelar = [r for label, _a, r in game.confirm_buttons() if label == "Cancelar"][0]
    game.handle_click(cancelar.center)
    assert game.confirm is None and len(stats.load_stats()["games"]) == 1
    # Esc con el diálogo abierto lo cierra sin salir de la pantalla
    game.handle_click(reset.center)
    game.handle_stats_key(pygame.K_ESCAPE)
    assert game.confirm is None and game.mode == "stats"
    # Confirmar borra todo
    game.handle_click(reset.center)
    borrar = [r for label, _a, r in game.confirm_buttons() if label == "Borrar todo"][0]
    game.handle_click(borrar.center)
    assert stats.load_stats()["games"] == []
    assert game.stats_summary["totals"]["played"] == 0
    back = {a: r for _l, a, _c, r in game.stats_buttons()}["back"]
    game.handle_click(back.center)
    assert game.mode == "menu"
