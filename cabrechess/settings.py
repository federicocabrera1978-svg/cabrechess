# SPDX-License-Identifier: GPL-3.0-or-later
"""Carpeta de datos del usuario y configuración (settings.json).

- Windows: %APPDATA%\\CabreChess
- Otros / sin APPDATA: ~/.cabrechess
- Se puede forzar con la variable de entorno CABRECHESS_DATA_DIR.

settings.json (opcional):
    {"stockfish_path": "C:/ruta/a/stockfish.exe", "analysis_depth": 3}
stockfish_path vacío (por defecto) = se usa solo el motor propio, dentro del
proceso. También se puede definir con la variable CABRECHESS_STOCKFISH.
"""
import json
import os
import sys
from pathlib import Path

DEFAULTS = {"stockfish_path": "", "analysis_depth": 3}


def data_dir():
    override = os.environ.get("CABRECHESS_DATA_DIR")
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")
    if sys.platform == "win32" and appdata:
        return Path(appdata) / "CabreChess"
    return Path.home() / ".cabrechess"


def settings_path():
    return data_dir() / "settings.json"


def load_settings(path=None):
    cfg = dict(DEFAULTS)
    path = Path(path) if path else settings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    env = os.environ.get("CABRECHESS_STOCKFISH")
    if env:
        cfg["stockfish_path"] = env
    try:
        cfg["analysis_depth"] = max(1, min(5, int(cfg["analysis_depth"])))
    except (TypeError, ValueError):
        cfg["analysis_depth"] = DEFAULTS["analysis_depth"]
    return cfg
