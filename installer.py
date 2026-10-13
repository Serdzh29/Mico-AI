"""Мастер установки и удаление Mico. Работает только в собранном Mico.exe.
Во время установки Mico рассказывает о себе текстом на странице прогресса."""
import json, os, shutil, subprocess, sys

from PyQt6.QtCore import QThread, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton,
                             QStackedWidget, QVBoxLayout, QWidget)

FROZEN = bool(getattr(sys, "frozen", False))
INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", "Mico")
INSTALL_EXE = os.path.join(INSTALL_DIR, "Mico.exe")
ICON_PATH = os.path.join(INSTALL_DIR, "mico.ico")
APPDIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Mico")
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Mico"

# Что Mico рассказывает во время установки. Показывается текстом, по одной фразе.
STORY = [
    "Привет! Я Mico. Я живу на твоём компьютере и помогаю без лишней суеты.",
    "Всё, что я вижу и помню, остаётся на этом ПК. В интернет ничего не уходит без твоей просьбы.",
    "Я управляю Windows: громкость, яркость, Wi-Fi, Bluetooth, Защитник, службы и компоненты системы.",
    "Могу проверить обновления, очистить DNS, открыть диспетчер задач или сбросить сеть, если попросишь.",
    "Я понимаю продолжения. Скажи «переключи трек», а потом «дальше», и я переключу ещё раз.",
    "Исправляю опечатки и учусь на твоих привычках, чтобы подсказывать нужное.",
    "Можно придумать свои фразы. Например, «работаю» включит режим «не беспокоить» и откроет нужные программы.",
    "Ctrl + Alt + M откроет чат. Ctrl + Alt + T переведёт выделенный текст.",
    "Утром я расскажу, на чём ты остановился вчера, и есть ли обновления.",
    "Я стою рядом с чатом и не закрываю окна, на которые ты смотришь.",
    "Почти готово. Осталось немного, и можно начинать.",
]

STEPS = [
    ("Копирую Mico в папку программ", "curious"),
    ("Создаю ярлык на рабочем столе", "happy"),
    ("Настраиваю автозапуск", "thinking"),
    ("Регистрирую Mico в Windows", "thinking"),
    ("Сохраняю настройки", "happy"),
    ("Проверяю Ollama для ответов", "curious"),
]


def should_run():
    """Запускать мастер: только в собранной версии и только не из папки установки."""
    if not FROZEN:
        return False
    return os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(os.path.abspath(INSTALL_EXE))


def render_mico(mood, size=150, color="#FFCFA3"):
    """Картинка Mico в нужном настроении: assets/mico.png, если он есть, иначе Mico, нарисованный программой."""
    custom = _asset("mico.png")
    if custom:
        return QPixmap(custom).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)
    from blob import Blob
    b = Blob({"color": color, "scale": size / 240.0, "opacity": 1.0})
    b.set_mood(mood, 999)
    pix = QPixmap(b.width(), b.height())
    pix.fill(Qt.GlobalColor.transparent)
    b.render(pix)
    b.deleteLater()
    return pix


def _asset(name):
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(base, "assets", name)
    return p if os.path.exists(p) else None


def column(*items):
    """Страница из элементов по вертикали (виджеты и отступы числом)."""
    w = QWidget()
    lay = QVBoxLayout(w)
    for it in items:
        if isinstance(it, int):
            lay.addSpacing(it)
        else:
            lay.addWidget(it)
    lay.addStretch()
    return w


class Wizard(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Установка Mico")
        self.setFixedSize(640, 430)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(_asset("mico.ico") or ""))
        self.ollama_ok = _ollama_present()
        self.story_i = 0
        self.story_timer = QTimer(self)
        self.story_timer.timeout.connect(self._next_story)

        root = QHBoxLayout(self)
        self.avatar = QLabel()
        self.avatar.setFixedWidth(180)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.avatar)

        right = QVBoxLayout()
        self.pages = QStackedWidget()
        right.addWidget(self.pages)
        for page in (self._page_welcome(), self._page_options(), self._page_install(), self._page_finish()):
            self.pages.addWidget(page)
        row = QHBoxLayout()
        self.cancel_b = QPushButton("Отмена")
        self.back_b = QPushButton("Назад")
        self.next_b = QPushButton("Далее")
        self.cancel_b.clicked.connect(self.reject)
        self.back_b.clicked.connect(lambda: self._go(self.pages.currentIndex() - 1))
        self.next_b.clicked.connect(self._next)
        row.addWidget(self.cancel_b)
        row.addStretch()
        row.addWidget(self.back_b)
        row.addWidget(self.next_b)
        right.addLayout(row)
        root.addLayout(right)
        self._go(0)

    # ---------- страницы ----------
    def _page_welcome(self):
        t = QLabel("<h2>Привет! Я Mico 💛</h2>"
                   "<p>Я твой компаньон на рабочем столе. Понимаю текст, управляю Windows, "
                   "подсказываю, что ты делал, и отвечаю на вопросы — всё локально, на твоём ПК.</p>"
                   "<p>Установка займёт около минуты.</p>")
        t.setWordWrap(True)
        return column(t)

    def _page_options(self):
        self.opt_auto = QCheckBox("Запускать вместе с Windows и после разблокировки")
        self.opt_auto.setChecked(True)
        self.opt_short = QCheckBox("Создать ярлык на рабочем столе")
        self.opt_short.setChecked(True)
        if self.ollama_ok:
            text = "✓ Ollama найдена. Ответы будут работать."
        else:
            text = "Ollama нужна для ответов. Установи её один раз, потом Mico скачает модели из настроек."
        self.ollama_lbl = QLabel(text)
        self.ollama_lbl.setWordWrap(True)
        ob = QPushButton("Открыть страницу Ollama")
        ob.clicked.connect(lambda: os.startfile("https://ollama.com/download"))
        return column(QLabel("<h3>Параметры</h3>"), self.opt_auto, self.opt_short,
                      self.ollama_lbl, ob)

    def _page_install(self):
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.status = QLabel("Готовлюсь…")
        self.status.setWordWrap(True)
        self.story = QLabel("")
        self.story.setWordWrap(True)
        self.story.setStyleSheet("font-style: italic; color: #7a6a58; font-size: 13px;")
        self.story.setMinimumHeight(70)
        return column(QLabel("<h3>Устанавливаю</h3>"), self.bar, self.status, 8, self.story)

    def _page_finish(self):
        self.finish_lbl = QLabel("<h2>Готово!</h2><p>Mico установлен. Запустить его сейчас?</p>")
        self.finish_lbl.setWordWrap(True)
        self.run_cb = QCheckBox("Запустить Mico")
        self.run_cb.setChecked(True)
        return column(self.finish_lbl, self.run_cb)

    # ---------- переходы ----------
    def _go(self, i):
        self.pages.setCurrentIndex(i)
        self.back_b.setVisible(i == 1)
        self.next_b.setText({0: "Далее", 1: "Установить", 2: "…", 3: "Закрыть"}[i])
        self.next_b.setEnabled(i != 2)
        self.cancel_b.setVisible(i != 3)
        self.avatar.setPixmap(render_mico({0: "happy", 1: "curious", 2: "thinking", 3: "love"}[i], 150))

    def _next(self):
        i = self.pages.currentIndex()
        if i == 0:
            self._go(1)
        elif i == 1:
            self._go(2)
            self._start_install()
        elif i == 3:
            if self.run_cb.isChecked() and os.path.exists(INSTALL_EXE):
                os.startfile(INSTALL_EXE)
            self.accept()

    # ---------- установка ----------
    def _start_install(self):
        self.story_i = 0
        self._next_story()
        self.story_timer.start(4500)
        self._worker = _Worker(self)
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _next_story(self):
        self.story.setText(STORY[self.story_i % len(STORY)])
        self.story_i += 1

    def _on_progress(self, pct, text, mood):
        self.bar.setValue(pct)
        self.status.setText(text)
        self.avatar.setPixmap(render_mico(mood, 150))

    def _on_done(self, err):
        self.story_timer.stop()
        if err:
            self.status.setText(f"Не получилось: {err}. Если Mico открыт, закрой его и запусти установку снова.")
            self.story.setText("")
            self.next_b.setEnabled(True)
            self.next_b.setText("Закрыть")
            self.next_b.clicked.disconnect()
            self.next_b.clicked.connect(self.reject)
            return
        self.bar.setValue(100)
        self._go(3)


def _install_steps(wizard, report):
    """Все шаги установки. report(i, пояснение) сообщает о прогрессе."""
    import autostart
    os.makedirs(INSTALL_DIR, exist_ok=True)
    report(0)
    shutil.copy2(sys.executable, INSTALL_EXE)
    icon = _asset("mico.ico")
    if icon:
        shutil.copy2(icon, ICON_PATH)            # значок для ярлыка и списка приложений
    report(1)
    if wizard.opt_short.isChecked():
        _desktop_shortcut(create=True)
    report(2)
    auto_on = False
    if wizard.opt_auto.isChecked():
        auto_on, msg = autostart.install(exe=INSTALL_EXE)
        if not auto_on:
            report(2, "не получилось, включи позже в настройках")
    report(3)
    _register_uninstall()
    report(4)
    _save_settings(auto_on)                                  # записываем то, что реально получилось, а не то, что выбрали
    report(5)


class _Worker(QThread):
    """Установка в фоне, чтобы окно не зависало."""
    progress = pyqtSignal(int, str, str)
    done = pyqtSignal(str)

    def __init__(self, wizard):
        super().__init__(wizard)
        self.wizard = wizard

    def run(self):
        def report(i, extra=""):
            text, mood = STEPS[i]
            self.progress.emit(int(i / len(STEPS) * 100), text + (f" — {extra}" if extra else ""), mood)
        try:
            _install_steps(self.wizard, report)
            self.done.emit("")
        except Exception as e:
            self.done.emit(f"{e.__class__.__name__}: {e}")


def _desktop_shortcut(create):
    import winctl
    path = "[Environment]::GetFolderPath('Desktop')+'\\Mico.lnk'"
    if create:
        icon_ps = f"$s.IconLocation='{ICON_PATH}';" if os.path.exists(ICON_PATH) else ""
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut({path});"
              f"$s.TargetPath='{INSTALL_EXE}';$s.WorkingDirectory='{INSTALL_DIR}';{icon_ps}$s.Save()")
    else:
        ps = f"Remove-Item -ErrorAction SilentlyContinue -Path ({path})"
    winctl.ps(ps, timeout=30)


def _register_uninstall():
    """Регистрирует Mico в «Параметры → Приложения», чтобы его можно было удалить штатным способом."""
    import winreg
    k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, winreg.KEY_SET_VALUE)
    values = {"DisplayName": "Mico", "DisplayVersion": _version(), "Publisher": "Mico",
              "InstallLocation": INSTALL_DIR,
              "DisplayIcon": ICON_PATH if os.path.exists(ICON_PATH) else INSTALL_EXE,
              "UninstallString": f'"{INSTALL_EXE}" --uninstall'}
    for name, value in values.items():
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
    winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
    winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)
    winreg.CloseKey(k)


def _unregister_uninstall():
    import winreg
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        pass


def _ollama_present():
    local = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
    if os.path.exists(local) or shutil.which("ollama"):
        return True
    try:
        import requests
        return requests.get("http://127.0.0.1:11434/api/tags", timeout=1).ok
    except Exception:
        return False


def _save_settings(autostart_on):
    """Минимальные настройки для первого запуска. Остальное — значения по умолчанию в программе."""
    os.makedirs(APPDIR, exist_ok=True)
    path = os.path.join(APPDIR, "config.json")
    try:
        cfg = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    cfg.update(autostart=autostart_on, greet_on_start=True, update_channel="stable")
    cfg.setdefault("last_version", _version())            # не показывать «что нового» сразу после установки
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _version():
    import version
    return version.APP_VERSION


# ============================ Бета-программа ============================
class _Cancelled(Exception):
    """Пользователь нажал «Отмена» во время загрузки."""


class BetaJoin(QThread):
    """Скачивает бета-сборку в фоне и сверяет контрольную сумму. Окно не зависает: загрузку можно отменить,
    а если сеть молчит дольше TIMEOUT секунд или загрузка идёт дольше MAX_SECONDS, она прерывается.
    Адрес файла с бетой задаёт разработчик (version.BETA_INFO_URL), настройки пользователя на это не влияют.
    done(путь, ошибка): при успехе ошибка пустая; при отмене ошибка равна CANCELLED."""
    done = pyqtSignal(str, str)
    CANCELLED = "отменено"
    TIMEOUT = (10, 30)              # (соединение, пауза без данных), секунд
    MAX_SECONDS = 900               # дольше не ждём

    def __init__(self, info_url, parent=None):
        super().__init__(parent)
        import threading
        self.info_url = info_url
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
        import time
        import requests
        import betaprogram
        import updates
        path = ""
        try:
            if not self.info_url:
                raise betaprogram.BetaUnavailable("бета-сборка пока не опубликована")
            info = betaprogram.beta_build(requests.get(self.info_url, timeout=self.TIMEOUT).text)
            path = betaprogram.download_path(info["version"])
            deadline = time.time() + self.MAX_SECONDS
            with requests.get(info["url"], stream=True, timeout=self.TIMEOUT) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        if self._cancel.is_set():
                            raise _Cancelled()
                        if time.time() > deadline:
                            raise betaprogram.BetaUnavailable("загрузка идёт слишком долго, попробуй позже")
                        f.write(chunk)
            if self._cancel.is_set():
                raise _Cancelled()
            if not updates.verify_sha256(path, info["sha256"]):
                raise betaprogram.BetaUnavailable("контрольная сумма не совпала, файл выброшен")
            self.done.emit(path, "")
        except _Cancelled:
            self._drop(path)
            self.done.emit("", self.CANCELLED)
        except Exception as e:
            self._drop(path)
            msg = str(e) if isinstance(e, betaprogram.BetaUnavailable) else f"не получилось скачать ({e.__class__.__name__})"
            self.done.emit("", msg)

    @staticmethod
    def _drop(path):
        """Убирает недокачанный или испорченный файл, чтобы он не остался во временной папке."""
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def finish_beta_join():
    """Запускается из временной копии, которую скачали для бета-версии. Ставит её на место старой
    программы и открывает. False — старая копия не отпустила файл или не вышло записать."""
    import betaprogram
    import features
    if not betaprogram.replace_when_free(sys.executable, INSTALL_EXE):
        return False
    path = os.path.join(APPDIR, "config.json")
    try:
        cfg = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    cfg.update(update_channel="beta", beta_consent_version=features.BETA_CONSENT_VERSION)
    os.makedirs(APPDIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    betaprogram.launch(INSTALL_EXE)
    return True


def run():
    """Мастер установки. Возвращает после закрытия; установленная копия запускается сама."""
    dlg = Wizard()
    dlg.exec()


# ============================ Удаление ============================
def is_uninstall_request():
    return "--uninstall" in sys.argv


def uninstall(app):
    """Удаление: спрашивает, удалять ли данные, снимает автозапуск, ярлык и регистрацию, затем удаляет файлы.
    Сам файл Mico.exe нельзя удалить, пока он запущен, поэтому удаляет его отдельный скрипт после выхода."""
    if not FROZEN:
        QMessageBox.information(None, "Mico", "Удаление доступно только для установленной версии Mico.exe.")
        return False
    if QMessageBox.question(None, "Удалить Mico",
                            "Удалить Mico с этого компьютера?\n\nПрограмма и её ярлык будут удалены, "
                            "автозапуск выключится.") != QMessageBox.StandardButton.Yes:
        return False
    delete_data = QMessageBox.question(
        None, "Данные Mico",
        f"Удалить также историю, настройки и напоминания?\n\nПапка: {APPDIR}\n\n"
        "«Нет» — данные сохранятся, если переустановишь Mico.") == QMessageBox.StandardButton.Yes
    try:
        import autostart
        autostart.remove()
        _desktop_shortcut(create=False)
        _unregister_uninstall()
    except Exception:
        pass
    _schedule_file_removal(delete_data)
    kept = "" if delete_data else f"\n\nОсталось по твоему выбору: данные в {APPDIR}."
    QMessageBox.information(None, "Mico удалён",
                            "Удалены: программа, ярлык на рабочем столе, автозапуск и запись в «Приложениях»."
                            + kept)
    if app is not None:
        app.quit()
    return True


def _schedule_file_removal(delete_data):
    """Скрипт в %TEMP%: ждёт выхода Mico, удаляет его папку и (по желанию) данные, затем удаляет себя."""
    script = os.path.join(os.environ.get("TEMP", "."), "mico_uninstall.cmd")
    lines = [
        "@echo off",
        ":wait",
        "ping 127.0.0.1 -n 2 >nul",
        f'del /f /q "{INSTALL_EXE}" 2>nul',
        f'if exist "{INSTALL_EXE}" goto wait',
        f'rmdir /s /q "{INSTALL_DIR}" 2>nul',
    ]
    if delete_data:
        lines.append(f'rmdir /s /q "{APPDIR}" 2>nul')
    lines.append('del /f /q "%~f0"')
    with open(script, "w", encoding="ascii", errors="replace") as f:
        f.write("\r\n".join(lines) + "\r\n")
    subprocess.Popen(["cmd", "/c", script], creationflags=0x08000000 | 0x00000008)     # без окна, отдельно
