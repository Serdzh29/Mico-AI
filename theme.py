"""Светлая/тёмная тема Mico: ручной выбор или как в Windows. Единый шрифт — Inter (см. load_fonts)."""
import os, sys

# Единый шрифт во всём Mico: чат, пузырь, кнопки, настройки. Inter — открытый шрифт (лицензия OFL),
# по духу ближе всего к шрифту Apple из презентаций, и одинаково выглядит на любой версии Windows.
FONT_FAMILY = "Inter"
FONT_FILES = ["Inter-Regular.otf", "Inter-Medium.otf", "Inter-SemiBold.otf", "Inter-Bold.otf"]
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


def panel_qss(accent, dark, outline=True, k=1.0):
    edge = f"2px solid {accent}" if outline else "none"
    fs = lambda px: max(8, round(px * k))          # шрифты масштабируются вместе с окном чата
    r = lambda px: max(8, round(18 * k))
    if dark:
        return FONT_QSS + f"""
            #card{{background:rgba(30,28,34,246);border-radius:{r(18)}px;border:{edge};}}
            QTextBrowser{{background:transparent;border:none;color:#efe9df;font-size:{fs(13)}px;}}
            QLineEdit{{background:#2a2830;border:1px solid #47444f;border-radius:12px;padding:7px 10px;color:#efe9df;
                       selection-background-color:{accent};selection-color:#201a14;}}
            QPushButton{{background:#3a3641;border:1px solid #514d5a;border-radius:11px;padding:5px 6px;
                         color:#efe9df;font-size:{fs(12)}px;}}
            QPushButton:hover{{background:#4a4553;}}
            QPushButton:checked{{background:{accent};color:#201a14;}}
            QLabel#status{{color:#a9a3b3;font-size:{fs(11)}px;padding-left:4px;}}
            QScrollBar:vertical{{background:transparent;width:8px;}}
            QScrollBar::handle:vertical{{background:#55515e;border-radius:4px;min-height:24px;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}"""
    return FONT_QSS + f"""
        #card{{background:rgba(255,252,245,246);border-radius:{r(18)}px;border:{edge};}}
        QTextBrowser{{background:transparent;border:none;color:#2b2118;font-size:{fs(13)}px;}}
        QLineEdit{{background:white;border:1px solid #e3d9c6;border-radius:12px;padding:7px 10px;color:#2b2118;}}
        QPushButton{{background:#fff3d1;border:1px solid #f0dca0;border-radius:11px;padding:5px 6px;
                     color:#2b2118;font-size:{fs(12)}px;}}
        QPushButton:hover{{background:#ffe9a8;}}
        QPushButton:checked{{background:{accent};}}
        QLabel#status{{color:#8a7d6a;font-size:{fs(11)}px;padding-left:4px;}}"""


LINK_LIGHT = "a{color:#1a62c9;}"
LINK_DARK = "a{color:#8ab4ff;}"


def app_qss(dark):
    """Стиль диалогов/меню приложения (QWidget не трогаем — иначе испортим прозрачные окна Mico)."""
    if not dark:
        return FONT_QSS
    return FONT_QSS + """
        QDialog, QMessageBox, QColorDialog {background:#26242b;color:#efe9df;}
        QDialog QLabel, QMessageBox QLabel, QCheckBox, QRadioButton {color:#efe9df;background:transparent;}
        QTabWidget::pane {border:1px solid #47444f;border-radius:6px;top:-1px;}
        QTabBar::tab {background:#2f2d36;color:#cfc8d8;padding:6px 12px;border:1px solid #47444f;
                      border-bottom:none;border-top-left-radius:6px;border-top-right-radius:6px;}
        QTabBar::tab:selected {background:#3d3946;color:#fff;}
        QLineEdit, QComboBox, QSpinBox, QAbstractSpinBox {background:#2a2830;color:#efe9df;border:1px solid #47444f;
                      border-radius:6px;padding:3px 6px;selection-background-color:#6b5b8a;}
        QComboBox QAbstractItemView {background:#2a2830;color:#efe9df;selection-background-color:#4a4553;}
        QPushButton {background:#3a3641;color:#efe9df;border:1px solid #514d5a;border-radius:6px;padding:5px 12px;}
        QPushButton:hover {background:#4a4553;}
        QPushButton:disabled {color:#7d7887;}
        QSlider::groove:horizontal {height:4px;background:#47444f;border-radius:2px;}
        QSlider::handle:horizontal {background:#d8cfe6;width:14px;margin:-6px 0;border-radius:7px;}
        QCheckBox::indicator {width:15px;height:15px;border:1px solid #6a657a;border-radius:3px;background:#2a2830;}
        QCheckBox::indicator:checked {background:#a893d6;}
        QMenu {background:#2a2830;color:#efe9df;border:1px solid #47444f;padding:4px;}
        QMenu::item {padding:6px 22px;border-radius:5px;}
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
        QTabBar::tab {{ background:transparent; color:{muted}; padding:6px 12px; margin-right:2px;
                        border-radius:9px; font-weight:500; }}
        QTabBar::tab:selected {{ background:{accent}; color:#201a14; }}
        QTabBar::tab:hover:!selected {{ color:{text}; }}
        QGroupBox {{ background:{card}; border:1px solid {border}; border-radius:12px;
                     margin-top:14px; padding:10px 12px 8px 12px; font-weight:600; }}
        QGroupBox::title {{ subcontrol-origin:margin; left:12px; top:2px; padding:0 4px; color:{text}; }}
        QLabel {{ color:{text}; }}
        QLineEdit, QComboBox, QSpinBox, QListWidget {{ background:{field}; border:1px solid {border};
                     border-radius:8px; padding:4px 8px; color:{text}; }}
        QListWidget::item {{ padding:4px 2px; }}
        QToolButton {{ background:{field}; border:1px solid {border}; border-radius:12px; color:{text};
                       font-weight:600; }}
        QToolButton:hover {{ border-color:{accent}; }}
        QPushButton {{ background:{field}; border:1px solid {border}; border-radius:9px; padding:5px 12px;
                       color:{text}; }}
        QPushButton:hover {{ border-color:{accent}; }}
        QPushButton:pressed {{ background:{accent}; color:#201a14; }}
        QPushButton#primary {{ background:{accent}; border-color:{accent}; color:#201a14; font-weight:600; }}
        QPushButton#primary:hover {{ background:{accent}; border-color:{text}; }}
        QPushButton#flat {{ background:transparent; border:none; color:{muted}; padding:2px 4px; }}
        QPushButton#flat:hover {{ color:{text}; }}
        QCheckBox {{ spacing:9px; color:{text}; }}
        QCheckBox::indicator {{ width:16px; height:16px; border-radius:5px; border:1px solid {border};
                                background:{field}; }}
        QCheckBox::indicator:checked {{ background:{accent}; border-color:{accent}; }}
        QSlider {{ background:transparent; border:none; min-height:22px; }}
        QSlider::groove:horizontal {{ height:6px; background:{border}; border-radius:3px; }}
        QSlider::handle:horizontal {{ background:{accent}; width:16px; height:16px; margin:-5px 0; border-radius:8px; }}
        QProgressBar {{ background:{field}; border:none; border-radius:6px; height:10px; text-align:center; }}
        QProgressBar::chunk {{ background:{accent}; border-radius:6px; }}
    """


# Стили для окна настроек: кнопка «Сбросить» у каждой настройки и серые подсказки.
RESET_QSS = """
    QPushButton#resetRow { background:#f3c9c4; color:#000000; border:1px solid #e3a9a2;
                           border-radius:8px; padding:2px 8px; font-size:11px; }
    QPushButton#resetRow:hover { background:#eeb6af; }
    QLabel#hint { color:#8f8f8f; font-size:11px; }
    QLabel#readout { color:#8f8f8f; font-size:12px; }
"""


def app_font(size=10):
    """Шрифт для QApplication.setFont: все виджеты берут его, если не заданы свои."""
    from PyQt6.QtGui import QFont
    f = QFont(FONT_FAMILY, size)
    f.setFamilies([FONT_FAMILY, "Segoe UI", "Arial"])     # запасные — только если Inter не нашёлся
    return f



def wi_settings_qss(accent, dark):
    """Настройки в режиме Windows Intelligence: спокойный вид в духе macOS — карточки без рамок, скруглённые поля,
    вкладки-таблетки, переключатели-пилюли и шапка с цветом Mico. Обычные настройки этим не меняются."""
    from intel import hex_rgb
    r, g, b = hex_rgb(accent)
    if dark:
        bg, card, border, text, muted, field = "#1c1c1e", "#2c2c2e", "#3a3a3c", "#f5f5f7", "#98989d", "#3a3a3c"
    else:
        bg, card, border, text, muted, field = "#f5f5f7", "#ffffff", "#e5e5ea", "#1d1d1f", "#6e6e73", "#f2f2f4"
    return FONT_QSS + f"""
        QDialog {{ background:{bg}; color:{text}; font-size:13px; }}
        QTabWidget::pane {{ border:none; }}
        QTabBar::tab {{ background:transparent; color:{muted}; padding:6px 14px; margin:0 3px; border-radius:10px;
                        font-weight:500; }}
        QTabBar::tab:selected {{ background:{card}; color:{text}; }}
        QTabBar::tab:hover:!selected {{ color:{text}; }}
        QScrollArea {{ background:transparent; border:none; }}
        QScrollArea > QWidget > QWidget {{ background:transparent; }}
        QGroupBox {{ background:{card}; border:none; border-radius:14px; margin-top:18px;
                     padding:14px 16px 12px 16px; font-weight:600; }}
        QGroupBox::title {{ subcontrol-origin:margin; left:16px; top:-4px; color:{muted};
                            font-size:11px; font-weight:600; }}
        QLabel {{ color:{text}; }}
        QLabel#hint {{ color:{muted}; font-size:11px; }}
        QLabel#readout {{ color:{muted}; font-size:12px; }}
        QFrame#wiHead {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                         stop:0 rgba({r},{g},{b},0.45), stop:1 {card}); border-radius:16px; }}
        QLabel#wiTitle {{ font-size:22px; font-weight:700; background:transparent; }}
        QLabel#wiSub {{ color:{muted}; font-size:12px; background:transparent; }}
        QLineEdit, QComboBox, QSpinBox, QTimeEdit, QListWidget {{ background:{field}; border:none;
                     border-radius:9px; padding:6px 10px; color:{text}; }}
        QComboBox::drop-down {{ border:none; width:22px; }}
        QCheckBox {{ spacing:12px; color:{text}; }}
        QCheckBox::indicator {{ width:40px; height:24px; border-radius:12px; background:{border}; border:none; }}
        QCheckBox::indicator:checked {{ background:{accent}; }}
        QSlider::groove:horizontal {{ height:4px; background:{border}; border-radius:2px; }}
        QSlider::sub-page:horizontal {{ background:{accent}; border-radius:2px; }}
        QSlider::handle:horizontal {{ background:#ffffff; width:20px; height:20px; margin:-8px 0;
                                      border-radius:10px; border:1px solid {border}; }}
        QPushButton {{ background:{field}; color:{text}; border:none; border-radius:10px; padding:7px 14px; }}
        QPushButton:hover {{ background:{border}; }}
        QPushButton#primary {{ background:{accent}; color:#1d1d1f; font-weight:600; }}
        QPushButton#flat {{ background:transparent; color:{muted}; }}
    """
