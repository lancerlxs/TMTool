# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['CheckDPI.py'],
    pathex=['D:\\PythonWorrk\\TMAI-win7'],
    binaries=[],
    datas=[],
    hiddenimports=['PIL', 'PIL.Image', 'PyQt5'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'numpy',
        'scipy',
        'matplotlib',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CheckDPI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CheckDPI',
)
