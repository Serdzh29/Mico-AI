import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import mailreport as M
from urllib.parse import unquote, urlsplit, parse_qs


def test_body_has_versions_and_counts_but_no_texts():
    body = M.build_body("2026.10.1217", "22631", {"up": 3, "down": 0, "idea": 1})
    assert "2026.10.1217" in body and "22631" in body
    assert "up — 3" in body and "idea — 1" in body and "down" not in body


def test_body_is_capped():
    body = M.build_body("x", None, {}, note="а" * 5000)
    assert len(body) <= M.MAX_BODY


def test_mailto_link_encodes_cyrillic_and_recipient():
    link = M.mailto_link("dev@example.com", "Отчёт Mico (бета)", "Привет\nмир")
    parts = urlsplit(link)
    assert parts.scheme == "mailto" and parts.path == "dev@example.com"
    q = parse_qs(parts.query)
    assert q["subject"] == ["Отчёт Mico (бета)"]
    assert q["body"] == ["Привет\nмир"]


def test_no_recipient_means_no_link():
    assert M.mailto_link("", "тема", "текст") is None
    assert M.mailto_link("не адрес", "тема", "текст") is None


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
