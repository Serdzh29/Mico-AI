"""Остановка Ollama вместе с Mico AI: при «Выход» закрываем и сервер модели, и его фоновые процессы,
чтобы они не держали оперативную память. Только psutil, без других модулей Mico."""
import os
import shutil
import subprocess
import time

import psutil

API = "http://127.0.0.1:11434"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

# Имена процессов Ollama на Windows и Linux/macOS: сервер, трей-приложение и процесс, который считает модель.
OLLAMA_NAMES = {
    "ollama.exe", "ollama app.exe", "ollama_llama_server.exe", "llama-server.exe", "ollama",
}


def _is_ollama(proc):
    try:
        return (proc.info.get("name") or "").lower() in OLLAMA_NAMES
    except (psutil.Error, AttributeError):
        return False


def ollama_processes():
    """Все работающие процессы Ollama."""
    found = []
    for proc in psutil.process_iter(["name"]):
        if _is_ollama(proc):
            found.append(proc)
    return found


def stop_ollama(timeout=3.0):
    """Завершает все процессы Ollama. Сначала мягко (terminate), потом жёстко (kill) для тех, кто не ответил.
    Возвращает количество найденных процессов. Ошибки доступа молча пропускаем: Mico всё равно закрывается."""
    procs = ollama_processes()
    if not procs:
        return 0
    for proc in procs:
        try:
            proc.terminate()
        except psutil.Error:
            pass
    try:
        _, alive = psutil.wait_procs(procs, timeout=timeout)
    except psutil.Error:
        alive = procs
    for proc in alive:
        try:
            proc.kill()
        except psutil.Error:
            pass
    return len(procs)


def _ollama_exe():
    """Где лежит Ollama: сначала серверный ollama.exe, потом трей-приложение, потом то, что в PATH."""
    local = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama")
    for name in ("ollama.exe", "ollama app.exe"):
        path = os.path.join(local, name)
        if os.path.exists(path):
            return path, name
    found = shutil.which("ollama")
    return (found, "ollama") if found else (None, None)


def is_running(timeout=1.0):
    """Отвечает ли сервер Ollama на 127.0.0.1:11434."""
    try:
        import requests
        return requests.get(API + "/api/tags", timeout=timeout).ok
    except Exception:
        return False


def ensure_running(wait_sec=25.0):
    """Запускает Ollama, если её ещё нет (как и Mico, в фоне). Возвращает True, если сервер ответил.
    Ничего не делает, если Ollama уже работает: тогда её не трогаем, а при выходе закроем, как и обещано."""
    if is_running():
        return True
    exe, name = _ollama_exe()
    if exe is None:
        return False
    try:
        if name == "ollama.exe" or name == "ollama":
            args = [exe, "serve"]                       # только сервер, без трей-окна
        else:
            args = [exe]                                # трей-приложение само поднимает сервер
        # Только CREATE_NO_WINDOW: процесс получает скрытую консоль, и llama-server, которого он запускает,
        # тоже не открывает черное окно. DETACHED_PROCESS такое окно как раз и создавал.
        subprocess.Popen(args, creationflags=_NO_WINDOW, close_fds=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return False
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        if is_running():
            return True
        time.sleep(0.5)
    return False
