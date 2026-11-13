# -*- mode: python ; coding: utf-8 -*-
# Build "onefile": un solo ejecutable. En Windows se autoextrae a %TEMP%
# al arrancar; el onedir (CabreChess-onedir.spec) es el formato recomendado.
import sys

ICON_ICO = "cabrechess/assets/logo/cabrechess.ico"
icon = [ICON_ICO] if sys.platform == "win32" else None
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
    upx=False,  # UPX dispara falsos positivos de antivirus (Avast, Defender)
    upx_exclude=[],
    runtime_tmpdir=None,
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
    a.binaries,
    a.datas,
    [],
    **exe_kwargs,
)
