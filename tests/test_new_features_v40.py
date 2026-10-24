import os as _os, sys as _sys, tempfile, zipfile
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import hogs, errhelp, filereader as F


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_hogs_phrases_and_filter():
    check(hogs.command("что тормозит компьютер"))
    check(hogs.command("Что сейчас грузит процессор?"))
    check(hogs.command("почему компьютер тормозит"))
    check(not hogs.command("что такое процессор"))
    check(not hogs.command("закрой браузер"))
    samples = [
        {"name": "explorer.exe", "pid": 100, "cpu": 90, "mem": 2 * 1024 ** 3},     # системный — не трогаем
        {"name": "chrome.exe", "pid": 200, "cpu": 40, "mem": 3 * 1024 ** 3},
        {"name": "idle.exe", "pid": 300, "cpu": 1, "mem": 10 * 1024 ** 2},         # незаметный
        {"name": "teams.exe", "pid": 400, "cpu": 5, "mem": 1200 * 1024 ** 2},
    ]
    top = hogs.pick(samples)
    check([s["name"] for s in top] == ["chrome.exe", "teams.exe"], top)
    check(hogs.is_protected("python.exe", 1) and hogs.is_protected("x", 4), "системные процессы защищены")
    check("chrome.exe" in hogs.describe(samples[1]) and "ГБ" in hogs.describe(samples[1]))




def test_errhelp_phrases_and_log():
    check(errhelp.command("покажи журнал") == "log")
    check(errhelp.command("покажи последние строки журнала") == "log")
    check(errhelp.command("найди решение") == "help")
    check(errhelp.command("открой справку windows") == "help")
    check(errhelp.command("какая погода") is None)
    d = tempfile.mkdtemp()
    name, text = errhelp.log_tail(d)
    check(name is None and text == "", "журнала нет — ничего не выдумываем")
    with open(_os.path.join(d, "crash.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(f"строка {i}" for i in range(40)))
    name, text = errhelp.log_tail(d)
    check(name == "crash.log" and "строка 39" in text and "строка 0" not in text, "берём только хвост")


def test_docx_and_pdf_reading():
    d = tempfile.mkdtemp()
    docx = _os.path.join(d, "plan.docx")
    body = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            '<w:p><w:r><w:t>Срок сдачи: 15 ноября.</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>Бюджет</w:t></w:r><w:r><w:t xml:space="preserve"> не указан.</w:t></w:r></w:p>'
            '</w:body></w:document>')
    with zipfile.ZipFile(docx, "w") as z:
        z.writestr("word/document.xml", body)
    check(F.kind(docx) == "text")
    text = F.read_text(docx)
    check("Срок сдачи: 15 ноября." in text and "Бюджет не указан." in text, text)
    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        return                                               # reportlab нужен только для теста PDF
    pdf = _os.path.join(d, "doc.pdf")
    c = canvas.Canvas(pdf)
    c.drawString(72, 720, "Deadline is 15 November.")
    c.save()
    check(F.kind(pdf) == "text")
    check("15 November" in F.read_text(pdf), "PDF читается")


def test_excerpt_picks_relevant_paragraphs():
    text = "\n\n".join([f"Вводная часть номер {i}. " + "слово " * 40 for i in range(30)]
                       + ["Сроки сдачи проекта: до 15 ноября 2026 года."])
    out = F.excerpt(text, "что здесь про сроки?", 800)
    check("Сроки сдачи" in out, "нашли абзац про сроки")
    check(len(out) <= 800 + 10, len(out))
    check(F.excerpt("коротко", "что угодно", 800) == "коротко", "короткий текст — целиком")
