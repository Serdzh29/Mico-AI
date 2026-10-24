"""Вкладка «Голос» в настройках: голос, скорость, выразительность, паузы, громкость, микрофон, слово «мико», проверки.
Значения сохраняются в общий cfg при «Сохранить»; голосовой модуль читает их на каждой фразе."""
import os

from PyQt6.QtCore import Qt
from switch_ui import RoundSlider, WrapCheck   # переключатели и круглые ползунки — как в настройках
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QSlider, QVBoxLayout, QWidget)

import i18n
import voice_ctl
import voice_models
import settings_look                       # карточки и цвет — как во всём окне настроек
import theme

VOICE_DEFAULTS = {
    "voice_on": False, "voice_name": voice_models.DEFAULT_VOICE, "voice_mood": True,
    "voice_speed": 1.0, "voice_expr": 60, "voice_pause": 1.0, "voice_volume": 100,
    "voice_wake": False, "voice_wake_words": "мико, mico", "voice_wake_sens": 1.0,
    "voice_end_ms": 1000, "voice_mic": "", "hotkey_voice": "ctrl+alt+v",
}


def _slider(lo, hi, value):
    s = RoundSlider(Qt.Orientation.Horizontal)
    s.setRange(lo, hi)
    s.setValue(int(value))
    return s


class VoicePage:
    """Три подраздела: голос и речь, микрофон и «мико», проверка. Создаётся один раз на окно настроек."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.voice = voice_ctl.shared(cfg)
        self.w = {}
        self._build()
        self.load(cfg)
        self.voice.test_result.connect(self._test_text.setText)

    # ----- построение -----
    def _build(self):
        self.page_voice = self._section_voice()
        self.page_mic = self._section_mic()
        self.page_test = self._section_test()
        accent = settings_look.ink(self.cfg["color"], theme.is_dark(self.cfg))
        self.widget = settings_look.CardPage([
            (self.page_voice, i18n.t("Голос и речь"), i18n.t("Какой голос, как быстро и с каким настроением"), "speaker"),
            (self.page_mic, i18n.t("Микрофон и «мико»"), i18n.t("Слово пробуждения, чувствительность, устройство"), "mic"),
            (self.page_test, i18n.t("Проверка и сброс"), i18n.t("Послушать голос, проверить микрофон, вернуть по умолчанию"), "bolt"),
        ], accent)

    def pages(self):
        return self.widget

    def _section_voice(self):
        w = QWidget()
        f = QFormLayout(w)
        self.w["voice_on"] = WrapCheck(i18n.t("Озвучивать ответы Mico"))
        f.addRow(self.w["voice_on"])
        self.w["voice_name"] = QComboBox()
        for key, title in voice_models.VOICE_TITLES.items():
            self.w["voice_name"].addItem(title, key)
        self._voice_state = QLabel("")
        self._voice_state.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(self.w["voice_name"], 1)
        row.addWidget(self._voice_state)
        f.addRow(i18n.t("Голос"), row)
        self.w["voice_name"].currentIndexChanged.connect(lambda _i: self._update_state())
        self.w["voice_mood"] = WrapCheck(i18n.t("Голос меняется с настроением (радость — живее, грусть — медленнее)"))
        f.addRow(self.w["voice_mood"])
        self.w["voice_speed"] = self._slider_row(f, i18n.t("Скорость речи"), 50, 200, "{}%", 100)
        self.w["voice_expr"] = self._slider_row(f, i18n.t("Выразительность"), 0, 100, "{}%", 60)
        self.w["voice_pause"] = self._slider_row(f, i18n.t("Паузы между фразами"), 0, 200, "{}%", 100)
        self.w["voice_volume"] = self._slider_row(f, i18n.t("Громкость"), 0, 150, "{}%", 100)
        return w

    def _section_mic(self):
        w = QWidget()
        f = QFormLayout(w)
        self.w["voice_wake"] = WrapCheck(i18n.t("Голосовой чат по слову «мико!»"))
        self.w["voice_wake"].setToolTip(i18n.t("Скажи «мико!» или «mico!» — сразу откроется голосовой чат. "
                                               "Микрофон слушает всё время, звук не сохраняется, распознавание на этом ПК. "
                                               "Выключено по умолчанию."))
        f.addRow(self.w["voice_wake"])
        self.w["voice_wake_sens"] = self._slider_row(f, i18n.t("Чувствительность микрофона"), 50, 200, "{}%", 100)
        self.w["voice_end_ms"] = self._slider_row(f, i18n.t("Пауза, после которой вопрос отправляется"), 400, 3000, "{} мс", 1000)
        self.w["voice_mic"] = QComboBox()
        self.w["voice_mic"].setToolTip(i18n.t("Микрофон, с которого Mico слушает. «По умолчанию» — как в Windows."))
        row = QHBoxLayout()
        row.addWidget(self.w["voice_mic"], 1)
        refresh = QPushButton(i18n.t("Обновить список"))
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.clicked.connect(self._fill_mics)
        row.addWidget(refresh)
        f.addRow(i18n.t("Микрофон"), row)
        hint = QLabel(i18n.t("Горячая клавиша голоса: Ctrl+Alt+V — нажми, скажи, нажми ещё раз. Или нажми значок микрофона в чате."))
        hint.setWordWrap(True)
        f.addRow(hint)
        return w

    def _section_test(self):
        w = QWidget()
        v = QVBoxLayout(w)
        row = QHBoxLayout()
        b_voice = QPushButton(i18n.t("Послушать голос"))
        b_voice.setCursor(Qt.CursorShape.PointingHandCursor)
        b_voice.clicked.connect(self._test_voice)
        b_mic = QPushButton(i18n.t("Проверить микрофон (3 с)"))
        b_mic.setCursor(Qt.CursorShape.PointingHandCursor)
        b_mic.clicked.connect(self._test_mic)
        row.addWidget(b_voice)
        row.addWidget(b_mic)
        row.addStretch(1)
        v.addLayout(row)
        self._test_text = QLabel("")
        self._test_text.setWordWrap(True)
        v.addWidget(self._test_text)
        reset = QPushButton(i18n.t("Вернуть настройки голоса по умолчанию"))
        reset.setCursor(Qt.CursorShape.PointingHandCursor)
        reset.clicked.connect(self._reset)
        v.addWidget(reset, 0, Qt.AlignmentFlag.AlignLeft)
        v.addStretch(1)
        return w

    def _slider_row(self, form, label, lo, hi, fmt, value):
        """Ползунок с подписью значения. Возвращает сам ползунок; значение храним как целое (проценты, мс)."""
        s = _slider(lo, hi, value)
        val = QLabel()
        val.setMinimumWidth(64)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def show(v):
            val.setText(fmt.format(v))
        s.valueChanged.connect(show)
        show(value)
        row = QHBoxLayout()
        row.addWidget(s, 1)
        row.addWidget(val)
        form.addRow(label, row)
        return s

    # ----- загрузка и сохранение -----
    def load(self, cfg):
        def g(k):
            return cfg.get(k, VOICE_DEFAULTS[k])
        self.w["voice_on"].setChecked(bool(g("voice_on")))
        idx = self.w["voice_name"].findData(g("voice_name"))
        self.w["voice_name"].setCurrentIndex(max(0, idx))
        self.w["voice_mood"].setChecked(bool(g("voice_mood")))
        self.w["voice_speed"].setValue(int(round(float(g("voice_speed")) * 100)))
        self.w["voice_expr"].setValue(int(g("voice_expr")))
        self.w["voice_pause"].setValue(int(round(float(g("voice_pause")) * 100)))
        self.w["voice_volume"].setValue(int(g("voice_volume")))
        self.w["voice_wake"].setChecked(bool(g("voice_wake")))
        self.w["voice_wake_sens"].setValue(int(round(float(g("voice_wake_sens")) * 100)))
        self.w["voice_end_ms"].setValue(int(g("voice_end_ms")))
        self._fill_mics(selected=g("voice_mic"))
        self._update_state()

    def _fill_mics(self, selected=None):
        """Список входных устройств из PortAudio. Без sounddevice просто остаётся «По умолчанию»."""
        cur = selected if selected is not None else self.w["voice_mic"].currentData()
        combo = self.w["voice_mic"]
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(i18n.t("По умолчанию"), "")
        for name, num in voice_ctl.mic_list():         # список собран в фоне при старте: окно не ждёт драйвер звука
            combo.addItem(name, num)
        idx = combo.findData(str(cur) if cur not in (None, "") else "")
        combo.setCurrentIndex(max(0, idx))
        combo.blockSignals(False)

    def _update_state(self):
        name = self.w["voice_name"].currentData() or voice_models.DEFAULT_VOICE
        ok = os.path.isfile(voice_models.paths(name)[0])
        self._voice_state.setText(i18n.t("Установлен") if ok else i18n.t("Скачается при включении"))

    def apply(self, cfg):
        """Переносит значения вкладки в cfg и включает/выключает голос и «мико» через контроллер."""
        was_on, was_wake, was_voice = bool(cfg.get("voice_on")), bool(cfg.get("voice_wake")), cfg.get("voice_name")
        cfg.update(
            voice_mood=self.w["voice_mood"].isChecked(),
            voice_speed=self.w["voice_speed"].value() / 100.0,
            voice_expr=self.w["voice_expr"].value(),
            voice_pause=self.w["voice_pause"].value() / 100.0,
            voice_volume=self.w["voice_volume"].value(),
            voice_wake_words=VOICE_DEFAULTS["voice_wake_words"],
            voice_wake_sens=self.w["voice_wake_sens"].value() / 100.0,
            voice_end_ms=self.w["voice_end_ms"].value(),
            voice_mic=self.w["voice_mic"].currentData() or "",
        )
        new_voice = self.w["voice_name"].currentData() or voice_models.DEFAULT_VOICE
        now_on = self.w["voice_on"].isChecked()
        now_wake = self.w["voice_wake"].isChecked()
        if new_voice != was_voice:
            self.voice.set_voice(new_voice)           # сам докачает голос, если его нет
        if now_on != was_on:
            self.voice.set_enabled(now_on)
        else:
            cfg["voice_on"] = now_on
        if now_wake != was_wake:
            self.voice.set_wake(now_wake)
        else:
            cfg["voice_wake"] = now_wake
        cfg["voice_name"] = new_voice

    def _reset(self):
        self.load(dict(VOICE_DEFAULTS))

    def _test_voice(self):
        self.voice.test_voice()

    def _test_mic(self):
        self.voice.test_mic(3.0)
