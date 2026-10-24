"""Светлая/тёмная тема Mico AI: ручной выбор или как в Windows. Основной текст — Segoe UI Variable, заголовки — Nunito Bold."""
import os, sys

# Основной текст — системный Segoe UI Variable (Windows 11), с нормальными весами: читается ровно и без перегруза.
# Заголовки, кнопки-акценты и подписи «Mico AI» — Nunito Bold 700 (файл assets/fonts/Nunito-Bold.ttf регистрируется при запуске).
FONT_FAMILY = "Segoe UI Variable Text"
FONT_DISPLAY = "Nunito"
FONT_DISPLAY_WEIGHT = 700
FONT_FILES = ["Nunito-Bold.ttf"]
# Этот кусок стиля добавляется в КАЖДЫЙ стиль: иначе виджет с размером из стиля теряет семейство шрифта
FONT_QSS = (f'QWidget {{ font-family: "{FONT_FAMILY}"; }}\n'
            f'QLabel#title, QLabel#pageTitle, QLabel#wiTitle, QLabel#tileTitle, QLabel#expTitle, QLabel#brand, '
            f'QLabel#percent, QPushButton#primary {{ font-family: "{FONT_DISPLAY}"; font-weight: {FONT_DISPLAY_WEIGHT}; }}\n')


def heading(text):
    """Заголовок внутри HTML (QLabel/QTextBrowser): Nunito Bold, остальной текст — Segoe UI Variable."""
    return f'<span style="font-family:{FONT_DISPLAY};font-weight:{FONT_DISPLAY_WEIGHT}">{text}</span>'


def fluent(dark):
    """Палитра Windows 11 (Fluent): нейтральные поверхности, тонкие обводки, без бежевых и розовых оттенков."""
    if dark:
        return {"bg": "#202020", "card": "#2b2b2b", "raised": "#383838", "field": "#2d2d2d", "stroke": "#3a3a3a",
                "text": "#ffffff", "muted": "#a6a6a6", "hover": "#3a3a3a", "press": "#2c2c2c"}
    return {"bg": "#f3f3f3", "card": "#ffffff", "raised": "#fbfbfb", "field": "#ffffff", "stroke": "#e5e5e5",
            "text": "#1a1a1a", "muted": "#5d5d5d", "hover": "#f6f6f6", "press": "#f0f0f0"}


def on_accent(hex_color):
    """Текст поверх акцентного цвета: тёмный на светлом, белый на тёмном (как в Windows 11)."""
    from intel import hex_rgb
    r, g, b = hex_rgb(hex_color)
    return "#1a1a1a" if 0.299 * r + 0.587 * g + 0.114 * b > 150 else "#ffffff"


def round_mask(btn, size):
    """Кнопка-цвет становится кружком: маска-эллипс режет углы при любом стиле (общий QSS не перебивает)."""
    from PyQt6.QtGui import QRegion
    btn.setFixedSize(size, size)
    btn.setMask(QRegion(0, 0, size, size, QRegion.RegionType.Ellipse))


def swatch_qss(hex_color):
    """Кнопка-цвет (цвет Mico, волны, действия): показывает сам цвет, подпись читается на любом оттенке."""
    return (f"background:{hex_color}; color:{on_accent(hex_color)}; border:1px solid rgba(128,128,128,0.35); "
            "border-radius:4px; padding:4px 12px;")


def load_fonts(base=None):
    """Регистрирует шрифты из assets/fonts, если они есть (сейчас не поставляются). True — основной шрифт найден."""
    from PyQt6.QtGui import QFontDatabase
    if base is None:
        base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    for name in FONT_FILES:
        path = os.path.join(base, "assets", "fonts", name)
        if os.path.exists(path):
            QFontDatabase.addApplicationFont(path)
    return FONT_DISPLAY in QFontDatabase.families()


def system_dark():
    """True, если в Windows включена тёмная тема приложений."""
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except Exception:
        pass
    try:  # запасной вариант: Qt 6.5+
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QGuiApplication
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


def is_dark(cfg):
    mode = cfg.get("theme", "auto")
    return True if mode == "dark" else False if mode == "light" else system_dark()


def panel_qss(accent, dark, outline=True, k=1.0, glow=True):
    """Стиль окна чата: поверхности как в Windows 11, плоские кнопки, мягкие поля ввода."""
    f = fluent(dark)
    edge = f"1px solid {accent}" if outline else "none"
    fs = lambda px: max(8, round(px * k))          # шрифты масштабируются вместе с окном чата
    r = lambda px: max(6, round(px * k))
    hov_edge = f"border:1px solid {accent};" if glow else ""   # подсветка при наведении — по настройке
    on = on_accent(accent)
    if dark:
        card, text, muted = "rgba(32,32,32,242)", "#ffffff", "#a6a6a6"
        field, field_edge, tint, tint_hi = "rgba(255,255,255,0.06)", "rgba(255,255,255,0.08)", "rgba(255,255,255,0.06)", "rgba(255,255,255,0.10)"
        handle = "rgba(255,255,255,0.25)"
    else:
        card, text, muted = "rgba(249,249,249,242)", "#1a1a1a", "#5c5c5c"
        field, field_edge, tint, tint_hi = "#ffffff", "rgba(0,0,0,0.08)", "rgba(0,0,0,0.04)", "rgba(0,0,0,0.07)"
        handle = "rgba(0,0,0,0.25)"
    return FONT_QSS + f"""
        #card{{background:{card};border-radius:{r(10)}px;border:{edge};}}
        QTextBrowser{{background:transparent;border:none;color:{text};font-size:{fs(13)}px;}}
        QLineEdit{{background:{field};border:1px solid {field_edge};border-radius:{r(8)}px;padding:8px 12px;color:{text};
                   selection-background-color:{accent};selection-color:{on};}}
        QLineEdit:focus{{border:1px solid {accent};}}
        QPushButton{{background:{tint};border:none;border-radius:{r(6)}px;padding:5px 10px;color:{text};font-size:{fs(12)}px;}}
        QPushButton:hover{{background:{tint_hi};{hov_edge}}}
        QPushButton:pressed{{background:{tint};}}
        QPushButton:checked{{background:{accent};color:{on};}}
        QPushButton#ghost{{background:transparent;color:{muted};padding:4px 8px;}}
        QPushButton#ghost:hover{{background:{tint_hi};color:{text};}}
        QLabel#status{{color:{muted};font-size:{fs(11)}px;padding-left:4px;}}
        QScrollBar:vertical{{background:transparent;width:8px;margin:4px 0;}}
        QScrollBar::handle:vertical{{background:{handle};border-radius:4px;min-height:28px;}}
        QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
        QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{{background:none;}}"""


LINK_LIGHT = "a{color:#1a62c9;}"
LINK_DARK = "a{color:#8ab4ff;}"


def app_qss(dark):
    """Стиль диалогов/меню приложения (QWidget не трогаем — иначе испортим прозрачные окна Mico AI)."""
    if not dark:
        return FONT_QSS
    return FONT_QSS + """
        QDialog, QMessageBox, QColorDialog {background:#2b2b2b;color:#ffffff;}
        QDialog QLabel, QMessageBox QLabel, QCheckBox, QRadioButton {color:#ffffff;background:transparent;}
        QTabWidget::pane {border:1px solid #3a3a3a;border-radius:8px;top:-1px;}
        QTabBar::tab {background:#2b2b2b;color:#d0d0d0;padding:6px 12px;border:1px solid #3a3a3a;
                      border-bottom:none;border-top-left-radius:6px;border-top-right-radius:6px;}
        QTabBar::tab:selected {background:#3a3a3a;color:#fff;}
        QLineEdit, QComboBox, QSpinBox, QAbstractSpinBox {background:#2b2b2b;color:#ffffff;border:1px solid #3a3a3a;
                      border-radius:8px;padding:3px 6px;selection-background-color:#4a4a4a;}
        QComboBox QAbstractItemView {background:#2b2b2b;color:#ffffff;selection-background-color:#444444;}
        QPushButton {background:#3a3a3a;color:#ffffff;border:1px solid #444444;border-radius:8px;padding:5px 12px;}
        QPushButton:hover {background:#444444;}
        QPushButton:disabled {color:#6b6b6b;}
        QSlider::groove:horizontal {height:4px;background:#3a3a3a;border-radius:8px;}
        QSlider::handle:horizontal {background:#ffffff;width:14px;margin:-6px 0;border-radius:7px;}
        QCheckBox::indicator {width:15px;height:15px;border:1px solid #6b6b6b;border-radius:8px;background:#2b2b2b;}
        QCheckBox::indicator:checked {background:#0078d4;}
        QMenu {background:#2b2b2b;color:#ffffff;border:1px solid #3a3a3a;padding:4px;}
        QMenu::item {padding:6px 22px;border-radius:8px;}
        QMenu::item:selected {background:#444444;}
        QMenu::separator {height:1px;background:#3a3a3a;margin:4px 8px;}
        QToolTip {background:#2b2b2b;color:#ffffff;border:1px solid #3a3a3a;}
    """


def settings_qss(accent, dark):
    """Оформление окна настроек: плоские карточки, скруглённые поля, акцентный цвет Mico."""
    f = fluent(dark)
    bg, card, border, text, field, muted = f["bg"], f["card"], f["stroke"], f["text"], f["field"], f["muted"]
    on = on_accent(accent)
    return FONT_QSS + f"""
        QDialog {{ background:{bg}; color:{text}; font-size:13px; }}
        QTabWidget::pane {{ border:none; }}
        QScrollArea {{ background:transparent; border:none; }}
        QScrollArea > QWidget > QWidget {{ background:transparent; }}
        QTabBar::tab {{ background:transparent; color:{muted}; padding:6px 10px; margin-right:2px;
                        border-radius:10px; font-weight:600; }}
        QTabBar::tab:selected {{ background:{accent}; color:{on_accent(accent)}; }}
        QTabBar::tab:hover:!selected {{ color:{text}; }}
        QTabBar QToolButton {{ width:20px; background:transparent; }}
        QGroupBox {{ background:{card}; border:1px solid {border}; border-radius:12px;
                     margin-top:14px; padding:10px 12px 8px 12px; font-weight:600; }}
        QGroupBox::title {{ subcontrol-origin:margin; left:12px; top:2px; padding:0 4px; color:{text}; }}
        QLabel {{ color:{text}; }}
        QLineEdit, QComboBox, QSpinBox, QListWidget {{ background:{field}; border:1px solid {border};
                     border-radius:10px; padding:4px 8px; color:{text}; }}
        QListWidget::item {{ padding:4px 2px; }}
        QToolButton {{ background:{field}; border:1px solid {border}; border-radius:12px; color:{text};
                       font-weight:600; }}
        QToolButton:hover {{ border-color:{accent}; }}
        QFrame#subTile {{ background:{card}; border:1px solid {border}; border-radius:14px; }}
        QFrame#subTile:hover {{ border-color:{accent}; background:{field}; }}
        QLabel#tileTitle {{ color:{text}; font-size:15px; font-weight:700; background:transparent; }}
        QPushButton {{ background:{field}; border:1px solid {border}; border-radius:12px; padding:9px 18px;
                       min-height:22px; color:{text}; font-size:13px; }}
        QPushButton:hover {{ border-color:{accent}; }}
        QPushButton:pressed {{ background:{accent}; color:{on_accent(accent)}; }}
        QPushButton#primary {{ background:{accent}; border-color:{accent}; color:{on_accent(accent)}; font-weight:700; }}
        QPushButton#primary:hover {{ background:{accent}; border-color:{text}; }}
        QPushButton#flat {{ background:transparent; border:none; color:{muted}; padding:2px 4px; }}
        QPushButton#flat:hover {{ color:{text}; }}
        QCheckBox {{ spacing:9px; color:{text}; }}
        QCheckBox::indicator {{ width:16px; height:16px; border-radius:8px; border:1px solid {border};
                                background:{field}; }}
        QCheckBox::indicator:checked {{ background:{accent}; border-color:{accent}; }}
        QSlider {{ background:transparent; border:none; min-height:22px; }}
        QSlider::groove:horizontal {{ height:6px; background:{border}; border-radius:8px; }}
        QSlider::handle:horizontal {{ background:{accent}; width:16px; height:16px; margin:-5px 0; border-radius:8px; }}
        QProgressBar {{ background:{field}; border:none; border-radius:8px; height:10px; text-align:center; }}
        QProgressBar::chunk {{ background:{accent}; border-radius:8px; }}
    """


# Стили для окна настроек: кнопка «Сбросить» у каждой настройки и серые подсказки.
RESET_QSS = """
    QPushButton#resetRow { background:transparent; color:#8a8a8a; border:none;
                           border-radius:4px; padding:2px 8px; font-size:11px; }
    QPushButton#resetRow:hover { background:rgba(128,128,128,0.18); color:#8a8a8a; }
    QLabel#hint { color:#8a8a8a; font-size:11px; font-style:italic; }
    QLabel#settingDesc { color:#8a8a8a; font-family:Georgia,serif; font-size:13px; font-style:normal; font-weight:400;
                         border-left:2px solid rgba(128,128,128,0.45); padding:2px 0 2px 9px; background:transparent; }
    QLabel#readout { color:#8f8f8f; font-size:12px; }
"""


def app_font(size=10):
    """Шрифт для QApplication.setFont: все виджеты берут его, если не заданы свои."""
    from PyQt6.QtGui import QFont
    f = QFont(FONT_FAMILY, size)
    f.setFamilies([FONT_FAMILY, "Segoe UI Variable Display", "Segoe UI", "Arial"])     # запасные — только если основной шрифт не нашёлся
    return f



def chevron_url(color):
    """Стрелка для полей выбора: Qt берёт её только из файла. Пишем маленький SVG в папку Mico."""
    import os
    folder = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Mico", "ui")
    try:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "chevron_" + color.strip("#") + ".svg")
        if not os.path.exists(path):
            svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12">'
                   f'<path d="M2.5 4.2 L6 7.7 L9.5 4.2" fill="none" stroke="{color}" stroke-width="1.6" '
                   'stroke-linecap="round" stroke-linejoin="round"/></svg>')
            with open(path, "w", encoding="utf-8") as f:
                f.write(svg)
        return path.replace(chr(92), "/")
    except OSError:
        return ""


def wi_settings_qss(accent, dark):
    """Настройки Mico AI: сайдбар с иконками слева, плитки-карточки справа, мягкие скругления.
    Тёмная тема — как на референсе; светлая — те же плитки на светлом фоне."""
    from intel import hex_rgb
    r, g, b = hex_rgb(accent)
    f = fluent(dark)
    bg, tile, tile_hi, field, text, muted, border = f["bg"], f["card"], f["raised"], f["field"], f["text"], f["muted"], f["stroke"]
    on = on_accent(accent)
    arrow = chevron_url(muted)
    from design import RADIUS
    RADIUS_S, RADIUS_M, RADIUS_L, RADIUS_PILL, RADIUS_HAIR = RADIUS["s"], RADIUS["m"], RADIUS["l"], RADIUS["pill"], RADIUS["hair"]
    return FONT_QSS + f"""
        QDialog {{ background:{bg}; color:{text}; font-size:13px; }}
        QTabWidget::pane {{ border:none; }}
        QScrollArea {{ background:transparent; border:none; }}
        QScrollArea > QWidget > QWidget {{ background:transparent; }}
        QScrollBar:vertical {{ background:transparent; width:8px; margin:4px 0; }}
        QScrollBar::handle:vertical {{ background:{border}; {RADIUS_S}px; min-height:36px; }}
        QScrollBar::handle:vertical:hover {{ background:{muted}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; background:none; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:none; }}
        QListWidget#sideNav {{ background:{bg}; border:none; outline:0; padding:6px 0; }}
        QListWidget#sideNav::item {{ color:{muted}; padding:10px 14px; margin:2px 10px;
                                    {RADIUS_M}px; font-weight:600; }}
        QListWidget#sideNav::item:hover:!selected {{ color:{text}; background:{tile}; }}
        QListWidget#sideNav::item:selected {{ background:{tile_hi}; color:{text}; font-weight:600; }}
        QListWidget#sideNav::item:disabled {{ color:{border}; }}
        QLabel#pageTitle {{ color:{text}; font-size:22px; font-weight:700; background:transparent;
                            padding:0 2px 4px 2px; }}
        QGroupBox {{ background:{tile}; border:none; {RADIUS_L}px; margin-top:20px;
                     padding:12px 14px 10px 14px; font-weight:600; }}
        QFrame#expander {{ background:transparent; border:none; }}
        QLabel#expTitle {{ color:{text}; font-size:13px; font-weight:700; background:transparent; }}
        QGroupBox::title {{ subcontrol-origin:margin; left:16px; top:-2px; color:{muted};
                            font-size:11px; font-weight:600; }}
        QLabel {{ color:{text}; background:transparent; }}
        QLabel#hint {{ color:{muted}; font-size:11px; font-style:italic; }}
        QLabel#settingDesc {{ color:{muted}; font-family:Georgia,serif; font-size:13px; font-style:normal; font-weight:400;
                              border-left:2px solid {accent}; padding:2px 0 2px 9px; background:transparent; }}
        QLabel#readout {{ color:{muted}; font-size:12px; }}
        QFrame#wiHead {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                         stop:0 rgba({r},{g},{b},0.40), stop:1 {tile}); {RADIUS_L}px; }}
        QLabel#wiTitle {{ font-size:22px; font-weight:700; background:transparent; }}
        QLabel#wiSub {{ color:{muted}; font-size:12px; background:transparent; }}
        QLineEdit, QComboBox, QSpinBox, QTimeEdit, QListWidget {{ background:{field}; border:none;
                     {RADIUS_S}px; padding:7px 12px; color:{text}; selection-background-color:{accent}; }}
        QLineEdit#search {{ {RADIUS_M}px; padding:8px 12px; }}
        QComboBox {{ padding-right:30px; }}
        QComboBox::drop-down {{ subcontrol-origin:padding; subcontrol-position:center right; border:none; width:30px; }}
        QComboBox::down-arrow {{ image:url("{arrow}"); width:12px; height:12px; }}
        QComboBox QAbstractItemView {{ background:{tile}; border:1px solid {border}; {RADIUS_M}px;
                     padding:4px; selection-background-color:{accent}; selection-color:{on}; outline:0; }}
        QCheckBox {{ spacing:12px; color:{text}; }}
        QCheckBox::indicator {{ width:38px; height:22px; {RADIUS_PILL}px; background:{border}; border:none; }}
        QCheckBox::indicator:checked {{ background:{accent}; }}
        QSlider::groove:horizontal {{ height:4px; background:{border}; border-radius:{RADIUS_HAIR}px; }}
        QSlider::sub-page:horizontal {{ background:{accent}; border-radius:{RADIUS_HAIR}px; }}
        QSlider::handle:horizontal {{ background:#ffffff; width:16px; height:16px; margin:-6px 0;
                                      {RADIUS_M}px; border:none; }}
        QPushButton {{ background:{field}; color:{text}; border:none; {RADIUS_S}px; padding:8px 14px; }}
        QPushButton:hover {{ background:{tile_hi}; }}
        QPushButton#primary {{ background:{accent}; color:{on}; font-weight:700; }}
        QPushButton#flat {{ background:transparent; color:{muted}; }}
    """


def windows_accent(default="#4cc2c4"):
    """Цвет акцента, который выбрал пользователь в Windows (Параметры → Персонализация → Цвета).
    Не удалось прочитать — запасной цвет."""
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\DWM")
        v, _ = winreg.QueryValueEx(k, "AccentColor")                # в формате ABGR
        return f"#{v & 0xFF:02x}{(v >> 8) & 0xFF:02x}{(v >> 16) & 0xFF:02x}"
    except Exception:
        return default



def mica_supported():
    """Mica есть только в Windows 11 (сборка 22000 и новее)."""
    try:
        import sys
        return sys.platform == "win32" and sys.getwindowsversion().build >= 22000
    except Exception:
        return False


def apply_mica(widget):
    """Включает фон Mica у окна Windows 11 и тёмную рамку по теме системы. На других системах ничего не делает."""
    if not mica_supported():
        return False
    try:
        import ctypes
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        dark = ctypes.c_int(1 if system_dark() else 0)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))   # DWMWA_USE_IMMERSIVE_DARK_MODE
        backdrop = ctypes.c_int(2)                                                       # DWMSBT_MAINWINDOW = Mica
        return dwm.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop), ctypes.sizeof(backdrop)) == 0
    except Exception:
        return False
