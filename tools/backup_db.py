"""Bazaning zaxira nusxasini oladi (bot ishlab turganda ham xavfsiz).

Ishlatish:  python3 tools/backup_db.py            (DB_PATH muhit o'zgaruvchisi yoki config'dan)
Cron (har kuni 03:00):  0 3 * * * cd /opt/pravaga_bot && python3 tools/backup_db.py
Oxirgi 14 ta nusxa saqlanadi.
"""
import glob
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH  # noqa: E402

KEEP = 14
folder = os.path.join(os.path.dirname(DB_PATH) or ".", "backups")
os.makedirs(folder, exist_ok=True)
target = os.path.join(folder, f"pravaga_{datetime.now():%Y%m%d_%H%M}.db")

src, dst = sqlite3.connect(DB_PATH), sqlite3.connect(target)
with dst:
    src.backup(dst)
src.close(), dst.close()

for old in sorted(glob.glob(os.path.join(folder, "pravaga_*.db")))[:-KEEP]:
    os.remove(old)
print("Zaxira nusxa:", target)
