# Construction : .venv\Scripts\python.exe -m PyInstaller neon_drive.spec --noconfirm
# Resultat : dist\NeonDrive\NeonDrive.exe
from PyInstaller.utils.hooks import collect_all

scenes = ["loading", "menu", "modes", "garage", "leaderboard", "stats", "settings", "game", "gameover", "calibration", "backdrop"]
datas = [("assets", "assets"), ("engine/shaders", "engine/shaders")]
hidden = ["glcontext", "_moderngl", "moderngl"] + [f"scenes.{s}" for s in scenes]
binaries = []
for pkg in ("mediapipe",):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hidden += h

a = Analysis(
    ["main.py"], pathex=["."], binaries=binaries, datas=datas, hiddenimports=hidden,
    excludes=["tkinter", "pytest", "IPython", "scipy", "pandas", "jax", "torch", "tensorflow"], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="NeonDrive", icon="assets/icons/app.ico", console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="NeonDrive", upx=False)
