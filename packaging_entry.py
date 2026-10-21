# SPDX-License-Identifier: GPL-3.0-or-later
"""Script de entrada para PyInstaller (CabreChess.spec).
PyInstaller necesita un script, no un paquete con imports relativos."""
from cabrechess.ui import main

if __name__ == "__main__":
    main()
