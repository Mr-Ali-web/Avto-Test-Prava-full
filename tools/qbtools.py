"""Savollar partiyalarini qurish va tekshirish uchun umumiy funksiyalar."""
import csv
import json
import os
import random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")


def build_rows(items, start_id, src="YHQ"):
    """items: (mavzu, savol, to'g'ri javob, [noto'g'ri javoblar], band, tushuntirish)"""
    rows, seen = [], set()
    for i, (topic, text, correct, wrongs, band, expl) in enumerate(items):
        qid = start_id + i
        opts = [correct] + list(wrongs)
        assert len(set(opts)) == len(opts), f"Takroriy variant: {qid} | {text[:50]}"
        assert 2 <= len(opts) <= 4, f"Variantlar soni noto'g'ri: {qid}"
        assert text not in seen, f"Takroriy savol: {qid}"
        seen.add(text)
        random.Random(qid).shuffle(opts)
        band_txt = band if band.startswith("VM") else f"{band}-band"
        rows.append({"id": qid, "topic": topic, "text": text, "options": opts,
                     "answer": opts.index(correct), "explain": expl,
                     "source": f"{src}, {band_txt}", "status": "draft"})
    return rows


def save_json(rows, filename):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, filename), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)


def save_review_csv(rows, filename):
    with open(os.path.join(DATA, filename), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Mavzu", "Savol", "A", "B", "C", "D", "To'g'ri javob", "Manba",
                    "Tushuntirish", "Ekspert xulosasi (to'g'ri / noto'g'ri / o'zgartirish)", "Izoh"])
        for r in rows:
            o = r["options"] + [""] * (4 - len(r["options"]))
            w.writerow([r["id"], r["topic"], r["text"], *o, "ABCD"[r["answer"]], r["source"],
                        r["explain"], "", ""])


def report(rows):
    by_topic = {}
    for r in rows:
        by_topic[r["topic"]] = by_topic.get(r["topic"], 0) + 1
    print(f"Jami: {len(rows)} ta savol")
    for t, n in sorted(by_topic.items(), key=lambda x: -x[1]):
        print(f"  {n:3d}  {t}")
    pos = [r["answer"] for r in rows]
    print("To'g'ri javob o'rinlari (A,B,C,D):", [pos.count(k) for k in range(4)])
