# SPDX-License-Identifier: GPL-3.0-or-later
"""Extrae del CHANGELOG las notas de una versión para el Release de GitHub.

Uso: python tools/release_notes.py v1.1.0 [release_notes.md]

Sin archivo de salida imprime las notas. El archivo se escribe en UTF-8
(en Windows la consola no siempre soporta emojis).
Falla si la etiqueta no coincide con ``cabrechess.__version__`` o si el
CHANGELOG no tiene la sección ``## [X.Y.Z]``.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def code_version():
    text = (ROOT / "cabrechess" / "_version.py").read_text(encoding="utf-8")
    return re.search(r'__version__\s*=\s*"([^"]+)"', text).group(1)


def changelog_section(version, changelog=None):
    if changelog is None:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    lines = changelog.splitlines()
    out, inside = [], False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = line.startswith(f"## [{version}]")
            continue
        if inside:
            if re.match(r"^\[[^\]]+\]: ", line):  # links del pie
                break
            out.append(line)
    if not inside and not out:
        raise SystemExit(f"CHANGELOG.md no tiene la sección ## [{version}]")
    return "\n".join(out).strip() + "\n"


def main(argv):
    if len(argv) not in (2, 3):
        raise SystemExit(__doc__)
    version = argv[1].removeprefix("v")
    if version != code_version():
        raise SystemExit(f"La etiqueta v{version} no coincide con __version__ = {code_version()}")
    notes = changelog_section(version)
    if len(argv) == 3:
        Path(argv[2]).write_text(notes, encoding="utf-8")
    else:
        sys.stdout.buffer.write(notes.encode("utf-8"))


if __name__ == "__main__":
    main(sys.argv)
