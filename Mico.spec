# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, copy_metadata


def meta(name):
    """Метаданные пакета нужны, если его читают через importlib.metadata. Если пакета нет — просто пропускаем."""
    try:
        return copy_metadata(name)
    except Exception:
        return []


datas = [('assets', 'assets'), ('knowledge', 'knowledge'), ('data', 'data')]
binaries = []
hiddenimports = ['win32crypt', 'win32com.client', 'pythoncom', 'pywintypes']
for pkg in ('faster_whisper', 'ctranslate2', 'piper', 'piper_phonemize', 'onnxruntime', 'sounddevice',
            'scipy', 'edge_tts', 'TTS', 'torch', 'torchaudio', 'torchcodec'):
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# имя дистрибутива coqui-tts отличается от имени пакета TTS: берём метаданные по обоим именам
datas += meta('coqui-tts') + meta('TTS')


a = Analysis(
    ['mico.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='Mico',
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
    icon=['assets/mico.ico'],
    manifest='Mico.manifest',
)
