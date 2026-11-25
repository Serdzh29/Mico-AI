"""Привычки: частые программы и команды по времени дня (чистая логика, без Qt)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import habits

now = time.time()
rows = [(now - 3600, now - 600, "chrome.exe", "x"), (now - 7200, now - 7000, "telegram.exe", "y"),
        (now - 500, now - 100, "explorer.exe", "z"), (now - 900, now - 880, "notepad.exe", "short"),
        (now - 40 * 86400, now - 39 * 86400, "steam.exe", "old")]
u = habits.app_usage(rows, now)
assert "chrome.exe" in u and "telegram.exe" in u, u
assert "explorer.exe" not in u, "системные окна не предлагаем"
assert "notepad.exe" not in u, "короткое открытие — не привычка"
assert "steam.exe" not in u, "старые записи не учитываем"
assert habits.top_apps(u, 1) == [("chrome.exe", "Chrome")]
assert habits.app_usage(rows, now, blocked=["chrome"]).get("chrome.exe") is None, "заблокированное не учитываем"
assert habits.app_label("myapp.exe") == "Myapp" and habits.app_label("") is None

cfg = {"chip_usage": {"a": 3, "b": 3}}
assert habits.command_score(cfg, "a", now) == 3.0, "без часов — просто счётчик"
habits.note_command(cfg, "a", now)
assert habits.command_score(cfg, "a", now) > habits.command_score(cfg, "b", now), "в этот час команда важнее"
assert habits.command_score(cfg, "zzz", now) == 0.0
print("OK habits")
