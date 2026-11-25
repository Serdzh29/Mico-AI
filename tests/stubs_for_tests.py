"""Подмена модулей Windows и тяжёлых библиотек для проверок на любой машине (вызывается из тестов).
Имя файла не начинается с test_, поэтому run_all.py его не запускает как отдельную проверку."""
import importlib.machinery, sys, types
from unittest import mock

_ROOTS = ("pythoncom", "pywintypes", "winreg", "mss", "psutil", "PyQt6", "pycaw", "comtypes", "llama_cpp",
          "cryptography", "onnxruntime", "sounddevice", "faster_whisper", "piper", "numpy", "scipy", "pypdf")


class _Stub(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        m = mock.MagicMock(name=f"{self.__name__}.{name}")
        setattr(self, name, m)
        return m


class _Finder:
    def find_spec(self, name, path, target=None):
        top = name.split(".")[0]
        if (top.startswith("win32") or top in _ROOTS) and name not in sys.modules:
            return importlib.machinery.ModuleSpec(name, self, is_package=True)

    def create_module(self, spec):
        return _Stub(spec.name)

    def exec_module(self, module):
        module.__path__ = []


def install():
    if not any(isinstance(f, _Finder) for f in sys.meta_path):
        sys.meta_path.insert(0, _Finder())
