"""El empaquetado multiplataforma (D4) nombra, archiva y verifica bien."""
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import package  # noqa: E402


def test_platform_key():
    assert package.platform_key("win32") == "windows"
    assert package.platform_key("darwin") == "macos"
    assert package.platform_key("linux") == "linux"
    assert package.platform_key("linux2") == "linux"


def test_macos_arch():
    assert package.macos_arch("arm64") == "arm64"
    assert package.macos_arch("aarch64") == "arm64"
    assert package.macos_arch("x86_64") == "x64"
    assert package.macos_arch("AMD64") == "x64"


def test_artifact_names_windows_y_linux():
    assert package.artifact_names("windows") == ["CabreChess-win64.zip", "CabreChess.exe"]
    assert package.artifact_names("linux") == ["CabreChess-linux64.tar.gz"]


def test_artifact_names_macos_incluye_arch():
    assert package.artifact_names("macos", "arm64") == ["CabreChess-macos-arm64.dmg"]
    assert package.artifact_names("macos", "x64") == ["CabreChess-macos-x64.dmg"]


def test_artifact_names_rechaza_plataforma_desconocida():
    with pytest.raises(ValueError):
        package.artifact_names("android")


def test_write_and_verify_sha256(tmp_path):
    blob = tmp_path / "CabreChess-linux64.tar.gz"
    blob.write_bytes(b"cabrechess-pack")
    sha = package.write_sha256(blob)
    assert sha.name == "CabreChess-linux64.tar.gz.sha256"
    text = sha.read_text(encoding="ascii")
    assert text.endswith("  CabreChess-linux64.tar.gz\n")
    assert package.verify_sha256(blob, sha)
    # El verificador acepta el hash en mayúsculas (como Get-FileHash de Windows).
    digest, name = text.strip().split()
    sha.write_text(f"{digest.upper()}  {name}\n", encoding="ascii")
    assert package.verify_sha256(blob, sha)
    blob.write_bytes(b"otro")
    assert not package.verify_sha256(blob, sha)


def test_make_zip_tiene_carpeta_de_primer_nivel(tmp_path):
    src = tmp_path / "CabreChess"
    (src / "_internal" / "cabrechess" / "assets" / "pieces" / "cburnett").mkdir(parents=True)
    (src / "CabreChess.exe").write_bytes(b"exe")
    (src / "_internal" / "cabrechess" / "assets" / "pieces" / "cburnett" / "wK.png").write_bytes(b"png")
    dest = tmp_path / "CabreChess-win64.zip"
    package.make_zip(src, dest)
    with zipfile.ZipFile(dest) as zf:
        names = zf.namelist()
    assert "CabreChess/CabreChess.exe" in names
    assert "CabreChess/_internal/cabrechess/assets/pieces/cburnett/wK.png" in names
    assert not any(n.startswith("CabreChess.exe") for n in names)


def test_make_targz_tiene_carpeta_de_primer_nivel(tmp_path):
    import tarfile

    src = tmp_path / "CabreChess"
    src.mkdir()
    (src / "CabreChess").write_bytes(b"bin")
    dest = tmp_path / "CabreChess-linux64.tar.gz"
    package.make_targz(src, dest)
    with tarfile.open(dest, "r:gz") as tf:
        names = tf.getnames()
    assert "CabreChess" in names
    assert "CabreChess/CabreChess" in names


def test_find_bundled_piece(tmp_path):
    piece_dir = tmp_path / "CabreChess" / "_internal" / "cabrechess" / "assets" / "pieces" / "cburnett"
    piece_dir.mkdir(parents=True)
    target = piece_dir / "wK.png"
    target.write_bytes(b"png")
    assert package.find_bundled_piece(tmp_path / "CabreChess") == target


def test_find_bundled_piece_falta(tmp_path):
    (tmp_path / "CabreChess").mkdir()
    with pytest.raises(SystemExit):
        package.find_bundled_piece(tmp_path / "CabreChess")


def test_check_exige_artefactos_y_checksums(tmp_path):
    with pytest.raises(SystemExit, match="faltan artefactos"):
        package.check("linux", tmp_path)
    blob = tmp_path / "CabreChess-linux64.tar.gz"
    blob.write_bytes(b"data")
    with pytest.raises(SystemExit, match="falta el checksum"):
        package.check("linux", tmp_path)
    package.write_sha256(blob)
    package.check("linux", tmp_path)  # no lanza


def test_build_rechaza_cruzar_plataformas():
    other = "windows" if package.platform_key() != "windows" else "linux"
    with pytest.raises(SystemExit, match="no se puede empaquetar"):
        package.build(other)


def test_onedir_spec_es_multiplataforma():
    text = (ROOT / "CabreChess-onedir.spec").read_text(encoding="utf-8")
    assert "sys.platform" in text
    assert "win32" in text
    assert "darwin" in text
    assert "BUNDLE" in text
    assert "version_info.txt" in text
    assert "CABRECHESS_ICNS" in text


def test_onefile_spec_solo_versiona_en_windows():
    text = (ROOT / "CabreChess.spec").read_text(encoding="utf-8")
    assert 'sys.platform == "win32"' in text
    assert "version_info.txt" in text


def test_release_workflow_tiene_matriz_y_notas_del_changelog():
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "windows-latest" in text
    assert "ubuntu-latest" in text
    assert "macos-latest" in text
    assert "strategy:" in text
    assert "matrix:" in text
    assert "tools/release_notes.py" in text
    assert "body_path: release_notes.md" in text
    assert "tools/package.py" in text
    assert "CabreChess-linux64.tar.gz" in text or "package.py" in text
    assert "v*" in text


def test_ci_arma_dist_en_las_tres_plataformas():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "windows-latest" in text
    assert "ubuntu-latest" in text
    assert "macos-latest" in text
    assert "tools/package.py" in text


def test_package_help(capsys):
    package.main(["--help"])
    out = capsys.readouterr().out
    assert "PyInstaller" in out
    assert "CabreChess-linux64.tar.gz" in out
