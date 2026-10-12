"""Светлая/тёмная тема Mico: ручной выбор или как в Windows."""


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
        return f"""
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
    return f"""
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
        return ""
    return """
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
    return f"""
        QDialog {{ background:{bg}; color:{text}; font-size:13px; }}
        QTabWidget::pane {{ border:none; }}
        QScrollArea {{ background:transparent; border:none; }}
        QScrollArea > QWidget > QWidget {{ background:transparent; }}
        QTabBar::tab {{ background:transparent; color:{muted}; padding:7px 14px; margin-right:4px;
                        border-radius:9px; font-weight:500; }}
        QTabBar::tab:selected {{ background:{accent}; color:#201a14; }}
        QTabBar::tab:hover:!selected {{ color:{text}; }}
        QGroupBox {{ background:{card}; border:1px solid {border}; border-radius:14px;
                     margin-top:18px; padding:14px 14px 10px 14px; font-weight:600; }}
        QGroupBox::title {{ subcontrol-origin:margin; left:14px; top:4px; padding:0 4px; color:{text}; }}
        QLabel {{ color:{text}; }}
        QLineEdit, QComboBox, QSpinBox, QListWidget {{ background:{field}; border:1px solid {border};
                     border-radius:9px; padding:6px 9px; color:{text}; }}
        QListWidget::item {{ padding:4px 2px; }}
        QToolButton {{ background:{field}; border:1px solid {border}; border-radius:12px; color:{text};
                       font-weight:600; }}
        QToolButton:hover {{ border-color:{accent}; }}
        QPushButton {{ background:{field}; border:1px solid {border}; border-radius:10px; padding:7px 14px;
                       color:{text}; }}
        QPushButton:hover {{ border-color:{accent}; }}
        QPushButton:pressed {{ background:{accent}; color:#201a14; }}
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
