import json
from datetime import datetime, timedelta, timezone

import aiosqlite

from config import (DAILY_BONUS_XP, DB_PATH, PLANS, REFERRAL_BONUS_DAYS, REFERRAL_MIN_ANSWERS,
                    SCHOOL_BONUS_DAYS, STREAK_REWARDS, TZ_OFFSET_HOURS, XP_PER_CORRECT)

SCHEMA = """
CREATE TABLE IF NOT EXISTS schools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    tg_id INTEGER PRIMARY KEY,
    name TEXT,
    created_at TEXT NOT NULL,
    streak INTEGER NOT NULL DEFAULT 0,
    last_active TEXT,
    xp INTEGER NOT NULL DEFAULT 0,
    premium_until TEXT,
    referred_by INTEGER,
    ref_rewarded INTEGER NOT NULL DEFAULT 0,
    school_id INTEGER REFERENCES schools(id),
    reminders_on INTEGER NOT NULL DEFAULT 1,
    last_reminder TEXT,
    streak_reward INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    topic TEXT,
    correct INTEGER NOT NULL,
    ts TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'practice'
);
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    errors INTEGER,
    passed INTEGER
);
CREATE INDEX IF NOT EXISTS idx_answers_user ON answers(tg_id);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    plan TEXT NOT NULL,
    amount INTEGER NOT NULL,
    method TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    proof_file_id TEXT,
    charge_id TEXT UNIQUE,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    decided_by INTEGER
);
CREATE TABLE IF NOT EXISTS sessions (
    tg_id INTEGER PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS daily_challenges (
    tg_id INTEGER NOT NULL,
    day TEXT NOT NULL,
    correct INTEGER NOT NULL,
    total INTEGER NOT NULL,
    ts TEXT NOT NULL,
    PRIMARY KEY (tg_id, day)
);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


TZ = timezone(timedelta(hours=TZ_OFFSET_HOURS))


def _today_start() -> datetime:
    """Toshkent vaqti bo'yicha bugungi kun boshlanishi (UTC da)."""
    local = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    return local.astimezone(timezone.utc)


async def init() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        cur = await db.execute("PRAGMA table_info(answers)")
        cols = {r[1] for r in await cur.fetchall()}
        if "mode" not in cols:  # eski bazalar uchun migratsiya
            await db.execute("ALTER TABLE answers ADD COLUMN mode TEXT NOT NULL DEFAULT 'practice'")
        cur = await db.execute("PRAGMA table_info(users)")
        ucols = {r[1] for r in await cur.fetchall()}
        for col, ddl in (("reminders_on", "INTEGER NOT NULL DEFAULT 1"),
                         ("last_reminder", "TEXT"),
                         ("streak_reward", "INTEGER NOT NULL DEFAULT 0")):
            if col not in ucols:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
        await db.commit()


async def add_school(code: str, name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO schools(code, name) VALUES (?, ?)", (code, name))
        await db.commit()


async def _grant_days(db: aiosqlite.Connection, tg_id: int, days: int) -> None:
    cur = await db.execute("SELECT premium_until FROM users WHERE tg_id=?", (tg_id,))
    row = await cur.fetchone()
    base = _now()
    if row and row[0]:
        current = datetime.fromisoformat(row[0])
        if current > base:
            base = current
    await db.execute("UPDATE users SET premium_until=? WHERE tg_id=?",
                     (_iso(base + timedelta(days=days)), tg_id))


async def register(tg_id: int, name: str, ref_by: int | None = None,
                   school_code: str | None = None) -> dict:
    """Yangi foydalanuvchini yaratadi. Qaytaradi: {"created": bool, "school": str|None}."""
    result = {"created": False, "school": None}
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM users WHERE tg_id=?", (tg_id,))
        if await cur.fetchone():
            return result
        if ref_by == tg_id:
            ref_by = None
        school_id = None
        if school_code:
            cur = await db.execute("SELECT id, name FROM schools WHERE code=?", (school_code,))
            row = await cur.fetchone()
            if row:
                school_id, result["school"] = row[0], row[1]
        await db.execute(
            "INSERT INTO users(tg_id, name, created_at, referred_by, school_id) VALUES (?,?,?,?,?)",
            (tg_id, name, _iso(_now()), ref_by, school_id))
        if school_id:
            await _grant_days(db, tg_id, SCHOOL_BONUS_DAYS)
        await db.commit()
        result["created"] = True
    return result


async def is_premium(tg_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT premium_until FROM users WHERE tg_id=?", (tg_id,))
        row = await cur.fetchone()
    return bool(row and row[0] and datetime.fromisoformat(row[0]) > _now())


async def record_answer(tg_id: int, question_id: int, topic: str, correct: bool,
                        xp_per_correct: int = XP_PER_CORRECT, mode: str = "practice") -> dict:
    """Javobni yozadi, streak/XP ni yangilaydi, kerak bo'lsa referral bonusini beradi.
    Qaytaradi: {"referrer": int|None} - bonus berilgan bo'lsa taklif qilgan odam id si."""
    out = {"referrer": None, "streak_reward": None}
    today = datetime.now(TZ).date()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO answers(tg_id, question_id, topic, correct, ts, mode) VALUES (?,?,?,?,?,?)",
            (tg_id, question_id, topic, int(correct), _iso(_now()), mode))

        cur = await db.execute(
            "SELECT streak, last_active, referred_by, ref_rewarded, streak_reward FROM users WHERE tg_id=?",
            (tg_id,))
        streak, last_active, referred_by, ref_rewarded, streak_reward = await cur.fetchone()
        last = datetime.fromisoformat(last_active).astimezone(TZ).date() if last_active else None
        if last != today:
            if last == today - timedelta(days=1):
                streak += 1
            else:
                streak, streak_reward = 1, 0  # marafon uzildi, qaytadan boshlanadi
            days = STREAK_REWARDS.get(streak)
            if days and streak > streak_reward:
                await _grant_days(db, tg_id, days)
                streak_reward = streak
                out["streak_reward"] = (streak, days)
        await db.execute(
            "UPDATE users SET streak=?, last_active=?, xp=xp+?, streak_reward=? WHERE tg_id=?",
            (streak, _iso(_now()), xp_per_correct if correct else 0, streak_reward, tg_id))

        if referred_by and not ref_rewarded:
            cur = await db.execute("SELECT COUNT(*) FROM answers WHERE tg_id=?", (tg_id,))
            (count,) = await cur.fetchone()
            if count >= REFERRAL_MIN_ANSWERS:
                await _grant_days(db, tg_id, REFERRAL_BONUS_DAYS)
                await _grant_days(db, referred_by, REFERRAL_BONUS_DAYS)
                await db.execute("UPDATE users SET ref_rewarded=1 WHERE tg_id=?", (tg_id,))
                out["referrer"] = referred_by
        await db.commit()
    return out


async def exams_today(tg_id: int) -> int:
    start = _today_start()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM exams WHERE tg_id=? AND started_at>=?", (tg_id, _iso(start)))
        (n,) = await cur.fetchone()
    return n


async def start_exam(tg_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO exams(tg_id, started_at) VALUES (?,?)",
                               (tg_id, _iso(_now())))
        await db.commit()
        return cur.lastrowid


async def finish_exam(exam_id: int, errors: int, passed: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE exams SET errors=?, passed=? WHERE id=?",
                         (errors, int(passed), exam_id))
        await db.commit()


async def get_stats(tg_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT streak, xp, premium_until FROM users WHERE tg_id=?", (tg_id,))
        streak, xp, premium_until = await cur.fetchone()
        cur = await db.execute(
            "SELECT COUNT(*), COALESCE(SUM(correct),0) FROM answers WHERE tg_id=?", (tg_id,))
        total, correct = await cur.fetchone()
        cur = await db.execute(
            """SELECT topic FROM answers WHERE tg_id=? GROUP BY topic
               HAVING COUNT(*) >= 3 ORDER BY AVG(correct) ASC LIMIT 1""", (tg_id,))
        weak = await cur.fetchone()
    premium = None
    if premium_until and datetime.fromisoformat(premium_until) > _now():
        premium = datetime.fromisoformat(premium_until).strftime("%d.%m.%Y")
    return {"streak": streak, "xp": xp, "total": total, "correct": correct,
            "weak_topic": weak[0] if weak else None, "premium": premium}


async def get_profile(tg_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT u.name, u.created_at, u.streak, u.xp, u.premium_until, s.name,
                      u.last_active, u.reminders_on
               FROM users u LEFT JOIN schools s ON s.id = u.school_id WHERE u.tg_id=?""", (tg_id,))
        row = await cur.fetchone()
        if not row:
            return None
        name, created_at, streak, xp, premium_until, school, last_active, reminders_on = row
        cur = await db.execute(
            "SELECT COUNT(*), COALESCE(SUM(correct),0) FROM answers WHERE tg_id=?", (tg_id,))
        total, correct = await cur.fetchone()
        cur = await db.execute(
            "SELECT COUNT(*), COALESCE(SUM(passed),0) FROM exams WHERE tg_id=? AND passed IS NOT NULL",
            (tg_id,))
        exams, passed = await cur.fetchone()
        cur = await db.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by=? AND ref_rewarded=1", (tg_id,))
        (invited,) = await cur.fetchone()
        cur = await db.execute(
            """SELECT topic FROM answers WHERE tg_id=? GROUP BY topic
               HAVING COUNT(*) >= 3 ORDER BY AVG(correct) ASC LIMIT 1""", (tg_id,))
        weak = await cur.fetchone()
        cur = await db.execute(
            "SELECT correct, total FROM daily_challenges WHERE tg_id=? AND day=?", (tg_id, today_str()))
        daily = await cur.fetchone()
    premium = None
    if premium_until and datetime.fromisoformat(premium_until) > _now():
        premium = datetime.fromisoformat(premium_until).strftime("%d.%m.%Y")
    return {"name": name, "streak": _effective_streak(streak, last_active), "xp": xp,
            "reminders_on": bool(reminders_on), "daily": {"correct": daily[0], "total": daily[1]} if daily else None, "total": total, "correct": correct,
            "exams": exams, "passed": passed, "invited": invited, "school": school,
            "premium": premium, "weak_topic": weak[0] if weak else None}


async def get_topic_stats(tg_id: int) -> list[tuple[str, int, int]]:
    """[(mavzu, jami, to'g'ri)] - eng zaif mavzu birinchi."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """SELECT topic, COUNT(*), SUM(correct) FROM answers WHERE tg_id=?
               GROUP BY topic ORDER BY AVG(correct) ASC, COUNT(*) DESC""", (tg_id,))
        return [(r[0], r[1], r[2] or 0) for r in await cur.fetchall()]


async def practice_today(tg_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM answers WHERE tg_id=? AND mode='practice' AND ts>=?",
            (tg_id, _iso(_today_start())))
        (n,) = await cur.fetchone()
    return n


async def premium_until_str(tg_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT premium_until FROM users WHERE tg_id=?", (tg_id,))
        row = await cur.fetchone()
    if row and row[0] and datetime.fromisoformat(row[0]) > _now():
        return datetime.fromisoformat(row[0]).astimezone(TZ).strftime("%d.%m.%Y")
    return None


# ---------------- To'lovlar ----------------
async def create_payment(tg_id: int, plan: str, amount: int, method: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO payments(tg_id, plan, amount, method, created_at) VALUES (?,?,?,?,?)",
            (tg_id, plan, amount, method, _iso(_now())))
        await db.commit()
        return cur.lastrowid


async def _fetch_payments(query: str, params: tuple) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(query, params)
        return [dict(r) for r in await cur.fetchall()]


async def get_payment(pid: int) -> dict | None:
    rows = await _fetch_payments("SELECT * FROM payments WHERE id=?", (pid,))
    return rows[0] if rows else None


async def latest_open_payment(tg_id: int) -> dict | None:
    """Karta orqali yaratilgan, hali chek yuborilmagan eng so'nggi to'lov."""
    rows = await _fetch_payments(
        """SELECT * FROM payments WHERE tg_id=? AND method='card' AND status='pending'
           AND proof_file_id IS NULL ORDER BY id DESC LIMIT 1""", (tg_id,))
    return rows[0] if rows else None


async def attach_proof(pid: int, proof: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payments SET proof_file_id=? WHERE id=?", (proof, pid))
        await db.commit()


async def list_pending() -> list[dict]:
    return await _fetch_payments(
        "SELECT * FROM payments WHERE status='pending' AND proof_file_id IS NOT NULL ORDER BY id", ())


async def decide_payment(pid: int, approve: bool, admin_id: int) -> dict | None:
    """To'lovni tasdiqlaydi/rad etadi. Faqat 'pending' holatdagi to'lov uchun ishlaydi
    (ikki marta bosilsa, ikkinchisi None qaytaradi). Tasdiqlansa premium kunlari beriladi."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM payments WHERE id=? AND status='pending'", (pid,))
        row = await cur.fetchone()
        if not row:
            return None
        pay = dict(row)
        if approve:
            await _grant_days(db, pay["tg_id"], PLANS[pay["plan"]]["days"])
        await db.execute(
            "UPDATE payments SET status=?, decided_at=?, decided_by=? WHERE id=?",
            ("approved" if approve else "rejected", _iso(_now()), admin_id, pid))
        await db.commit()
        return pay


async def record_invoice_payment(tg_id: int, plan: str, amount: int, charge_id: str) -> bool:
    """Telegram (Click/Payme) orqali muvaffaqiyatli to'lov. Takroriy charge_id e'tiborga olinmaydi."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """INSERT INTO payments(tg_id, plan, amount, method, status, charge_id, created_at, decided_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (tg_id, plan, amount, "invoice", "approved", charge_id, _iso(_now()), _iso(_now())))
        except aiosqlite.IntegrityError:
            return False
        await _grant_days(db, tg_id, PLANS[plan]["days"])
        await db.commit()
    return True


async def grant_days_admin(tg_id: int, days: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM users WHERE tg_id=?", (tg_id,))
        if not await cur.fetchone():
            return False
        await _grant_days(db, tg_id, days)
        await db.commit()
    return True


async def admin_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        (users,) = await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
        (prem,) = await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE premium_until > ?", (_iso(_now()),))).fetchone()
        cnt, total = await (await db.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM payments WHERE status='approved'")).fetchone()
        (pend,) = await (await db.execute(
            "SELECT COUNT(*) FROM payments WHERE status='pending' AND proof_file_id IS NOT NULL")).fetchone()
    return {"users": users, "premium": prem, "paid_count": cnt, "paid_sum": total, "pending": pend}


# ---------------- Kunlik 10 ta, marafon, eslatmalar ----------------
def today_str() -> str:
    return datetime.now(TZ).date().isoformat()


def _effective_streak(streak: int, last_active: str | None) -> int:
    """Marafon uzilgan bo'lsa (kecha ham, bugun ham faol bo'lmagan) 0 qaytaradi."""
    if not last_active:
        return 0
    last = datetime.fromisoformat(last_active).astimezone(TZ).date()
    return streak if last >= datetime.now(TZ).date() - timedelta(days=1) else 0


async def daily_done(tg_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT correct, total FROM daily_challenges WHERE tg_id=? AND day=?", (tg_id, today_str()))
        row = await cur.fetchone()
    return {"correct": row[0], "total": row[1]} if row else None


async def save_daily(tg_id: int, correct: int, total: int) -> bool:
    """Bugungi kunlik testni saqlaydi va bonus XP beradi. Ikkinchi marta saqlanmaydi."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO daily_challenges(tg_id, day, correct, total, ts) VALUES (?,?,?,?,?)",
                (tg_id, today_str(), correct, total, _iso(_now())))
        except aiosqlite.IntegrityError:
            return False
        await db.execute("UPDATE users SET xp=xp+? WHERE tg_id=?", (DAILY_BONUS_XP, tg_id))
        await db.commit()
    return True


async def toggle_reminders(tg_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET reminders_on = 1 - reminders_on WHERE tg_id=?", (tg_id,))
        cur = await db.execute("SELECT reminders_on FROM users WHERE tg_id=?", (tg_id,))
        row = await cur.fetchone()
        await db.commit()
    return bool(row and row[0])


async def get_reminder_targets() -> list[tuple[int, int]]:
    """Bugun hali faol bo'lmagan va eslatma yoqilgan foydalanuvchilar: [(tg_id, streak)].
    Uzoq vaqt faol bo'lmaganlarga (14 kundan ko'p) va hech qachon mashq qilmagan eski
    foydalanuvchilarga (3 kundan ko'p) qayta-qayta yozilmaydi."""
    today = datetime.now(TZ).date()
    out = []
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT tg_id, streak, last_active, created_at, last_reminder FROM users WHERE reminders_on=1")
        rows = await cur.fetchall()
    for tg_id, streak, last_active, created_at, last_reminder in rows:
        if last_reminder == today.isoformat():
            continue
        last = datetime.fromisoformat(last_active).astimezone(TZ).date() if last_active else None
        if last == today:
            continue
        if last is None:
            if (today - datetime.fromisoformat(created_at).astimezone(TZ).date()).days > 3:
                continue
        elif (today - last).days > 14:
            continue
        out.append((tg_id, _effective_streak(streak, last_active)))
    return out


async def mark_reminded(tg_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_reminder=? WHERE tg_id=?", (today_str(), tg_id))
        await db.commit()


async def disable_reminders(tg_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET reminders_on=0 WHERE tg_id=?", (tg_id,))
        await db.commit()


# ---------------- Sessiyalar (bot qayta ishga tushsa, imtihon/kunlik test yo'qolmasligi uchun) ----------------
async def save_session(tg_id: int, data: dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions(tg_id, data, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(tg_id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
            (tg_id, json.dumps(data), _iso(_now())))
        await db.commit()


async def delete_session(tg_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sessions WHERE tg_id=?", (tg_id,))
        await db.commit()


async def load_sessions(max_age_hours: int = 24) -> dict[int, dict]:
    """Eskirgan (24 soatdan oshgan) sessiyalarni o'chiradi va qolganlarini qaytaradi."""
    cutoff = _iso(_now() - timedelta(hours=max_age_hours))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sessions WHERE updated_at < ?", (cutoff,))
        await db.commit()
        cur = await db.execute("SELECT tg_id, data FROM sessions")
        rows = await cur.fetchall()
    return {tg_id: json.loads(data) for tg_id, data in rows}
