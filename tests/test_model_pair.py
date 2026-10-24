"""Установка: для каждой памяти есть лёгкая и мощная модель; мощная выбрана по памяти, лёгкая — ступенью ниже."""
import os, sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import model_catalog as C


class ModelPair(unittest.TestCase):
    def test_ollama_16gb_heavy_is_qwen35_light_is_qwen25(self):
        light, heavy = C.pair_for(16, C.OLLAMA_TIERS)
        self.assertEqual(heavy["id"], "qwen3.5:9b")
        self.assertEqual(light["id"], "qwen2.5:3b")

    def test_ollama_small_memory_has_one_model(self):
        light, heavy = C.pair_for(6, C.OLLAMA_TIERS)
        self.assertEqual(light["id"], heavy["id"])

    def test_builtin_pairs_come_from_catalog(self):
        light, heavy = C.pair_for(16)
        self.assertEqual(heavy["id"], "qwen2.5-3b-q5")     # мощная теперь — тоже лёгкая Qwen2.5 3B
        self.assertEqual(light["id"], "qwen2.5-3b")
        light, heavy = C.pair_for(4)
        self.assertEqual(light["id"], heavy["id"])

    def test_pair_never_picks_legacy(self):
        for gb in (4, 8, 16, 24, 32, 64):
            for m in C.pair_for(gb):
                self.assertFalse(m.get("legacy"), (gb, m["id"]))


if __name__ == "__main__":
    unittest.main()
