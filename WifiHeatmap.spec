# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH)
release_docs = [
    ('LICENSE', str(project_root / 'LICENSE'), 'DATA'),
    ('THIRD_PARTY_LICENSES', str(project_root / 'THIRD_PARTY_LICENSES'), 'DATA'),
    ('README.md', str(project_root / 'README.md'), 'DATA'),
    ('CHANGELOG.md', str(project_root / 'CHANGELOG.md'), 'DATA'),
]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('images', 'images')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WifiHeatmap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon='images/app_icon.ico',
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    *release_docs,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WifiHeatmap',
)
