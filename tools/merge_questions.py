"""data/questions_yhq_v*.json partiyalarini bitta questions_all.json ga birlashtiradi.

Yangi partiya qo'shish: tools/build_questions_vN.py yozing (qbtools.build_rows orqali),
uni ishga tushiring, so'ng:  python3 tools/merge_questions.py
Bot avtomatik data/questions_all.json ni ishlatadi.
"""
import glob
import json
import os

import qbtools

rows = []
for path in sorted(glob.glob(os.path.join(qbtools.DATA, "questions_yhq_v*.json"))):
    with open(path, encoding="utf-8") as f:
        batch = json.load(f)
    print(f"{os.path.basename(path)}: {len(batch)} ta")
    rows += batch

ids = [r["id"] for r in rows]
assert len(ids) == len(set(ids)), "Takroriy ID lar bor!"
texts = [r["text"] for r in rows]
assert len(texts) == len(set(texts)), "Takroriy savol matnlari bor!"
for r in rows:
    assert 2 <= len(r["options"]) <= 4 and 0 <= r["answer"] < len(r["options"]), f"Xato: {r['id']}"

qbtools.save_json(rows, "questions_all.json")
qbtools.save_review_csv(rows, "review_sheet_all.csv")
qbtools.report(rows)
