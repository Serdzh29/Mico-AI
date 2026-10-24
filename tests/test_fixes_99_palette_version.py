"""Регрессия: полоска загрузки доходит до конца вместе с проектором, версия без M, кружки палитры, паузы речи."""
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import model_store as S  # noqa: E402
import version  # noqa: E402
import voice_text  # noqa: E402


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


class FakeResp:
    def __init__(self, body):
        self.status_code = 200
        self._body = body
        self.headers = {"Content-Length": str(len(body))}

    def iter_content(self, chunk_size=1):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class DownloadProgressTest(unittest.TestCase):
    def test_progress_covers_projector_and_reaches_the_end(self):
        """Раньше проектор качался без полоски и она вставала на 99%."""
        root = tempfile.mkdtemp()

        def fake_get(url, headers=None, stream=None, timeout=None):
            return FakeResp(b"p" * 100_000) if url.endswith("mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf") \
                else FakeResp(b"m" * 300_000)

        calls = []
        with mock.patch.object(S.requests, "get", side_effect=fake_get):
            ok = S.download("qwen2.5-vl-3b", progress=lambda d, t: calls.append((d, t)), root=root)
        self.assertTrue(ok)
        self.assertEqual(calls[-1][0], calls[-1][1])            # в конце всё скачано
        dones = [d for d, _ in calls]
        self.assertEqual(dones, sorted(dones))                  # полоска не откатывается назад
        self.assertIn(400_000, dones)                           # учитываются оба файла: 300 000 + 100 000

    def test_already_downloaded_file_still_reports_progress(self):
        root = tempfile.mkdtemp()
        with open(S.path_for("qwen3.5-4b", root), "wb") as f:
            f.write(b"x" * 500)
        calls = []
        self.assertTrue(S.download("qwen3.5-4b", progress=lambda d, t: calls.append((d, t)), root=root))
        self.assertEqual(calls[-1], (500, 500))

    def test_installer_has_a_progress_step_for_the_projector(self):
        ins = read("installer.py")
        self.assertIn("make_show(92, 99, vision[\"title\"])", ins)
        self.assertNotIn("_download_model(vision, None", ins)


class VersionTest(unittest.TestCase):
    def test_version_is_shown_without_m(self):
        self.assertEqual(version.display_version("stable"), "26.10.24")
        self.assertEqual(version.APP_VERSION, "M26.10.24")       # внутри сравнение версий не меняется


class PaletteTest(unittest.TestCase):
    def test_swatches_are_round_by_style_not_by_mask(self):
        for name in ("aichat.py", "voice_dock.py"):
            src = read(name)
            self.assertNotIn("round_mask(b,", src, name)
            self.assertIn("setFixedSize(", src, name)


class SpeechPauseTest(unittest.TestCase):
    def test_comma_gets_short_breath_pause(self):
        self.assertEqual(voice_text.pause_after("Да,"), 0.2)
        self.assertGreater(voice_text.pause_after("Да,"), voice_text.pause_after("Да"))
        self.assertLess(voice_text.pause_after("Да,"), voice_text.pause_after("Да."))


class SleepFpsTest(unittest.TestCase):
    def test_sleep_default_is_economical(self):
        main = read("main.py")
        self.assertIn('"anim_sleep_fps": 20,', main)


if __name__ == "__main__":
    unittest.main()
