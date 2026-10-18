"""Мастер установки и удаление Mico. Работает только в собранном Mico.exe.
Оформление в духе Mico AI: тёмная тема, персиковый акцент, без лишнего текста."""
import json, os, shutil, subprocess, sys, time

from PyQt6.QtCore import QEasingCurve, QThread, QVariantAnimation, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMessageBox,
                             QProgressBar, QPushButton, QStackedWidget, QVBoxLayout, QWidget)
from theme import FONT_FAMILY

FROZEN = bool(getattr(sys, "frozen", False))
INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", "Mico")
INSTALL_EXE = os.path.join(INSTALL_DIR, "Mico.exe")
ICON_PATH = os.path.join(INSTALL_DIR, "mico.ico")
APPDIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Mico")
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Mico"

STEPS = [
    ("Копирую Mico AI в папку программ", "curious"),
    ("Создаю ярлык на рабочем столе", "happy"),
    ("Настраиваю автозапуск", "thinking"),
    ("Регистрирую Mico AI в Windows", "thinking"),
    ("Сохраняю настройки", "happy"),
    ("Проверяю Ollama для ответов", "curious"),
]


def should_run():
    """Запускать мастер: только в собранной версии и только не из папки установки."""
    if not FROZEN:
        return False
    return os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(os.path.abspath(INSTALL_EXE))


def render_mico(mood, size=150, color="#FFCFA3"):
    """Картинка Mico AI в нужном настроении: assets/mico.png, если он есть, иначе Mico AI, нарисованный программой."""
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


ACCENT = "#FFCFA3"          # персиковый Mico AI: единый акцент мастера

QSS = f"""
QDialog#wizard {{ background: #15131a; }}
QFrame#side {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #221f2a, stop:1 #141218);
              border-right: 1px solid #242130; }}
QLabel {{ color: #e9e4dc; font-family: "{FONT_FAMILY}"; font-size: 13px; background: transparent; }}
QLabel#title {{ font-size: 24px; font-weight: 600; color: #f6f1e8; }}
QLabel#sub {{ color: #8d8697; font-size: 13px; }}
QLabel#step {{ color: #6d6679; font-size: 11px; }}
QLabel#brand {{ color: #cfc8d8; font-size: 15px; font-weight: 600; }}
QLabel#percent {{ font-size: 44px; font-weight: 300; color: #f6f1e8; }}
QLabel#ok {{ color: #9fd8a8; font-size: 13px; }}
QLabel#warn {{ color: #d9a58a; font-size: 13px; }}
QCheckBox {{ color: #ddd7cc; font-size: 13px; spacing: 12px; padding: 7px 0; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius:8px; border: 1px solid #4a4556; background: #1d1b24; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}
QPushButton {{ font-family: "{FONT_FAMILY}"; font-size: 13px; padding: 9px 22px; border-radius:12px;
              background: transparent; color: #b9b2c4; border: 1px solid #343040; }}
QPushButton:hover {{ background: #221f2a; color: #f1ebe1; }}
QPushButton:disabled {{ color: #4f4a5a; border-color: #26232e; }}
QPushButton#primary {{ background: {ACCENT}; color: #1a1620; border: none; font-weight: 600; }}
QPushButton#primary:hover {{ background: #ffdcb8; }}
QPushButton#primary:disabled {{ background: #34303d; color: #7a7384; }}
QProgressBar {{ background: #26232e; border: none; border-radius:8px; max-height: 6px; min-height: 6px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius:8px; }}
"""


class Wizard(QDialog):
    PAGE_STEP = {0: "", 1: "Шаг 1 из 2", 2: "Установка", 3: ""}
    PAGE_MOOD = {0: "happy", 1: "curious", 2: "thinking", 3: "love"}

    def __init__(self):
        super().__init__()
        self.setObjectName("wizard")
        self.setWindowTitle("Установка Mico AI")
        self.setFixedSize(700, 440)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(_asset("mico.ico") or ""))
        self.setStyleSheet(QSS)
        self.ollama_ok = _ollama_present()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # левая панель: Mico AI и название
        side = QFrame()
        side.setObjectName("side")
        side.setFixedWidth(230)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 36)
        sv.addStretch()
        self.avatar = QLabel()
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand = QLabel("Mico AI")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sv.addWidget(self.avatar)
        sv.addSpacing(10)
        sv.addWidget(brand)
        sv.addStretch()
        root.addWidget(side)

        # правая часть: шаг, страница, кнопки
        right = QVBoxLayout()
        right.setContentsMargins(40, 34, 40, 30)
        right.setSpacing(0)
        self.step_lbl = QLabel("")
        self.step_lbl.setObjectName("step")
        right.addWidget(self.step_lbl)
        right.addSpacing(10)
        self.pages = QStackedWidget()
        for page in (self._page_welcome(), self._page_options(), self._page_install(), self._page_finish()):
            self.pages.addWidget(page)
        right.addWidget(self.pages, 1)

        row = QHBoxLayout()
        self.cancel_b = QPushButton("Отмена")
        self.back_b = QPushButton("Назад")
        self.next_b = QPushButton("Далее")
        self.next_b.setObjectName("primary")
        self.cancel_b.clicked.connect(self.reject)
        self.back_b.clicked.connect(lambda: self._go(self.pages.currentIndex() - 1))
        self.next_b.clicked.connect(self._next)
        row.addWidget(self.cancel_b)
        row.addStretch()
        row.addWidget(self.back_b)
        row.addSpacing(8)
        row.addWidget(self.next_b)
        right.addLayout(row)
        root.addLayout(right, 1)
        self._go(0)

    # ---------- страницы ----------
    def _title(self, text):
        t = QLabel(text)
        t.setObjectName("title")
        return t

    def _sub(self, text):
        s = QLabel(text)
        s.setObjectName("sub")
        s.setWordWrap(True)
        return s

    def _page_welcome(self):
        return column(self._title("Установка Mico AI"),
                      10,
                      self._sub("Компаньон на рабочем столе. Понимает текст, управляет Windows "
                                "и отвечает на вопросы. Всё работает на твоём ПК."),
                      10,
                      self._sub("Займёт около минуты."))

    def _page_options(self):
        self.opt_auto = QCheckBox("Запускать вместе с Windows")
        self.opt_auto.setChecked(True)
        self.opt_short = QCheckBox("Ярлык на рабочем столе")
        self.opt_short.setChecked(True)
        if self.ollama_ok:
            self.ollama_lbl = QLabel("✓ Ollama найдена, ответы будут работать")
            self.ollama_lbl.setObjectName("ok")
        else:
            self.ollama_lbl = QLabel("Для ответов нужна Ollama. Установи её один раз, модели Mico AI скачает сам.")
            self.ollama_lbl.setObjectName("warn")
        self.ollama_lbl.setWordWrap(True)
        ob = QPushButton("Открыть страницу Ollama")
        ob.clicked.connect(lambda: os.startfile("https://ollama.com/download"))
        ob.setFixedWidth(230)
        return column(self._title("Параметры"), 14,
                      self.opt_auto, self.opt_short, 18,
                      self.ollama_lbl, 10, ob)

    def _page_install(self):
        self.percent = QLabel("0%")
        self.percent.setObjectName("percent")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.status = QLabel("Готовлюсь…")
        self.status.setObjectName("sub")
        self.status.setWordWrap(True)
        return column(self._title("Устанавливаю"), 18, self.percent, 12, self.bar, 14, self.status)

    def _page_finish(self):
        self.run_cb = QCheckBox("Запустить Mico AI")
        self.run_cb.setChecked(True)
        return column(self._title("Готово"), 10,
                      self._sub("Mico AI установлен и готов к работе."), 20,
                      self.run_cb)

    # ---------- переходы ----------
    def _go(self, i):
        self.pages.setCurrentIndex(i)
        self.step_lbl.setText(self.PAGE_STEP[i])
        self.back_b.setVisible(i == 1)
        self.next_b.setText({0: "Далее", 1: "Установить", 2: "…", 3: "Закрыть"}[i])
        self.next_b.setEnabled(i != 2)
        self.cancel_b.setVisible(i != 3)
        self.avatar.setPixmap(render_mico(self.PAGE_MOOD[i], 150))

    def _next(self):
        i = self.pages.currentIndex()
        if i == 0:
            self._go(1)
        elif i == 1:
            self._go(2)
            self._fade_pages()
            self._start_install()
        elif i == 3:
            if self.run_cb.isChecked() and os.path.exists(INSTALL_EXE):
                os.startfile(INSTALL_EXE)
            self.accept()

    # ---------- установка ----------
    def _start_install(self):
        self._worker = _Worker(self)
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _animate_to(self, target, ms, after=None):
        """Полоска и проценты плавно едут к target. Новый вызов отменяет предыдущий ход."""
        if getattr(self, "_bar_anim", None) is not None:
            self._bar_anim.stop()
        anim = QVariantAnimation(self)
        anim.setStartValue(self.bar.value())
        anim.setEndValue(int(target))
        anim.setDuration(ms)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def show(v):
            n = int(round(float(v)))
            self.bar.setValue(n)
            self.percent.setText(f"{n}%")
        anim.valueChanged.connect(show)
        if after is not None:
            anim.finished.connect(after)
        self._bar_anim = anim
        anim.start()

    def _fade_pages(self):
        """Смена страницы: содержимое плавно проявляется, а не появляется рывком."""
        effect = QGraphicsOpacityEffect(self.pages)
        self.pages.setGraphicsEffect(effect)
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(340)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(lambda v: effect.setOpacity(float(v)))
        anim.finished.connect(lambda: self.pages.setGraphicsEffect(None))   # без эффекта текст чёткий
        self._fade_anim = anim
        anim.start()

    def _on_progress(self, pct, text, mood):
        self.status.setText(text)
        self.avatar.setPixmap(render_mico(mood, 150))
        self._animate_to(pct, 620)

    def _on_done(self, err):
        if err:
            self.status.setText(f"Не получилось: {err}. Если Mico AI открыт, закрой его и запусти установку снова.")
            self.next_b.setEnabled(True)
            self.next_b.setText("Закрыть")
            self.next_b.clicked.disconnect()
            self.next_b.clicked.connect(self.reject)
            return
        def finish():                                    # полоска дошла до 100% — даём её увидеть и переходим
            QTimer.singleShot(260, lambda: (self._go(3), self._fade_pages()))
        self.status.setText("Готово")
        self._animate_to(100, 520, after=finish)


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
            if i:
                time.sleep(0.45)                         # шаги идут не мгновенно: прогресс успевает быть видным
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


REMOVER_PATH = os.path.join(INSTALL_DIR, "remove_mico.cmd")


def _write_remover():
    """Скрипт удаления рядом с программой: работает, даже если Mico.exe сам не запускается."""
    import remover
    os.makedirs(INSTALL_DIR, exist_ok=True)
    with open(REMOVER_PATH, "w", encoding="ascii", newline="") as f:
        f.write(remover.script(INSTALL_DIR, APPDIR))


def _register_uninstall():
    """Регистрирует Mico AI в «Параметры → Приложения», чтобы его можно было удалить штатным способом."""
    import winreg
    uninstall_cmd = f'"{INSTALL_EXE}" --uninstall'          # удаление через наш мастер, а не консольный скрипт
    k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, winreg.KEY_SET_VALUE)
    values = {"DisplayName": "Mico AI", "DisplayVersion": _version(), "Publisher": "Mico AI",
              "InstallLocation": INSTALL_DIR,
              "DisplayIcon": ICON_PATH if os.path.exists(ICON_PATH) else INSTALL_EXE,
              "UninstallString": uninstall_cmd}
    for name, value in values.items():
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
    winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
    winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)
    winreg.CloseKey(k)


def refresh_uninstall_entry():
    """Старые установки прописывали удаление консольным скриптом (remove_mico.cmd). При каждом запуске
    установленного Mico AI запись в «Приложениях» приводится к мастеру, а старый скрипт удаляется."""
    if not FROZEN or os.path.normcase(sys.executable) != os.path.normcase(INSTALL_EXE):
        return
    import winreg
    expected = f'"{INSTALL_EXE}" --uninstall'
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, winreg.KEY_READ)
        current, _ = winreg.QueryValueEx(k, "UninstallString")
        winreg.CloseKey(k)
    except OSError:
        current = None
    if current != expected:
        _register_uninstall()
    if os.path.exists(REMOVER_PATH):
        try:
            os.remove(REMOVER_PATH)
        except OSError:
            pass


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
    import version
    cfg.update(autostart=autostart_on, greet_on_start=True, update_channel=version.BUILD_CHANNEL)
    cfg.setdefault("last_version", _version())            # не показывать «что нового» сразу после установки
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _version():
    import version
    return version.APP_VERSION


# ============================ Бета-программа ============================
def run():
    """Мастер установки. Возвращает после закрытия; установленная копия запускается сама."""
    dlg = Wizard()
    dlg.exec()


# ============================ Удаление ============================
def is_uninstall_request():
    return "--uninstall" in sys.argv


_NOWIN = 0x08000000 if os.name == "nt" else 0        # не показывать окно консоли (только Windows)
_DETACHED = 0x00000008 if os.name == "nt" else 0


def _dir_size_mb(path):
    total = 0
    for dp, _dn, fn in os.walk(path):
        for f in fn:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total // (1024 * 1024)


def _mico_ollama_models():
    """Модели, которые Mico AI использует (из его настроек). Удаляются только по галочке: их могут брать другие программы."""
    names = []
    try:
        with open(os.path.join(APPDIR, "config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        for key in ("text_model", "vision_model"):
            name = cfg.get(key)
            if name and name not in names:
                names.append(name)
    except Exception:
        pass
    return names


class _Remover(QThread):
    """Шаги удаления, которые можно сделать, пока Mico AI работает. Файлы программы и данных удаляет отдельный скрипт после выхода."""
    progress = pyqtSignal(int, str)
    done = pyqtSignal(str)

    def __init__(self, choices, ollama_names):
        super().__init__()
        self.choices = choices
        self.ollama_names = ollama_names
        self.errors = []          # понятные сообщения о том, что не удалось
        self.failed = set()       # ключи шагов, которые не выполнились: такие не попадают в «удалено»

    def _steps(self):
        steps = []
        if self.choices.get("autostart"):
            steps.append(("autostart", "Снимаю автозапуск", self._autostart))
        if self.choices.get("shortcut"):
            steps.append(("shortcut", "Удаляю ярлык на рабочем столе", self._shortcut))
        if self.choices.get("ollama") and self.ollama_names:
            steps.append(("ollama", "Удаляю модели Ollama", self._ollama))
        steps.append(("program", "Убираю запись из «Приложений» Windows", _unregister_uninstall))
        return steps

    def _autostart(self):
        import autostart
        autostart.remove()

    def _shortcut(self):
        _desktop_shortcut(create=False)

    def _ollama(self):
        bad = []
        for name in self.ollama_names:
            try:
                r = subprocess.run(["ollama", "rm", name], capture_output=True, timeout=180,
                                   creationflags=_NOWIN)
                if r.returncode != 0:
                    bad.append(name)
            except FileNotFoundError:
                raise RuntimeError("Ollama не найдена, модели не тронуты")
            except Exception:
                bad.append(name)
        if bad:
            raise RuntimeError("не удалось удалить " + ", ".join(bad))

    def run(self):
        steps = self._steps()
        try:
            for i, (key, text, fn) in enumerate(steps):
                if i:
                    time.sleep(0.45)                     # шаги видны, а не мелькают
                self.progress.emit(int(i / len(steps) * 100), text)
                try:
                    fn()
                except Exception as e:
                    self.failed.add(key)
                    self.errors.append(f"{text} ({e})")
            self.progress.emit(100, "Почти готово")
            self.done.emit("")
        except Exception as e:
            self.done.emit(f"{e.__class__.__name__}: {e}")


class Uninstaller(QDialog):
    """Мастер удаления в стиле установщика: сначала выбор, что удалить, потом плавный прогресс и итог."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.removed = False
        self.worker = None
        self.ollama_names = _mico_ollama_models()
        self.setObjectName("wizard")
        self.setWindowTitle("Удаление Mico AI")
        self.setFixedSize(700, 480)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(QSS)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        side = QFrame()
        side.setObjectName("side")
        side.setFixedWidth(230)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 36)
        sv.addStretch()
        self.avatar = QLabel()
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand = QLabel("Mico AI")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sv.addWidget(self.avatar)
        sv.addSpacing(10)
        sv.addWidget(brand)
        sv.addStretch()
        root.addWidget(side)

        right = QVBoxLayout()
        right.setContentsMargins(40, 34, 40, 30)
        right.setSpacing(0)
        self.step_lbl = QLabel("Удаление")
        self.step_lbl.setObjectName("step")
        right.addWidget(self.step_lbl)
        right.addSpacing(10)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._page_choose())
        self.pages.addWidget(self._page_progress())
        self.pages.addWidget(self._page_done())
        right.addWidget(self.pages, 1)

        row = QHBoxLayout()
        self.cancel_b = QPushButton("Отмена")
        self.cancel_b.clicked.connect(self.reject)
        self.next_b = QPushButton("Удалить")
        self.next_b.setObjectName("primary")
        self.next_b.clicked.connect(self._start)
        row.addWidget(self.cancel_b)
        row.addStretch()
        row.addWidget(self.next_b)
        right.addLayout(row)
        self.btn_row_widget = row
        root.addLayout(right, 1)
        self._go(0)

    # ---------- страницы ----------
    def _choice(self, key, title, hint, checked):
        box = QCheckBox(title)
        box.setChecked(checked)
        self.choices[key] = box
        hint_lbl = QLabel(hint)
        hint_lbl.setObjectName("sub")
        hint_lbl.setWordWrap(True)
        hint_lbl.setContentsMargins(30, 0, 0, 6)
        block = QWidget()
        lay = QVBoxLayout(block)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(box)
        lay.addWidget(hint_lbl)
        return block

    def _page_choose(self):
        self.choices = {}
        items = [self._title("Удалить Mico AI?"), 6,
                 self._sub("Программу удалим в любом случае. Остальное выбираешь сам."), 14]
        items.append(self._choice("shortcut", "Ярлык на рабочем столе",
                                  "Запись в «Приложениях» Windows удалится в любом случае.", True))
        items.append(self._choice("autostart", "Автозапуск с Windows",
                                  "Mico AI перестанет запускаться при входе в систему.", True))
        items.append(self._choice("data", "История, настройки и напоминания",
                                  "Чат, память и напоминания. Оставь, если переустановишь Mico AI с прежними данными.",
                                  False))
        if self.ollama_names:
            items.append(self._choice("ollama", "Модели Ollama, которые использовал Mico AI",
                                      "Их могут использовать другие программы. Удаляются командой ollama rm.",
                                      False))
        size = _dir_size_mb(INSTALL_DIR) if os.path.isdir(INSTALL_DIR) else 0
        items += [14, self._sub(f"Программа Mico AI · {size} МБ")]
        return column(*items)

    def _page_progress(self):
        self.percent = QLabel("0%")
        self.percent.setObjectName("percent")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.status = QLabel("Готовлюсь…")
        self.status.setObjectName("sub")
        self.status.setWordWrap(True)
        return column(self._title("Удаляю"), 18, self.percent, 12, self.bar, 14, self.status)

    def _page_done(self):
        self.done_text = QLabel("")
        self.done_text.setObjectName("sub")
        self.done_text.setWordWrap(True)
        return column(self._title("Mico AI удалён"), 10, self.done_text)

    def _title(self, text):
        t = QLabel(text)
        t.setObjectName("title")
        return t

    def _sub(self, text):
        s = QLabel(text)
        s.setObjectName("sub")
        s.setWordWrap(True)
        return s

    # ---------- переходы ----------
    def _go(self, i):
        self.pages.setCurrentIndex(i)
        self.step_lbl.setText({0: "Удаление", 1: "Удаление", 2: "Готово"}[i])
        self.cancel_b.setVisible(i == 0)
        self.next_b.setVisible(i != 2)
        self.next_b.setText({0: "Удалить", 1: "…"}[i] if i != 2 else "")
        self.next_b.setEnabled(i != 1)
        self.avatar.setPixmap(render_mico({0: "thinking", 1: "curious", 2: "love"}[i], 150))

    def _fade_pages(self):
        effect = QGraphicsOpacityEffect(self.pages)
        self.pages.setGraphicsEffect(effect)
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(340)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(lambda v: effect.setOpacity(float(v)))
        anim.finished.connect(lambda: self.pages.setGraphicsEffect(None))
        self._fade_anim = anim
        anim.start()

    def _animate_to(self, target, ms, after=None):
        if getattr(self, "_bar_anim", None) is not None:
            self._bar_anim.stop()
        anim = QVariantAnimation(self)
        anim.setStartValue(self.bar.value())
        anim.setEndValue(int(target))
        anim.setDuration(ms)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def show(v):
            n = int(round(float(v)))
            self.bar.setValue(n)
            self.percent.setText(f"{n}%")
        anim.valueChanged.connect(show)
        if after is not None:
            anim.finished.connect(after)
        self._bar_anim = anim
        anim.start()

    # ---------- удаление ----------
    def _start(self):
        picked = {k: box.isChecked() for k, box in self.choices.items()}
        self.picked = picked
        self._go(1)
        self._fade_pages()
        self.worker = _Remover(picked, self.ollama_names if picked.get("ollama") else [])
        self.worker.progress.connect(self._on_progress)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _on_progress(self, pct, text):
        self.status.setText(text)
        self._animate_to(pct, 620)

    def _on_done(self, err):
        if err:
            self.status.setText(f"Не получилось: {err}")
            self.next_b.setEnabled(True)
            return

        def finish():
            QTimer.singleShot(260, self._finish_removal)
        self.status.setText("Готово")
        self._animate_to(100, 520, after=finish)

    def _finish_removal(self):
        """Программу и данные удаляет скрипт: он ждёт, пока Mico AI закроется, и только потом трогает файлы."""
        picked = self.picked
        failed = self.worker.failed if self.worker else set()
        _schedule_file_removal(delete_data=picked.get("data", False))
        self.removed = True
        removed = ["программа Mico AI"]
        if picked.get("shortcut") and "shortcut" not in failed:
            removed.append("ярлык на рабочем столе")
        if "program" not in failed:
            removed.append("запись в «Приложениях» Windows")
        if picked.get("autostart") and "autostart" not in failed:
            removed.append("автозапуск")
        if picked.get("data"):
            removed.append("история и настройки")
        if picked.get("ollama") and "ollama" not in failed:
            removed.append("модели Ollama")
        kept = []
        if not picked.get("data"):
            kept.append("история и настройки в папке Mico AI (AppData)")
        if not picked.get("ollama") and self.ollama_names:
            kept.append("модели Ollama")
        text = "Удалено: " + ", ".join(removed) + "."
        if kept:
            text += "\n\nОсталось по твоему выбору: " + ", ".join(kept) + "."
        if self.worker and self.worker.errors:
            text += "\n\nНе получилось: " + "; ".join(self.worker.errors) + ". Можно повторить позже."
        self.done_text.setText(text)
        self._go(2)
        self._fade_pages()
        self.next_b.setText("Закрыть")
        self.next_b.setVisible(True)
        self.next_b.setEnabled(True)
        self.next_b.clicked.disconnect()
        self.next_b.clicked.connect(self._close_app)

    def _close_app(self):
        self.accept()
        if self.app is not None:
            self.app.quit()

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            event.ignore()                                  # во время удаления окно не закрыть: иначе шаги оборвутся
            return
        super().closeEvent(event)


def uninstall(app):
    """Мастер удаления: выбор, что удалить, плавный прогресс и итог. Возвращает True, если удаление выполнено."""
    if not FROZEN:
        QMessageBox.information(None, "Mico AI", "Удаление доступно только для установленной версии Mico AI.")
        return False
    dlg = Uninstaller(app)
    dlg.exec()
    return dlg.removed


def _schedule_file_removal(delete_data):
    """Скрипт в %TEMP%: ждёт выхода Mico AI, удаляет его папку и по выбору данные, затем удаляет себя."""
    script = os.path.join(os.environ.get("TEMP", "."), "mico_uninstall.cmd")
    lines = [
        "@echo off",
        f'taskkill /f /im Mico.exe /fi "PID ne {os.getpid()}" >nul 2>&1',   # другие запущенные копии Mico AI не дадут удалить файл
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
    subprocess.Popen(["cmd", "/c", script], creationflags=_NOWIN | _DETACHED)     # без окна, отдельно
