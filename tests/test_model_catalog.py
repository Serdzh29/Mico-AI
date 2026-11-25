"""Каталог и хранение единственной текстовой модели Mico: одна модель, ссылка на HF, докачка, удаление (без сети)."""
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from llm import catalog as C
from llm import store as S


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
    def test_catalog_is_a_single_verified_model(self):
        self.assertEqual(len(C.CATALOG), 1, "в каталоге одна текстовая модель")
        entry = C.CATALOG[0]
        self.assertEqual(entry["id"], "qwen3.5-4b")
        self.assertTrue(entry["verified"])
        self.assertTrue(entry["file"].endswith(".gguf"))
        self.assertGreater(entry["size_gb"], 0)
        self.assertGreaterEqual(entry["min_ram_gb"], 8)

    def test_recommend_is_the_only_model(self):
        for gb in (4, 8, 16, 32, 64):
            self.assertEqual(C.recommend(gb)["id"], "qwen3.5-4b", gb)

    def test_windows_reports_slightly_less_memory(self):
        # 8 ГБ в Windows — это около 7,8 ГБ, и модель всё равно должна считаться подходящей
        entry = C.CATALOG[0]
        self.assertTrue(C.fits(entry, 7.8))
        self.assertFalse(C.fits(entry, 7.4))

    def test_by_id_finds_only_known_models(self):
        self.assertIsNotNone(C.by_id("qwen3.5-4b"))
        self.assertIsNone(C.by_id("gemma-3-4b-q4"))
        self.assertIsNone(C.by_id("no-such-model"))

    def test_label_tells_about_the_model(self):
        text = C.label(C.CATALOG[0], 16)
        self.assertIn(C.CATALOG[0]["title"], text)
        self.assertIn("ГБ", text)

    def test_url_points_to_huggingface(self):
        u = C.url(C.CATALOG[0])
        self.assertTrue(u.startswith("https://huggingface.co/"))
        self.assertTrue(u.endswith(".gguf"))


class PairTest(unittest.TestCase):
    def test_pair_is_the_single_model(self):
        for gb in (4, 8, 16, 32):
            light, heavy = C.pair_for(gb)
            self.assertIs(light, C.CATALOG[0])
            self.assertIs(heavy, C.CATALOG[0])


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

    def test_broken_content_length_does_not_crash(self):
        """Мусор в Content-Length не должен ронять загрузку: итог берём из подсказки размера."""
        calls = []
        resp = FakeResp(200, b"x" * 100, {"Content-Length": "мусор"})
        with mock.patch.object(S.requests, "get", return_value=resp):
            self.assertTrue(S.download("qwen3.5-4b", progress=lambda d, t: calls.append((d, t)), root=self.dir))
        for done, total in calls:
            self.assertGreaterEqual(done, 0)
            self.assertGreater(total, 0)


if __name__ == "__main__":
    unittest.main()
