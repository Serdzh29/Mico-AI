"""База знаний о Windows 11 26H2 и инсайдерских сборках: поиск, источники Microsoft, неподтверждённое не как факт."""
import os as _os, sys, json, re
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import knowledge

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

items = [i for i in knowledge.load(_os.path.join(ROOT, "knowledge")) if i["source"] == "windows_insider"]
check(len(items) >= 6, f"мало статей: {len(items)}")

# --- поиск отвечает статьями о 26H2 и каналах ---
items_all = knowledge.load(_os.path.join(ROOT, "knowledge"))
for q in ["что такое 26H2", "какие есть инсайдерские каналы", "как перейти в канал Experimental", "вышла ли 26H2"]:
    hits = knowledge.search(q, items_all, limit=1)
    check(hits and hits[0][1]["source"] == "windows_insider", (q, [h[1]["title"] for h in hits]))

# --- у каждой статьи есть источник от Microsoft ---
for it in items:
    body = it["body"]
    check(re.search(r"Microsoft|blogs\.windows\.com|learn\.microsoft\.com|mc\.merill\.net", body), it["title"])

# --- неподтверждённое стоит только в своём разделе, не в фактах ---
text = open(_os.path.join(ROOT, "knowledge", "windows_insider.md"), encoding="utf-8").read()
head, _, unconfirmed = text.partition("## Что пока не подтверждено Microsoft")
check(unconfirmed, "нет раздела о неподтверждённом")
for rumor in ["Copilot в проводнике", "агент", "ИИ в диспетчере"]:
    check(rumor not in head, f"слух «{rumor}» попал в факты")
check("10 октября 2028" in head and "release health" in head, "дата поддержки 26H2 без источника Microsoft")

# --- данные о сборках: официальное помечено, непроверенное — нет ---
d = json.load(open(_os.path.join(ROOT, "data", "windows_releases.json"), encoding="utf-8"))
for b in d["builds"]:
    if b.get("official") is True:
        check(re.search(r"Insider|Microsoft|blogs\.windows", b.get("source", "")), b["build"])
    if b["build"] == "26300.9457":
        check(b.get("official") is True and "Microsoft" in b.get("source", ""), "сборка выпуска 26H2 без источника Microsoft")
for lc in d["lifecycle"]:
    if lc["version"] == "26H2":
        check(lc.get("home_pro_end") == "2028-10-10" and "Microsoft" in lc.get("source", ""), "срок 26H2 без источника")
    if lc["version"] == "24H2":
        check("13 октября 2026" in lc.get("note", ""), "24H2: дата окончания обновлений")

print("ALL OK")
