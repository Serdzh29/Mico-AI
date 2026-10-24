"""Выбор устройства для встроенной модели: видеокарта, если она есть и сборка её умеет; иначе процессор.
Скорость не сравниваем. Без видеокарты и без Qt."""
import os
import subprocess
import sys
import unittest
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import accel as A

GPU = {"name": "NVIDIA GeForce RTX 3050", "total_mb": 4096, "free_mb": 3500}


class GpuInfoTest(unittest.TestCase):
    def test_parses_nvidia_smi_line(self):
        run = lambda *a, **k: SimpleNamespace(returncode=0, stdout="NVIDIA GeForce RTX 3050, 4096, 3500\n")
        self.assertEqual(A.gpu_info(run), GPU)

    def test_no_nvidia_smi_means_no_gpu(self):
        def run(*a, **k):
            raise FileNotFoundError("nvidia-smi")
        self.assertIsNone(A.gpu_info(run))

    def test_driver_error_means_no_gpu(self):
        run = lambda *a, **k: SimpleNamespace(returncode=9, stdout="")
        self.assertIsNone(A.gpu_info(run))


class ChooseTest(unittest.TestCase):
    def choose(self, loads, info=GPU, supported=True, model_mb=2000, cache=None):
        """loads — какие слои загружаются (множество). Возвращает результат, список проверенных слоёв и кэш."""
        calls = []

        def try_load(layers):
            calls.append(layers)
            return layers in loads
        cache = {} if cache is None else cache
        res = A.choose(model_mb, info, supported, try_load, cache, "m|gpu")
        return res, calls, cache

    def test_no_gpu_uses_cpu_without_checking(self):
        (layers, report), calls, _ = self.choose(set(), info=None)
        self.assertEqual(layers, A.CPU)
        self.assertEqual(calls, [])
        self.assertIn("не найдена", report)

    def test_build_without_gpu_support_uses_cpu(self):
        (layers, _), calls, _ = self.choose({A.FULL_GPU}, supported=False)
        self.assertEqual(layers, A.CPU)
        self.assertEqual(calls, [])

    def test_gpu_is_used_even_if_cpu_would_be_faster(self):
        # раньше сравнивали скорость и могли уйти на процессор; теперь видеокарта — всегда, если запустилась
        (layers, report), _, _ = self.choose({A.FULL_GPU})
        self.assertEqual(layers, A.FULL_GPU)
        self.assertIn("все ответы считаются на видеокарте", report)

    def test_gpu_that_cannot_load_falls_back_to_cpu(self):
        (layers, report), _, _ = self.choose(set())
        self.assertEqual(layers, A.CPU)
        self.assertIn("не запустила", report)

    def test_partial_offload_when_model_does_not_fit(self):
        small = dict(GPU, free_mb=1500)                      # 3 ГБ модель не влезает целиком
        (layers, report), calls, _ = self.choose({24}, info=small, model_mb=3000)
        self.assertNotIn(A.FULL_GPU, calls)                  # полную загрузку даже не пробуем
        self.assertEqual(layers, 24)
        self.assertIn("часть слоёв", report)

    def test_partial_falls_to_smaller_gpu_share_before_cpu(self):
        small = dict(GPU, free_mb=1500)
        (layers, _), calls, _ = self.choose({12}, info=small, model_mb=3000)
        self.assertEqual(layers, 12)
        self.assertEqual(calls, [24, 12])

    def test_result_is_cached(self):
        _, _, cache = self.choose({A.FULL_GPU})
        (layers, _), calls, _ = self.choose(set(), cache=cache)
        self.assertEqual(layers, A.FULL_GPU)
        self.assertEqual(calls, [])                          # второй раз не проверяем


if __name__ == "__main__":
    unittest.main()
