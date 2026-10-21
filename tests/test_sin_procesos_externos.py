"""El juego (incluido el análisis) corre 100% en el proceso: no lanza
subprocesos, no usa motores externos, red ni registro. Esto evita
heurísticas de antivirus sobre el .exe de PyInstaller."""
import ast
from pathlib import Path

import chess

import cabrechess

PKG = Path(cabrechess.__file__).resolve().parent
PROHIBIDOS = {"subprocess", "multiprocessing", "chess.engine", "socket", "urllib",
              "http", "winreg", "tempfile", "shutil", "webbrowser", "pty", "signal"}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module


# Único módulo que puede lanzar un proceso: el backend OPCIONAL de Stockfish,
# que solo se importa si el usuario configuró stockfish_path.
OPCIONAL_STOCKFISH = "stockfish.py"


def test_sin_imports_de_procesos_red_o_registro():
    for py in PKG.glob("*.py"):
        if py.name == OPCIONAL_STOCKFISH:
            continue
        for mod in _imports(py):
            root = mod.split(".")[0]
            assert mod not in PROHIBIDOS and root not in PROHIBIDOS, f"{py.name} importa {mod}"


def test_sin_llamadas_a_exec_o_os_system():
    malos = {"system", "popen", "startfile", "execv", "execl", "spawnv", "spawnl", "exec", "eval"}
    for py in PKG.glob("*.py"):
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                f = node.func
                name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", "")
                assert name not in malos, f"{py.name}:{node.lineno} llama a {name}()"


def test_ctypes_solo_para_dpi_en_windows():
    for py in PKG.glob("*.py"):
        if "ctypes" in py.read_text(encoding="utf-8"):
            assert py.name == "display.py", py.name


def test_analisis_es_en_proceso(game):
    game.start_game("analysis")
    game.execute_move(chess.Move.from_uci("e2e4"))
    assert game.mode == "analysis"
    assert isinstance(game.eval_score, (int, float))
    assert game.ai_thread is None          # el análisis no lanza la IA


def test_stockfish_no_se_carga_por_defecto(tmp_path):
    # Intérprete limpio: el análisis por defecto no importa el backend de
    # Stockfish ni chess.engine (que lanza procesos).
    import os
    import subprocess
    import sys
    code = (
        "import sys, chess, cabrechess\n"
        "g = cabrechess.CabreChess(); g.start_game('analysis')\n"
        "g.execute_move(chess.Move.from_uci('e2e4')); g.update()\n"
        "r = g.get_analyzer().wait(g.board, timeout=60)\n"
        "assert r is not None and r.engine == 'CabreChess', r\n"
        "assert 'cabrechess.stockfish' not in sys.modules\n"
        "assert 'chess.engine' not in sys.modules\n"
        "print('ok')\n")
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
               CABRECHESS_DATA_DIR=str(tmp_path), PYTHONPATH=str(PKG.parent))
    env.pop("CABRECHESS_STOCKFISH", None)
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True,
                         text=True, timeout=120)
    assert out.returncode == 0 and "ok" in out.stdout, out.stderr


def test_stockfish_solo_importa_chess_engine_y_es_lazy():
    src = (PKG / OPCIONAL_STOCKFISH).read_text(encoding="utf-8")
    assert "popen_uci" in src
    for py in PKG.glob("*.py"):
        if py.name != OPCIONAL_STOCKFISH:
            assert "from .stockfish import" not in py.read_text(encoding="utf-8") or py.name == "analysis.py"
