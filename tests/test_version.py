"""La versión sale de un solo lugar y coincide en menú, .exe y CHANGELOG."""
import re
import sys
from pathlib import Path

import cabrechess
from cabrechess.ui import menu_version_text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import release_notes  # noqa: E402


def test_version_es_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", cabrechess.__version__)


def test_menu_muestra_version_del_paquete():
    assert menu_version_text().startswith(f"v{cabrechess.__version__} ")


def test_menu_dibuja_sin_errores(game):
    game.draw_menu()


def test_version_info_del_exe_coincide():
    text = (ROOT / "version_info.txt").read_text(encoding="utf-8")
    nums = ",".join(cabrechess.__version__.split(".") + ["0"])
    compact = text.replace(" ", "")
    assert f"filevers=({nums})" in compact
    assert f"prodvers=({nums})" in compact
    assert f"u'FileVersion', u'{cabrechess.__version__}'" in text
    assert f"u'ProductVersion', u'{cabrechess.__version__}'" in text


def test_changelog_tiene_seccion_de_la_version():
    notes = release_notes.changelog_section(cabrechess.__version__)
    assert "Temas de tablero" in notes
    assert not re.search(r"^## ", notes, re.M)
    assert not re.search(r"^\[\d", notes, re.M)  # sin links del pie


def test_release_notes_rechaza_etiqueta_distinta():
    import pytest
    with pytest.raises(SystemExit):
        release_notes.main(["release_notes.py", "v0.0.1"])


def test_release_notes_escribe_archivo_utf8(tmp_path):
    out = tmp_path / "notes.md"
    release_notes.main(["release_notes.py", f"v{cabrechess.__version__}", str(out)])
    assert "Temas de tablero" in out.read_text(encoding="utf-8")
