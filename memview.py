"""Что Mico AI знает о тебе: заметки, недавние команды, история разговора, программы и окна, буфер обмена.
Всё хранится в зашифрованной базе на этом компьютере. Здесь можно посмотреть записи, удалить выбранные
или очистить целый раздел. Заголовки окон показываются полностью."""
import time
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QComboBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget

SECTIONS = [
    ("notes", "Заметки"),
    ("actions", "Недавние команды"),
    ("chat", "История разговора"),
    ("events", "Программы и окна"),
    ("clips", "Буфер обмена"),
]
LIMIT = 300
_store = None


def bind(store):
    """Подключает зашифрованное хранилище (вызывается при запуске, как reminders.bind)."""
    global _store
    _store = store


class MemoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.pick = QComboBox()
        for key, title in SECTIONS:
            self.pick.addItem(title, key)
        self.pick.currentIndexChanged.connect(self.reload)

        self.count = QLabel("")
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        row = QHBoxLayout()
        b_del = QPushButton("Удалить выбранное")
        b_del.clicked.connect(self._delete_selected)
        b_all = QPushButton("Очистить раздел")
        b_all.clicked.connect(self._wipe_section)
        b_ref = QPushButton("Обновить")
        b_ref.clicked.connect(self.reload)
        for b in (b_del, b_all, b_ref):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            row.addWidget(b)

        lay.addWidget(self.pick)
        lay.addWidget(self.count)
        lay.addWidget(self.list, 1)
        lay.addLayout(row)
        self.reload()

    def _table(self):
        return self.pick.currentData()

    def reload(self, *_):
        self.list.clear()
        if _store is None:
            self.count.setText("Хранилище ещё не подключено.")
            return
        rows = _store.list_rows(self._table(), LIMIT)
        for rid, ts, text in rows:
            item = QListWidgetItem(f"{time.strftime('%d.%m %H:%M', time.localtime(ts))}   {text}")
            item.setData(Qt.ItemDataRole.UserRole, rid)
            self.list.addItem(item)
        note = " (показаны последние)" if len(rows) >= LIMIT else ""
        self.count.setText(f"Записей: {len(rows)}{note}")

    def _delete_selected(self):
        if _store is None:
            return
        items = self.list.selectedItems()
        if not items:
            self.count.setText("Выбери записи в списке и нажми «Удалить выбранное».")
            return
        for it in items:
            _store.delete_row(self._table(), it.data(Qt.ItemDataRole.UserRole))
        self.reload()

    def _wipe_section(self):
        if _store is None:
            return
        name = self.pick.currentText()
        answer = QMessageBox.question(self, "Очистить раздел",
                                      f"Удалить всё в разделе «{name}»? Это нельзя отменить.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        _store.wipe_table(self._table())
        self.reload()
