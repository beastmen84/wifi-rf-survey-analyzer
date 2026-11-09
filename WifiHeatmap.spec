# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from shutil import copy2
from runpy import run_path
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct,
    VarFileInfo, VarStruct,
)


project_root = Path(SPECPATH)
product = run_path(str(project_root / 'app_core' / 'version.py'))
version_parts = (*map(int, product['APP_VERSION'].split('.')), 0)
windows_version = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_parts, prodvers=version_parts,
        mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('CompanyName', product['APP_AUTHOR']),
        StringStruct('FileDescription', product['APP_DISPLAY_NAME']),
        StringStruct('FileVersion', product['APP_VERSION']),
        StringStruct('InternalName', 'WiFiRFSurveyAnalyzer'),
        StringStruct('LegalCopyright', product['APP_COPYRIGHT']),
        StringStruct('OriginalFilename', 'WiFiRFSurveyAnalyzer.exe'),
        StringStruct('ProductName', product['APP_DISPLAY_NAME']),
        StringStruct('ProductVersion', product['APP_VERSION']),
    ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])],
)
release_docs = [
    ('LICENSE', str(project_root / 'LICENSE'), 'DATA'),
    ('THIRD_PARTY_LICENSES', str(project_root / 'THIRD_PARTY_LICENSES'), 'DATA'),
    ('README.md', str(project_root / 'README.md'), 'DATA'),
    ('CHANGELOG.md', str(project_root / 'CHANGELOG.md'), 'DATA'),
    ('docs/AUDIT_1_4_0.md', str(project_root / 'docs' / 'AUDIT_1_4_0.md'), 'DATA'),
    ('docs/AUDIT_1_3_0.md', str(project_root / 'docs' / 'AUDIT_1_3_0.md'), 'DATA'),
    ('docs/AUDIT_1_1_0.md', str(project_root / 'docs' / 'AUDIT_1_1_0.md'), 'DATA'),
    ('docs/assets/readme_start.png', str(project_root / 'docs' / 'assets' / 'readme_start.png'), 'DATA'),
    ('requirements.txt', str(project_root / 'requirements.txt'), 'DATA'),
    ('requirements-dev.txt', str(project_root / 'requirements-dev.txt'), 'DATA'),
    ('requirements-lock.txt', str(project_root / 'requirements-lock.txt'), 'DATA'),
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
    name='WiFiRFSurveyAnalyzer',
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
    version=windows_version,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    release_docs,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WiFiRFSurveyAnalyzer',
)

dist_root = Path(DISTPATH) / 'WiFiRFSurveyAnalyzer'
for dest_name, src_name, _typecode in release_docs:
    target_path = dist_root / dest_name
    target_path.parent.mkdir(parents=True, exist_ok=True)
    copy2(src_name, target_path)
