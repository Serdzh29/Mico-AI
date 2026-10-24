"""Рассуждения модели не попадают в чат, даже если их обрезал лимит токенов."""
import os, sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import local_llm as L


class ReasoningLeak(unittest.TestCase):
    def test_truncated_reasoning_without_answer_is_not_shown(self):
        text = "Thinking Process:\n\n1. **Analyze the Request:**\n   * Constraint 1: I am Mico AI"
        self.assertEqual(L.clean_reply(text), L.NO_ANSWER)

    def test_answer_found_inside_untagged_reasoning(self):
        text = "Thinking Process:\n1. Analyze\n   * Draft:\n   *   [happy] Бравл Старс — мобильная игра."
        self.assertEqual(L.clean_reply(text), "[happy] Бравл Старс — мобильная игра.")

    def test_unclosed_think_tag_is_cut(self):
        self.assertEqual(L.clean_reply("<think>долго думаю"), L.NO_ANSWER)

    def test_normal_answer_untouched(self):
        self.assertEqual(L.clean_reply("[love] Привет!"), "[love] Привет!")


if __name__ == "__main__":
    unittest.main()
