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


def test_sin_imports_de_procesos_red_o_registro():
    for py in PKG.glob("*.py"):
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
