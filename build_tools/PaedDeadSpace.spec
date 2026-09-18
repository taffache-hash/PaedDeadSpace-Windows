# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata


ROOT = Path(SPECPATH)
UI_DIR = ROOT / "ui"

streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all("streamlit")
pds_datas, pds_binaries, pds_hiddenimports = collect_all("paeddeadspace")

datas = []
datas += streamlit_datas
datas += pds_datas
datas += copy_metadata("streamlit")
datas += copy_metadata("paeddeadspace")
datas += [
    (str(UI_DIR / "app.py"), "ui"),
    (str(UI_DIR / "ui_logic.py"), "ui"),
]

binaries = []
binaries += streamlit_binaries
binaries += pds_binaries

hiddenimports = []
hiddenimports += streamlit_hiddenimports
hiddenimports += pds_hiddenimports
hiddenimports += [
    "matplotlib",
    "matplotlib.pyplot",
    "altair",
    "pandas",
    "numpy",
    "pyarrow",
    "pydeck",
    "watchdog",
]

a = Analysis(
    ["launcher.py"],
    pathex=[str(ROOT), str(UI_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PaedDeadSpace",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PaedDeadSpace",
)
