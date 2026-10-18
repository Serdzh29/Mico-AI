"""Светлая/тёмная тема Mico AI: ручной выбор или как в Windows. Единый шрифт — системный Segoe UI Variable."""
import os, sys

# Единый шрифт во всём Mico AI: чат, пузырь, кнопки, настройки. Segoe UI Variable — системный шрифт Windows 11,
# им же пользуются «Параметры» и такие приложения, как Wintoys. Шрифт не поставляется с программой.
FONT_FAMILY = "Segoe UI Variable Text"
FONT_FILES = []
# Этот кусок стиля добавляется в КАЖДЫЙ стиль: иначе виджет с размером из стиля теряет семейство шрифта
FONT_QSS = f'QWidget {{ font-family: "{FONT_FAMILY}"; }}\n'


def load_fonts(base=None):
    """Регистрирует шрифты, которые лежат вместе с программой (assets/fonts). True — Inter доступен."""
    from PyQt6.QtGui import QFontDatabase
    if base is None:
        base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    for name in FONT_FILES:
        path = os.path.join(base, "assets", "fonts", name)
        if os.path.exists(path):
            QFontDatabase.addApplicationFont(path)
    return FONT_FAMILY in QFontDatabase.families()


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
    edge = f"2px solid {accent}" if outline else "none"
    fs = lambda px: max(8, round(px * k))          # шрифты масштабируются вместе с окном чата
    hov = f"border:1px solid {accent};" if glow else ""       # подсветка при наведении — по настройке «Подсветка кнопок»
    r = lambda px: max(8, round(20 * k))
    if dark:
        return FONT_QSS + f"""
            #card{{background:rgba(30,28,34,246);border-radius:{r(18)}px;border:{edge};}}
            QTextBrowser{{background:transparent;border:none;color:#efe9df;font-size:{fs(13)}px;}}
            QLineEdit{{background:#2a2830;border:1px solid #47444f;border-radius:12px;padding:7px 10px;color:#efe9df;
                       selection-background-color:{accent};selection-color:#201a14;}}
            QPushButton{{background:#3a3641;border:1px solid #514d5a;border-radius:12px;padding:5px 6px;
                         color:#efe9df;font-size:{fs(12)}px;}}
            QPushButton:hover{{background:#4a4553;{hov}}}
            QPushButton:checked{{background:{accent};color:#201a14;}}
            QLabel#status{{color:#a9a3b3;font-size:{fs(11)}px;padding-left:4px;}}
            QScrollBar:vertical{{background:transparent;width:8px;}}
            QScrollBar::handle:vertical{{background:#55515e;border-radius:8px;min-height:24px;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}"""
    return FONT_QSS + f"""
        #card{{background:rgba(255,252,245,246);border-radius:{r(18)}px;border:{edge};}}
        QTextBrowser{{background:transparent;border:none;color:#2b2118;font-size:{fs(13)}px;}}
        QLineEdit{{background:white;border:1px solid #e3d9c6;border-radius:12px;padding:7px 10px;color:#2b2118;}}
        QPushButton{{background:#fff3d1;border:1px solid #f0dca0;border-radius:12px;padding:5px 6px;
                     color:#2b2118;font-size:{fs(12)}px;}}
        QPushButton:hover{{background:#ffe9a8;{hov}}}
        QPushButton:checked{{background:{accent};}}
        QLabel#status{{color:#8a7d6a;font-size:{fs(11)}px;padding-left:4px;}}"""


LINK_LIGHT = "a{color:#1a62c9;}"
LINK_DARK = "a{color:#8ab4ff;}"


def app_qss(dark):
    """Стиль диалогов/меню приложения (QWidget не трогаем — иначе испортим прозрачные окна Mico AI)."""
    if not dark:
        return FONT_QSS
    return FONT_QSS + """
        QDialog, QMessageBox, QColorDialog {background:#26242b;color:#efe9df;}
        QDialog QLabel, QMessageBox QLabel, QCheckBox, QRadioButton {color:#efe9df;background:transparent;}
        QTabWidget::pane {border:1px solid #47444f;border-radius:8px;top:-1px;}
        QTabBar::tab {background:#2f2d36;color:#cfc8d8;padding:6px 12px;border:1px solid #47444f;
                      border-bottom:none;border-top-left-radius:6px;border-top-right-radius:6px;}
        QTabBar::tab:selected {background:#3d3946;color:#fff;}
        QLineEdit, QComboBox, QSpinBox, QAbstractSpinBox {background:#2a2830;color:#efe9df;border:1px solid #47444f;
                      border-radius:8px;padding:3px 6px;selection-background-color:#6b5b8a;}
        QComboBox QAbstractItemView {background:#2a2830;color:#efe9df;selection-background-color:#4a4553;}
        QPushButton {background:#3a3641;color:#efe9df;border:1px solid #514d5a;border-radius:8px;padding:5px 12px;}
        QPushButton:hover {background:#4a4553;}
        QPushButton:disabled {color:#7d7887;}
        QSlider::groove:horizontal {height:4px;background:#47444f;border-radius:8px;}
        QSlider::handle:horizontal {background:#d8cfe6;width:14px;margin:-6px 0;border-radius:7px;}
        QCheckBox::indicator {width:15px;height:15px;border:1px solid #6a657a;border-radius:8px;background:#2a2830;}
        QCheckBox::indicator:checked {background:#a893d6;}
        QMenu {background:#2a2830;color:#efe9df;border:1px solid #47444f;padding:4px;}
        QMenu::item {padding:6px 22px;border-radius:8px;}
        QMenu::item:selected {background:#4a4553;}
        QMenu::separator {height:1px;background:#47444f;margin:4px 8px;}
        QToolTip {background:#2a2830;color:#efe9df;border:1px solid #47444f;}
    """


def settings_qss(accent, dark):
    """Оформление окна настроек: плоские карточки, скруглённые поля, акцентный цвет Mico."""
    bg, card, border, text, field, muted = (
        ("#1c1a20", "#26232b", "#3a3640", "#efe9df", "#2f2b35", "#a9a3b3") if dark else
        ("#f6f4f1", "#ffffff", "#e8e2d9", "#2b2118", "#ffffff", "#8a7d6a"))
    return FONT_QSS + f"""
        QDialog {{ background:{bg}; color:{text}; font-size:13px; }}
        QTabWidget::pane {{ border:none; }}
        QScrollArea {{ background:transparent; border:none; }}
        QScrollArea > QWidget > QWidget {{ background:transparent; }}
        QTabBar::tab {{ background:transparent; color:{muted}; padding:6px 10px; margin-right:2px;
                        border-radius:10px; font-weight:500; }}
        QTabBar::tab:selected {{ background:{accent}; color:#201a14; }}
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
        QLabel#tileTitle {{ color:{text}; font-size:15px; font-weight:600; background:transparent; }}
        QPushButton {{ background:{field}; border:1px solid {border}; border-radius:12px; padding:9px 18px;
                       min-height:22px; color:{text}; font-size:13px; }}
        QPushButton:hover {{ border-color:{accent}; }}
        QPushButton:pressed {{ background:{accent}; color:#201a14; }}
        QPushButton#primary {{ background:{accent}; border-color:{accent}; color:#201a14; font-weight:600; }}
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
    QPushButton#resetRow { background:#f3c9c4; color:#000000; border:1px solid #e3a9a2;
                           border-radius:10px; padding:2px 8px; font-size:11px; }
    QPushButton#resetRow:hover { background:#eeb6af; }
    QLabel#hint { color:#8f8f8f; font-size:11px; }
    QLabel#readout { color:#8f8f8f; font-size:12px; }
"""


def app_font(size=10):
    """Шрифт для QApplication.setFont: все виджеты берут его, если не заданы свои."""
    from PyQt6.QtGui import QFont
    f = QFont(FONT_FAMILY, size)
    f.setFamilies([FONT_FAMILY, "Segoe UI Variable Display", "Segoe UI Variable", "Segoe UI", "Arial"])     # запасные — только если основной шрифт не нашёлся
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
    if dark:
        bg, tile, tile_hi, field, text, muted, border = "#171717", "#222222", "#2a2a2a", "#2b2b2b", "#ececec", "#8a8a8a", "#2f2f2f"
    else:
        bg, tile, tile_hi, field, text, muted, border = "#f4f4f5", "#ffffff", "#ededf0", "#f0f0f2", "#1c1c1e", "#6b6b72", "#e3e3e8"
    arrow = chevron_url(muted)
    return FONT_QSS + f"""
        QDialog {{ background:{bg}; color:{text}; font-size:13px; }}
        QTabWidget::pane {{ border:none; }}
        QScrollArea {{ background:transparent; border:none; }}
        QScrollArea > QWidget > QWidget {{ background:transparent; }}
        QScrollBar:vertical {{ background:transparent; width:8px; margin:4px 0; }}
        QScrollBar::handle:vertical {{ background:{border}; border-radius:4px; min-height:36px; }}
        QScrollBar::handle:vertical:hover {{ background:{muted}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; background:none; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:none; }}
        QListWidget#sideNav {{ background:{bg}; border:none; outline:0; padding:6px 0; }}
        QListWidget#sideNav::item {{ color:{muted}; padding:10px 14px; margin:2px 10px;
                                    border-radius:8px; font-weight:500; }}
        QListWidget#sideNav::item:hover:!selected {{ color:{text}; background:{tile}; }}
        QListWidget#sideNav::item:selected {{ background:{tile_hi}; color:{text}; font-weight:600; }}
        QListWidget#sideNav::item:disabled {{ color:{border}; }}
        QLabel#pageTitle {{ color:{text}; font-size:22px; font-weight:700; background:transparent;
                            padding:0 2px 4px 2px; }}
        QGroupBox {{ background:{tile}; border:none; border-radius:12px; margin-top:20px;
                     padding:12px 14px 10px 14px; font-weight:500; }}
        QFrame#expander {{ background:transparent; border:none; }}
        QLabel#expTitle {{ color:{text}; font-size:13px; font-weight:500; background:transparent; }}
        QGroupBox::title {{ subcontrol-origin:margin; left:16px; top:-2px; color:{muted};
                            font-size:11px; font-weight:600; }}
        QLabel {{ color:{text}; background:transparent; }}
        QLabel#hint {{ color:{muted}; font-size:11px; }}
        QLabel#readout {{ color:{muted}; font-size:12px; }}
        QFrame#wiHead {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                         stop:0 rgba({r},{g},{b},0.40), stop:1 {tile}); border-radius:12px; }}
        QLabel#wiTitle {{ font-size:22px; font-weight:700; background:transparent; }}
        QLabel#wiSub {{ color:{muted}; font-size:12px; background:transparent; }}
        QLineEdit, QComboBox, QSpinBox, QTimeEdit, QListWidget {{ background:{field}; border:none;
                     border-radius:8px; padding:7px 12px; color:{text}; selection-background-color:{accent}; }}
        QLineEdit#search {{ border-radius:8px; padding:8px 12px; }}
        QComboBox {{ padding-right:30px; }}
        QComboBox::drop-down {{ subcontrol-origin:padding; subcontrol-position:center right; border:none; width:30px; }}
        QComboBox::down-arrow {{ image:url("{arrow}"); width:12px; height:12px; }}
        QComboBox QAbstractItemView {{ background:{tile}; border:1px solid {border}; border-radius:8px;
                     padding:4px; selection-background-color:{accent}; selection-color:#1c1c1e; outline:0; }}
        QCheckBox {{ spacing:12px; color:{text}; }}
        QCheckBox::indicator {{ width:38px; height:22px; border-radius:11px; background:{border}; border:none; }}
        QCheckBox::indicator:checked {{ background:{accent}; }}
        QSlider::groove:horizontal {{ height:4px; background:{border}; border-radius:2px; }}
        QSlider::sub-page:horizontal {{ background:{accent}; border-radius:2px; }}
        QSlider::handle:horizontal {{ background:#ffffff; width:16px; height:16px; margin:-6px 0;
                                      border-radius:8px; border:none; }}
        QPushButton {{ background:{field}; color:{text}; border:none; border-radius:8px; padding:8px 14px; }}
        QPushButton:hover {{ background:{tile_hi}; }}
        QPushButton#primary {{ background:{accent}; color:#1c1c1e; font-weight:600; }}
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

