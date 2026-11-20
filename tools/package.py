# SPDX-License-Identifier: GPL-3.0-or-later
"""Empaqueta CabreChess con PyInstaller para Windows, Linux o macOS.

Uso (en la raíz del repo):

    python tools/package.py          # detecta la plataforma, escribe en dist/
    python tools/package.py --check  # solo verifica los archivos ya generados

En Windows genera CabreChess-win64.zip (recomendado) y CabreChess.exe.
En Linux, CabreChess-linux64.tar.gz.
En macOS, un .dmg con CabreChess.app (el nombre incluye la arquitectura:
CabreChess-macos-arm64.dmg o CabreChess-macos-x64.dmg).
Cada archivo trae su .sha256.
"""
from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
DIST_ONEDIR = ROOT / "dist-onedir"
BUILD = ROOT / "build"
PIECE = Path("cabrechess") / "assets" / "pieces" / "cburnett" / "wK.png"
# Tamaños del iconset de Apple (pixeles, nombre).
_ICNS_SIZES = (
    (16, "icon_16x16.png"),
    (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"),
    (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"),
    (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"),
    (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"),
    (1024, "icon_512x512@2x.png"),
)


def platform_key(sys_platform: str | None = None) -> str:
    """windows, macos o linux a partir de sys.platform."""
    p = sys_platform if sys_platform is not None else sys.platform
    if p == "win32":
        return "windows"
    if p == "darwin":
        return "macos"
    return "linux"


def macos_arch(machine: str | None = None) -> str:
    """arm64 o x64, para el nombre del .dmg."""
    m = (machine if machine is not None else platform.machine()).lower()
    if m in ("arm64", "aarch64"):
        return "arm64"
    return "x64"


def artifact_names(key: str, arch: str | None = None) -> list[str]:
    """Nombres de los archivos que se publican en el Release (sin .sha256)."""
    if key == "windows":
        return ["CabreChess-win64.zip", "CabreChess.exe"]
    if key == "linux":
        return ["CabreChess-linux64.tar.gz"]
    if key == "macos":
        suffix = arch if arch is not None else macos_arch()
        return [f"CabreChess-macos-{suffix}.dmg"]
    raise ValueError(f"plataforma desconocida: {key}")


def write_sha256(path: Path) -> Path:
    """Escribe ``<archivo>.sha256`` al lado, en el formato de sha256sum."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    out = path.with_name(path.name + ".sha256")
    out.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return out


def verify_sha256(path: Path, sha_path: Path | None = None) -> bool:
    """Comprueba que el checksum coincida (el hash puede ir en mayúsculas)."""
    if sha_path is None:
        sha_path = path.with_name(path.name + ".sha256")
    line = sha_path.read_text(encoding="ascii").strip().split()
    if len(line) < 2 or line[1] != path.name:
        return False
    return line[0].lower() == hashlib.sha256(path.read_bytes()).hexdigest()


def make_zip(src_dir: Path, dest: Path) -> Path:
    """Arma un .zip con ``src_dir`` como carpeta de primer nivel."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(src_dir.rglob("*")):
            if file.is_file():
                zf.write(file, arcname=(Path(src_dir.name) / file.relative_to(src_dir)).as_posix())
    return dest


def make_targz(src_dir: Path, dest: Path) -> Path:
    """Arma un .tar.gz con ``src_dir`` como carpeta de primer nivel."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    with tarfile.open(dest, "w:gz") as tf:
        tf.add(src_dir, arcname=src_dir.name)
    return dest


def make_dmg(app_path: Path, dest: Path, volname: str = "CabreChess") -> Path:
    """Arma un .dmg con el .app y un atajo a Aplicaciones (solo macOS)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    staging = BUILD / "dmg"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copytree(app_path, staging / app_path.name, symlinks=True)
    applications = staging / "Applications"
    applications.symlink_to("/Applications")
    subprocess.run(
        [
            "hdiutil",
            "create",
            "-volname",
            volname,
            "-srcfolder",
            str(staging),
            "-ov",
            "-format",
            "UDZO",
            str(dest),
        ],
        check=True,
    )
    return dest


def ensure_macos_icns(root: Path | None = None) -> Path:
    """Genera cabrechess.icns en build/ a partir del PNG, con sips e iconutil."""
    root = ROOT if root is None else root
    out = root / "build" / "cabrechess.icns"
    existing = root / "cabrechess" / "assets" / "logo" / "cabrechess.icns"
    if existing.is_file() and not out.is_file():
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(existing, out)
        return out
    if out.is_file():
        return out
    png = root / "cabrechess" / "assets" / "logo" / "cabrechess.png"
    if not png.is_file():
        raise SystemExit(f"no está el PNG del logo: {png}")
    iconset = root / "build" / "cabrechess.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)
    for px, name in _ICNS_SIZES:
        target = iconset / name
        subprocess.run(
            ["sips", "-z", str(px), str(px), str(png), "--out", str(target)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out)], check=True)
    return out


def onedir_output(key: str, dist_onedir: Path | None = None) -> Path:
    """Carpeta (Windows/Linux) o .app (macOS) que deja PyInstaller."""
    base = DIST_ONEDIR if dist_onedir is None else dist_onedir
    if key == "macos":
        return base / "CabreChess.app"
    return base / "CabreChess"


def find_bundled_piece(root: Path) -> Path:
    """Busca el sprite wK.png dentro del empaquetado."""
    matches = [p for p in root.rglob("wK.png") if p.parent.name == "cburnett"]
    if not matches:
        raise SystemExit(f"no se encontró {PIECE} dentro de {root}")
    return matches[0]


def _run_pyinstaller(spec: str, distpath: Path | None = None) -> None:
    cmd = [sys.executable, "-m", "PyInstaller", spec]
    if distpath is not None:
        cmd[3:3] = ["--distpath", str(distpath)]
    subprocess.run(cmd, cwd=ROOT, check=True)


def build(key: str | None = None) -> list[Path]:
    """Compila y empaqueta para la plataforma. Devuelve los archivos en dist/."""
    key = platform_key() if key is None else key
    if key != platform_key():
        raise SystemExit(
            f"no se puede empaquetar para {key} en {platform_key()} "
            "(PyInstaller no cruza de un sistema a otro)"
        )
    DIST.mkdir(parents=True, exist_ok=True)
    if key == "macos":
        icns = ensure_macos_icns()
        os.environ["CABRECHESS_ICNS"] = str(icns)

    _run_pyinstaller("CabreChess-onedir.spec", DIST_ONEDIR)
    packed = onedir_output(key)
    if not packed.exists():
        raise SystemExit(f"PyInstaller no dejó {packed}")
    find_bundled_piece(packed)

    built: list[Path] = []
    if key == "windows":
        _run_pyinstaller("CabreChess.spec", DIST)
        exe = DIST / "CabreChess.exe"
        if not exe.is_file():
            raise SystemExit(f"no está el onefile: {exe}")
        built.append(exe)
        built.append(make_zip(packed, DIST / "CabreChess-win64.zip"))
    elif key == "linux":
        built.append(make_targz(packed, DIST / "CabreChess-linux64.tar.gz"))
    else:
        name = artifact_names("macos")[0]
        built.append(make_dmg(packed, DIST / name))

    for path in built:
        write_sha256(path)
    check(key, DIST)
    return built


def check(key: str | None = None, dist: Path | None = None) -> None:
    """Falla si faltan los artefactos esperados o no coinciden los checksums."""
    key = platform_key() if key is None else key
    dist = DIST if dist is None else dist
    names = artifact_names(key)
    missing = [n for n in names if not (dist / n).is_file()]
    if missing:
        raise SystemExit(f"faltan artefactos en {dist}: {', '.join(missing)}")
    for name in names:
        path = dist / name
        sha = path.with_name(name + ".sha256")
        if not sha.is_file():
            raise SystemExit(f"falta el checksum: {sha}")
        if not verify_sha256(path, sha):
            raise SystemExit(f"el checksum no coincide: {sha}")
    print("ok", ", ".join(names))


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if args in (["-h"], ["--help"]):
        print(__doc__.strip())
        return
    if args == ["--check"]:
        check()
        return
    if args:
        raise SystemExit(__doc__)
    build()


if __name__ == "__main__":
    main()
