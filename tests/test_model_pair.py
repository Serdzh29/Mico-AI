"""Установка: модель в каталоге одна, поэтому «лёгкая» и «мощная» совпадают (старый интерфейс пары сохранён)."""
import os, sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from llm import catalog as C


class ModelPair(unittest.TestCase):
    def test_pair_is_the_single_catalog_model(self):
        for gb in (4, 8, 16, 24, 32, 64):
            light, heavy = C.pair_for(gb)
            self.assertIs(light, C.CATALOG[0], gb)
            self.assertIs(heavy, C.CATALOG[0], gb)

    def test_pair_accepts_the_old_tiers_argument(self):
        light, heavy = C.pair_for(16, tiers=[{"id": "старая-ступень"}])
        self.assertEqual(heavy["id"], "qwen3.5-4b")

    def test_single_model_is_the_recommended_one(self):
        for gb in (8, 16, 32):
            self.assertEqual(C.recommend(gb)["id"], C.pair_for(gb)[1]["id"], gb)


if __name__ == "__main__":
    unittest.main()
