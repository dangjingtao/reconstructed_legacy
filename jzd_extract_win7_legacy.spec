# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

runtime_dir = 'win7_runtime'
runtime_files = [
    os.path.join(runtime_dir, name)
    for name in os.listdir(runtime_dir)
    if name.lower().endswith('.dll')
]

datas = [('oda', 'oda')]
datas += [(path, '.') for path in runtime_files]
datas += collect_data_files('ezdxf', includes=['*.py.typed', '*.txt', '*.json'])
binaries = []
hiddenimports = collect_submodules(
    'ezdxf',
    filter=lambda name: not name.startswith('ezdxf.addons.browser'),
)

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='jzd_extract_win7_legacy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
