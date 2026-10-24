"""Каталог и хранение встроенных моделей: выбор по памяти, ссылки, докачка, удаление (без сети)."""
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import model_catalog as C
import model_store as S


class FakeResp:
    def __init__(self, status, body, headers=None):
        self.status_code = status
        self._body = body
        self.headers = headers or {"Content-Length": str(len(body))}

    def iter_content(self, chunk_size=1):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class CatalogTest(unittest.TestCase):
    def test_recommend_by_ram(self):
        self.assertEqual(C.recommend(4)["id"], "qwen2.5-3b")
        self.assertEqual(C.recommend(6)["id"], "qwen2.5-3b")
        self.assertEqual(C.recommend(8)["id"], "qwen2.5-3b-q5")
        # все компьютеры получают лёгкую Qwen2.5 3B: тяжёлые модели думают долго и грузят ЦП и память
        self.assertEqual(C.recommend(16)["id"], "qwen2.5-3b-q5")
        self.assertEqual(C.recommend(24)["id"], "qwen2.5-3b-q5")
        self.assertEqual(C.recommend(32)["id"], "qwen2.5-3b-q5")
        self.assertEqual(C.recommend(64)["id"], "qwen2.5-3b-q5")

    def test_windows_reports_slightly_less_memory(self):
        # 8 ГБ в Windows — это около 7,8 ГБ, и это всё равно восьмигигабайтная ступень
        self.assertEqual(C.recommend(7.8)["id"], "qwen2.5-3b-q5")
        self.assertEqual(C.recommend(31.7)["id"], "qwen2.5-3b-q5")
        self.assertEqual(C.recommend(63.6)["id"], "qwen2.5-3b-q5")
        self.assertIsNone(C.recommend_vision(4))
        self.assertEqual(C.recommend_vision(8)["id"], "qwen2.5-vl-3b")
        self.assertEqual(C.recommend(15.6)["id"], "qwen2.5-3b-q5")

    def test_heavy_model_is_not_recommended_but_still_known(self):
        # старая 9B-модель для 16 ГБ больше не предлагается, но уже скачанная должна находиться
        for gb in (6, 8, 16, 32, 64):
            self.assertTrue(C.by_id(C.recommend(gb)["id"]) is not None and not C.by_id(C.recommend(gb)["id"]).get("legacy"))
        self.assertIsNotNone(C.by_id("qwen3.5-9b"))

    def test_gemma_is_offered_but_never_auto_picked(self):
        g = C.by_id("gemma-3-4b-q4")
        self.assertIsNotNone(g)
        self.assertFalse(g.get("legacy"))                     # видна в настройках
        self.assertFalse(g.get("auto", True))                 # но не подбирается сама
        for gb in (4, 8, 16, 32, 64):
            self.assertNotEqual(C.recommend(gb)["id"], "gemma-3-4b-q4")
            self.assertNotIn("gemma-3-4b-q4", [m["id"] for m in C.pair_for(gb)])

    def test_every_tier_has_a_model(self):
        for gb in (6, 8, 16, 32):
            self.assertTrue(C.fits(C.recommend(gb), gb), gb)

    def test_label_tells_ram_verdict(self):
        big = C.by_id("qwen2.5-14b")
        self.assertIn("нужно не меньше 32 ГБ", C.label(big, 16))
        self.assertIn("подходит", C.label(big, 32))

    def test_url_points_to_huggingface(self):
        u = C.url(C.by_id("qwen2.5-7b"))
        self.assertTrue(u.startswith("https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/"))
        self.assertTrue(u.endswith(".gguf"))


class VisionTest(unittest.TestCase):
    def test_vision_model_is_not_a_text_choice(self):
        for gb in (4, 8, 16, 32, 64):
            self.assertNotEqual(C.recommend(gb).get("kind"), "vision")

    def test_vision_model_needs_projector(self):
        v = C.by_id("qwen2.5-vl-3b")
        self.assertTrue(v["mmproj_file"].startswith("mmproj-"))


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_download_then_installed_then_delete(self):
        body = b"x" * 1000
        with mock.patch.object(S.requests, "get", return_value=FakeResp(200, body)):
            ok = S.download("qwen3.5-4b", root=self.dir)
        self.assertTrue(ok)
        self.assertEqual(S.installed_ids(self.dir), ["qwen3.5-4b"])
        self.assertTrue(S.delete("qwen3.5-4b", root=self.dir))
        self.assertEqual(S.installed_ids(self.dir), [])

    def test_resume_appends_from_partial(self):
        entry = C.by_id("qwen3.5-4b")
        part = S.path_for("qwen3.5-4b", self.dir) + ".part"
        with open(part, "wb") as f:
            f.write(b"a" * 400)
        seen = {}

        def fake_get(url, headers=None, stream=None, timeout=None):
            seen["range"] = headers.get("Range")
            return FakeResp(206, b"b" * 600, {"Content-Length": "600"})

        with mock.patch.object(S.requests, "get", side_effect=fake_get):
            self.assertTrue(S.download("qwen3.5-4b", root=self.dir))
        self.assertEqual(seen["range"], "bytes=400-")
        with open(S.path_for("qwen3.5-4b", self.dir), "rb") as f:
            data = f.read()
        self.assertEqual(len(data), 1000)
        self.assertTrue(data.startswith(b"a" * 400) and data.endswith(b"b" * 600))

    def test_failed_download_leaves_no_final_file(self):
        with mock.patch.object(S.requests, "get", side_effect=S.requests.ConnectionError("нет сети")):
            self.assertFalse(S.download("qwen3.5-4b", root=self.dir, retries=2))
        self.assertEqual(S.installed_ids(self.dir), [])

    def test_vision_installed_only_with_projector(self):
        open(S.path_for("qwen2.5-vl-3b", self.dir), "wb").write(b"m")    # основной файл есть, проектора нет
        self.assertNotIn("qwen2.5-vl-3b", S.installed_ids(self.dir))
        with open(S.mmproj_path_for("qwen2.5-vl-3b", self.dir), "wb") as f:
            f.write(b"p")
        self.assertIn("qwen2.5-vl-3b", S.installed_ids(self.dir))

    def test_unknown_model(self):
        self.assertFalse(S.download("no-such-model", root=self.dir))
        self.assertIsNone(S.path_for("no-such-model", self.dir))

    def test_progress_reported_at_start_and_per_chunk(self):
        calls = []
        with mock.patch.object(S.requests, "get", return_value=FakeResp(200, b"x" * 200_000)):
            S.download("qwen3.5-4b", progress=lambda d, t: calls.append((d, t)), root=self.dir)
        self.assertEqual(calls[0][0], 0)                  # первое сообщение — до первого куска
        self.assertGreater(len(calls), 2)
        self.assertEqual(calls[-1][0], 200_000)


if __name__ == "__main__":
    unittest.main()
