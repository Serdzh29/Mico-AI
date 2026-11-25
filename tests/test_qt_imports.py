"""Каждое имя Qt импортируется из своего модуля: QtGui — рисование и шрифты, QtWidgets — виджеты, QtCore — таймеры.
Ошибка здесь падает только при запуске программы, поэтому проверяем заранее."""
import ast, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUI = {"QGuiApplication", "QFont", "QColor", "QPainter", "QPainterPath", "QPen", "QBrush", "QLinearGradient",
       "QRadialGradient", "QAction", "QIcon", "QImage", "QPalette", "QCursor", "QPixmap", "QFontDatabase",
       "QTextCharFormat", "QTextCursor", "QKeySequence", "QShortcut", "QRegion"}
WID = {"QWidget", "QLabel", "QPushButton", "QFrame", "QLineEdit", "QTextBrowser", "QDialog", "QVBoxLayout",
       "QHBoxLayout", "QGridLayout", "QFormLayout", "QApplication", "QMenu", "QMessageBox", "QScrollArea",
       "QToolButton", "QComboBox", "QCheckBox", "QSpinBox", "QSlider", "QTabWidget", "QSystemTrayIcon",
       "QColorDialog", "QInputDialog", "QFileDialog", "QListWidget", "QListWidgetItem", "QPlainTextEdit",
       "QSizePolicy", "QDialogButtonBox", "QGroupBox", "QAbstractSpinBox", "QStyle", "QGraphicsOpacityEffect"}

def test_qt_names_come_from_the_right_module():
    bad = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests")]
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            tree = ast.parse(open(p, encoding="utf-8").read())
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("PyQt6."):
                    mod = n.module.split(".")[1]
                    for a in n.names:
                        if (mod == "QtWidgets" and a.name in GUI) or (mod == "QtGui" and a.name in WID):
                            bad.append(f"{os.path.relpath(p, ROOT)}:{n.lineno} {a.name} из {n.module}")
    assert not bad, bad

if __name__ == "__main__":
    test_qt_names_come_from_the_right_module()
    print("OK test_qt_names_come_from_the_right_module")
