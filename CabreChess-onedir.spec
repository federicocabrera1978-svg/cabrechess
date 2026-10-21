# -*- mode: python ; coding: utf-8 -*-
# Build "onedir": una carpeta con CabreChess.exe + DLLs, sin autoextraerse a
# %TEMP% al arrancar (lo que hace el onefile y suele disparar heurísticas de
# antivirus como Avast CyberCapture / Behavior Shield). Se distribuye en .zip.
# Uso: pyinstaller --distpath dist-onedir CabreChess-onedir.spec


a = Analysis(
    ['packaging_entry.py'],
    pathex=[],
    binaries=[],
    datas=[('cabrechess/assets', 'cabrechess/assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CabreChess',
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
    icon=['cabrechess/assets/logo/cabrechess.ico'],
    version='version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CabreChess',
)
