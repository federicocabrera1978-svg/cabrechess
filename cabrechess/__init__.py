# SPDX-License-Identifier: GPL-3.0-or-later
"""CabreChess - by Federico Cabrera. Ajedrez en pygame inspirado en Lichess.

Copyright (C) 2026 Federico Cabrera
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. See the LICENSE file for details.
"""
from ._version import __version__
from .engine import SimpleEngine
from .sprites import load_window_icon
from .ui import CabreChess, main

__all__ = ["CabreChess", "SimpleEngine", "load_window_icon", "main", "__version__"]
