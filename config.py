import os

BASE_DIR_ = os.path.dirname(os.path.abspath(__file__))


def _load_env_file():
    """.env faylini (bo'lsa) o'qiydi: KEY=VALUE. Qo'shimcha kutubxona kerak emas."""
    path = os.path.join(BASE_DIR_, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env_file()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "pravaga.db"))
_ALL = os.path.join(BASE_DIR, "data", "questions_all.json")      # tools/merge_questions.py yaratadi
_V1 = os.path.join(BASE_DIR, "data", "questions_yhq_v1.json")
QUESTIONS_PATH = os.getenv("QUESTIONS_PATH", _ALL if os.path.exists(_ALL) else _V1)

IMAGES_DIR = os.getenv("IMAGES_DIR", os.path.join(BASE_DIR, "data", "images"))

# Imtihon qoidalari (rasmiy format: 20 savol, ko'pi bilan 2 xato)
EXAM_SIZE = 20
MAX_ERRORS = 2

# Biznes qoidalari - keyin real raqamlar bilan sozlanadi
FREE_EXAMS_PER_DAY = 1
REFERRAL_BONUS_DAYS = 3      # taklif qilgan ham, taklif qilingan ham oladi
REFERRAL_MIN_ANSWERS = 5     # do'sti kamida shuncha savol yechsa bonus beriladi
SCHOOL_BONUS_DAYS = 7        # avtomaktab havolasi orqali kirganlarga
XP_PER_CORRECT = 10


# ---------------- Limitlar va premium ----------------
TZ_OFFSET_HOURS = 5            # Toshkent vaqti (kunlik limitlar 00:00 da yangilanadi)
FREE_PRACTICE_PER_DAY = 15     # bepul foydalanuvchi uchun kunlik mashq savollari

# NAMUNA NARXLAR (so'mda) - o'zingiz belgilang!
PLANS = {
    "w1": {"title": "1 hafta", "days": 7, "price": 10000},
    "m1": {"title": "1 oy", "days": 30, "price": 29000},
    "m3": {"title": "3 oy", "days": 90, "price": 59000},
}

# ---------------- To'lov va admin (maxfiy qiymatlar .env da) ----------------
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")  # BotFather > Payments (Click/Payme)
CARD_NUMBER = os.getenv("CARD_NUMBER", "")                        # karta orqali o'tkazma uchun
CARD_OWNER = os.getenv("CARD_OWNER", "")


# ---------------- Kunlik 10 ta savol, marafon va eslatmalar ----------------
DAILY_CHALLENGE_SIZE = 10
DAILY_BONUS_XP = 50
REMINDER_HOUR = 19                       # Toshkent vaqti bilan soat nechada eslatma yuboriladi
STREAK_REWARDS = {3: 1, 7: 2, 14: 3, 30: 7}   # streak kuni: bonus premium kunlari (marafon mukofoti)
