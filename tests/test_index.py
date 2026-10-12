import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, os, tempfile, time
sys.path.insert(0, ROOT)
import indexer as I
# структура
root = tempfile.mkdtemp()
def mk(rel, data=b"x"):
    p = os.path.join(root, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(data); return p
mk("Pictures/кот на диване.jpg"); mk("Pictures/отпуск/море.png"); mk("Documents/договор аренды.docx")
mk("Documents/node_modules/x.js"); mk("Music/любимая песня.mp3"); mk("Videos/фильм.mkv")
os.makedirs(os.path.join(root, "Games", "Hades"), exist_ok=True)
mk("Programs/Telegram/Telegram.exe")
steps = []
recs = I.collect(progress=lambda p, t: steps.append(p),
                 roots_user=[os.path.join(root, "Pictures"), os.path.join(root, "Documents"),
                             os.path.join(root, "Music"), os.path.join(root, "Videos")],
                 roots_programs=[os.path.join(root, "Programs")],
                 roots_games=[os.path.join(root, "Games")])
kinds = {}
for r in recs: kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
print("kinds:", kinds)
assert "node_modules" not in " ".join(r["path"] for r in recs)
assert steps == sorted(steps) and steps[-1] == 100, steps
print("progress monotonic, ends at 100:", steps[:6], "...", steps[-1])
print("search 'кот':", [r["name"] for r in I.search("найди кот", recs)])
print("search 'фото':", [r["name"] for r in I.search("покажи фото", recs)])
print("search 'игры':", [r["name"] for r in I.search("какие у меня игры", recs)])
print("search 'договор':", [r["name"] for r in I.search("где договор", recs)])
print("search 'телеграм':", [r["name"] for r in I.search("найди телеграм", recs)])
print("search 'песня':", [r["name"] for r in I.search("найди песню", recs)])
print("search nothing:", I.search("найди космолёт", recs))
