# -*- mode: python ; coding: utf-8 -*-
# Build "onedir": una carpeta con el ejecutable + dependencias, sin
# autoextraerse a un temporal al arrancar. En Windows se reparte en .zip,
# en Linux en .tar.gz y en macOS como .app / .dmg.
# Uso: pyinstaller --distpath dist-onedir CabreChess-onedir.spec
import os
import re
import sys
from pathlib import Path

ICON_ICO = "cabrechess/assets/logo/cabrechess.ico"
ICON_PNG = "cabrechess/assets/logo/cabrechess.png"
ICON_ICNS = "cabrechess/assets/logo/cabrechess.icns"


def _code_version():
    text = Path("cabrechess/_version.py").read_text(encoding="utf-8")
    return re.search(r'__version__\s*=\s*"([^"]+)"', text).group(1)


def _icon():
    if sys.platform == "win32":
        return [ICON_ICO]
    if sys.platform == "darwin":
        env = os.environ.get("CABRECHESS_ICNS")
        for candidate in (env, ICON_ICNS, ICON_PNG):
            if candidate and Path(candidate).is_file():
                return [candidate]
        return None
    if Path(ICON_PNG).is_file():
        return [ICON_PNG]
    return None


icon = _icon()
version = "version_info.txt" if sys.platform == "win32" else None

a = Analysis(
    ["packaging_entry.py"],
    pathex=[],
    binaries=[],
    datas=[("cabrechess/assets", "cabrechess/assets")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe_kwargs = dict(
    name="CabreChess",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
if version:
    exe_kwargs["version"] = version

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    **exe_kwargs,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CabreChess",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="CabreChess.app",
        icon=icon[0] if icon else None,
        bundle_identifier="com.federicocabrera.cabrechess",
        info_plist={
            "CFBundleName": "CabreChess",
            "CFBundleDisplayName": "CabreChess",
            "CFBundleShortVersionString": _code_version(),
            "CFBundleVersion": _code_version(),
            "CFBundleGetInfoString": "CabreChess " + _code_version(),
            "NSHighResolutionCapable": True,
        },
    )
