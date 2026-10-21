"""Sonidos: qué suena en cada jugada, silencio al cargar partidas y tecla M."""
import json

import chess

from cabrechess.settings import load_settings, save_setting, settings_path
from cabrechess.sounds import SoundManager, sound_for_move


def _kind(fen, uci):
    board = chess.Board(fen)
    move = chess.Move.from_uci(uci)
    after = board.copy()
    after.push(move)
    return sound_for_move(board, move, after)


def test_tipo_de_sonido_por_jugada():
    assert _kind(chess.STARTING_FEN, "e2e4") == "move"
    # captura
    assert _kind("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", "e4d5") == "capture"
    # enroque corto
    assert _kind("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1") == "castle"
    # jaque
    assert _kind("4k3/8/8/8/8/8/8/R3K3 w - - 0 1", "a1a8") == "check"
    # mate del pastor
    fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 4 4"
    assert _kind(fen, "f3f7") == "end"


def test_sound_manager_genera_sonidos_y_silencia(game):
    sm = SoundManager(enabled=True)
    if sm.available:
        assert {"move", "capture", "castle", "check", "end", "low_time"} <= set(sm.sounds)
        assert sm.play("move") is True
    assert sm.toggle() is False
    assert sm.play("move") is False


def test_jugadas_reproducen_sonido(game, monkeypatch):
    played = []
    monkeypatch.setattr(game.sound, "play", lambda name: played.append(name) or True)
    game.start_game("pvp")
    game.execute_move(chess.Move.from_uci("e2e4"))
    game.execute_move(chess.Move.from_uci("d7d5"))
    game.execute_move(chess.Move.from_uci("e4d5"))
    assert played == ["move", "move", "capture"]


def test_fin_por_tiempo_suena_una_vez(game, monkeypatch):
    played = []
    monkeypatch.setattr(game.sound, "play", lambda name: played.append(name) or True)
    game.start_game("pvp")
    game.flag_fall(chess.WHITE)
    game.flag_fall(chess.WHITE)
    assert played.count("end") == 1


def test_aviso_de_reloj_bajo_una_sola_vez(game, monkeypatch):
    played = []
    monkeypatch.setattr(game.sound, "play", lambda name: played.append(name) or True)
    game.start_game("pvp")
    game.time_white = 9.5
    game.check_low_time()
    game.check_low_time()
    assert played == ["low_time"]


def test_tecla_m_guarda_preferencia(game):
    before = game.sound.enabled
    assert game.toggle_sound() is (not before)
    assert load_settings()["sound"] is (not before)
    game.toggle_sound()
    assert load_settings()["sound"] is before


def test_save_setting_conserva_otras_claves(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"analysis_depth": 4}), encoding="utf-8")
    assert save_setting("sound", False, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"analysis_depth": 4, "sound": False}
    assert load_settings(path)["sound"] is False
    assert settings_path().name == "settings.json"


def test_cargar_partida_guardada_es_silencioso(game, monkeypatch):
    game.start_game("pvp")
    for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
        game.execute_move(chess.Move.from_uci(uci))
    game.sync_game_over_panel()          # autoguarda la partida terminada
    gid = game.saved_game_id
    assert gid is not None
    played = []
    monkeypatch.setattr(game.sound, "play", lambda name: played.append(name) or True)
    assert game.load_saved_game(gid)
    assert played == []
    assert game.silent is False
