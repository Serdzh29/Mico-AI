"""«Выход» закрывает Ollama: фейковые процессы, без реальных."""
import unittest
from unittest import mock

import ollama_ctl


class FakeProc:
    def __init__(self, name, alive_after_terminate=False):
        self.info = {"name": name}
        self.terminated = self.killed = False
        self.alive_after_terminate = alive_after_terminate

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


class OllamaExitTest(unittest.TestCase):
    def test_stops_only_ollama_processes(self):
        procs = [FakeProc("ollama.exe"), FakeProc("ollama app.exe"), FakeProc("chrome.exe"), FakeProc("python.exe")]
        with mock.patch.object(ollama_ctl.psutil, "process_iter", return_value=procs), \
             mock.patch.object(ollama_ctl.psutil, "wait_procs", return_value=([], [])):
            n = ollama_ctl.stop_ollama()
        self.assertEqual(n, 2)
        self.assertTrue(procs[0].terminated and procs[1].terminated)
        self.assertFalse(procs[2].terminated)
        self.assertFalse(procs[3].terminated)

    def test_kills_survivors(self):
        stubborn = FakeProc("ollama_llama_server.exe")
        with mock.patch.object(ollama_ctl.psutil, "process_iter", return_value=[stubborn]), \
             mock.patch.object(ollama_ctl.psutil, "wait_procs", return_value=([], [stubborn])):
            ollama_ctl.stop_ollama()
        self.assertTrue(stubborn.killed)

    def test_nothing_running(self):
        with mock.patch.object(ollama_ctl.psutil, "process_iter", return_value=[FakeProc("explorer.exe")]):
            self.assertEqual(ollama_ctl.stop_ollama(), 0)


if __name__ == "__main__":
    unittest.main()
