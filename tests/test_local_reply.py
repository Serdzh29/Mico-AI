"""Ответ встроенной модели: рассуждения Qwen не попадают пользователю, просьба «без рассуждений» добавляется."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import local_llm as L


class ReplyTest(unittest.TestCase):
    def test_closing_think_without_opening_is_removed(self):
        # шаблон Qwen сам ставит <think>, в ответе остаётся только хвост рассуждения и </think>
        text = "The user asks about Brawl Stars...\n</think>\n\n[happy] Бравл Старс — игра."
        self.assertEqual(L.clean_reply(text), "[happy] Бравл Старс — игра.")

    def test_full_think_block_is_removed(self):
        self.assertEqual(L.clean_reply("<think>хм</think>Привет"), "Привет")

    def test_plain_answer_unchanged(self):
        self.assertEqual(L.clean_reply("  Привет!  "), "Привет!")

    def test_no_think_added_to_last_user_message(self):
        msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "как дела"}]
        out = L._no_think(msgs)
        self.assertTrue(out[-1]["content"].endswith("/no_think"))
        self.assertEqual(msgs[-1]["content"], "как дела")          # исходная переписка не меняется
        self.assertEqual(L._no_think(out)[-1]["content"], out[-1]["content"])   # не дописываем дважды

    def test_no_think_only_for_qwen3(self):
        msgs = [{"role": "user", "content": "привет"}]
        self.assertTrue(L._messages_for("/m/Qwen_Qwen3.5-4B-Q4_K_M.gguf", msgs)[-1]["content"].endswith("/no_think"))
        out = L._messages_for("/m/Qwen2.5-7B-Instruct-Q4_K_M.gguf", msgs)
        self.assertEqual(out[-1]["content"], "привет")                 # Qwen2.5 — без пометки /no_think
        self.assertIn("русском", out[0]["content"])                    # а русский — всегда

    def test_russian_rule_added_once(self):
        msgs = [{"role": "system", "content": "Ты Mico."}, {"role": "user", "content": "hi"}]
        once = L._russian(msgs)
        self.assertEqual(once[0]["content"].count("русском"), 1)
        self.assertEqual(L._russian(once)[0]["content"].count("русском"), 1)


class EngineShapeTest(unittest.TestCase):
    def test_engine_methods_are_on_the_class(self):
        import local_llm
        for name in ("chat", "_try_load", "_unload_locked", "unload_if_idle", "_load"):
            self.assertTrue(hasattr(local_llm._Engine, name), name)


if __name__ == "__main__":
    unittest.main()
