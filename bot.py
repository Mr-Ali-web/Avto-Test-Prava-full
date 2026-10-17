import asyncio
import json
import logging
import os
import random
from datetime import datetime
from urllib.parse import quote, urlencode

from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (BotCommand, CallbackQuery, ErrorEvent, FSInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, Message,
                           ReplyKeyboardMarkup)

import db
import payments
from payments import premium_cta_kb
from config import (BOT_TOKEN, DAILY_BONUS_XP, DAILY_CHALLENGE_SIZE, EXAM_SIZE,
                    FREE_EXAMS_PER_DAY, FREE_PRACTICE_PER_DAY, IMAGES_DIR,
                    MAX_ERRORS, QUESTIONS_PATH, REFERRAL_BONUS_DAYS,
                    REFERRAL_MIN_ANSWERS, REMINDER_HOUR, SCHOOL_BONUS_DAYS,
                    STREAK_REWARDS, XP_PER_CORRECT)
from texts_uz import T

router = Router()

with open(QUESTIONS_PATH, encoding="utf-8") as f:
    QUESTIONS = {q["id"]: q for q in json.load(f)}

# Vaqtinchalik sessiyalar (xotirada). Production'da DB yoki Redis'ga ko'chiriladi.
SESSIONS: dict[int, dict] = {}
# Rasm Telegram'ga bir marta yuklanadi, keyin file_id orqali tez yuboriladi.
FILE_IDS: dict[int, str] = {}
LETTERS = "ABCDEFGH"
_BOT_USERNAME: str | None = None


async def set_session(uid: int, s: dict) -> None:
    SESSIONS[uid] = s
    await touch_session(uid)


async def touch_session(uid: int) -> None:
    """Imtihon va kunlik test sessiyalari bazaga yoziladi (restartdan keyin davom etadi)."""
    s = SESSIONS.get(uid)
    if s and s["mode"] in ("exam", "daily"):
        await db.save_session(uid, s)


async def end_session(uid: int) -> dict | None:
    s = SESSIONS.pop(uid, None)
    await db.delete_session(uid)
    return s


# ---------------- Yordamchilar ----------------
async def practice_left(uid: int) -> int | None:
    """None - cheklov yo'q (premium). Aks holda bugun qolgan mashq savollari soni."""
    if await db.is_premium(uid):
        return None
    return max(0, FREE_PRACTICE_PER_DAY - await db.practice_today(uid))


def practice_header(q: dict, left: int | None) -> str:
    header = T["practice_header"].format(num=q["id"])
    return header if left is None else header + T["practice_left"].format(left=left)


def menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=T["btn_practice"]), KeyboardButton(text=T["btn_exam"])],
            [KeyboardButton(text=T["btn_daily"]), KeyboardButton(text=T["btn_profile"])],
            [KeyboardButton(text=T["btn_invite"]), KeyboardButton(text=T["btn_premium"])],
        ],
        resize_keyboard=True,
    )


def build_question(q: dict, header: str) -> tuple[str, InlineKeyboardMarkup]:
    """Variantlar har safar aralashtiriladi. Variant matnlari xabarda (uzun bo'lsa ham to'liq
    ko'rinadi), tugmalarda esa faqat A/B/C/D harflari bo'ladi; callback'da asl indeks yuboriladi."""
    order = list(range(len(q["options"])))
    random.shuffle(order)
    lines = [f"{LETTERS[pos]}. {q['options'][orig]}" for pos, orig in enumerate(order)]
    text = f"{question_text(q, header)}\n\n" + "\n".join(lines)
    row = [InlineKeyboardButton(text=LETTERS[pos], callback_data=f"a:{q['id']}:{orig}")
           for pos, orig in enumerate(order)]
    return text, InlineKeyboardMarkup(inline_keyboard=[row])


def question_text(q: dict, header: str) -> str:
    return f"{header}\n[{q['topic']}]\n\n{q['text']}"


def image_path(q: dict) -> str | None:
    name = q.get("image")
    if not name:
        return None
    path = os.path.join(IMAGES_DIR, name)
    return path if os.path.exists(path) else None


async def send_question(msg: Message, q: dict, header: str):
    text, kb = build_question(q, header)
    path = image_path(q)
    if path:
        photo = FILE_IDS.get(q["id"]) or FSInputFile(path)
        if len(text) <= 1000:  # Telegram caption limiti 1024 belgi
            sent = await msg.answer_photo(photo, caption=text, reply_markup=kb)
        else:
            sent = await msg.answer_photo(photo)
            await msg.answer(text, reply_markup=kb)
        FILE_IDS[q["id"]] = sent.photo[-1].file_id
    else:
        await msg.answer(text, reply_markup=kb)


async def edit_message(msg: Message, text: str, kb: InlineKeyboardMarkup | None = None):
    """Rasmli xabarda caption, oddiy xabarda text tahrirlanadi."""
    if msg.photo:
        if len(text) > 1000:  # caption sig'masa, qolgan qismi alohida xabarda
            await msg.edit_caption(caption=text[:1000], reply_markup=None)
            await msg.answer(text[1000:], reply_markup=kb)
        else:
            await msg.edit_caption(caption=text, reply_markup=kb)
    else:
        await msg.edit_text(text, reply_markup=kb)


def result_text(q: dict, choice: int) -> str:
    if choice == q["answer"]:
        text = T["correct"].format(xp=XP_PER_CORRECT)
    else:
        text = T["wrong"].format(chosen=q["options"][choice], answer=q["options"][q["answer"]])
    if q.get("explain"):
        text += T["explain"].format(text=q["explain"])
    if q.get("source"):
        text += T["source_line"].format(source=q["source"])
    return text


async def bot_username(bot: Bot) -> str:
    global _BOT_USERNAME
    if not _BOT_USERNAME:
        _BOT_USERNAME = (await bot.get_me()).username
    return _BOT_USERNAME


async def share_button(bot: Bot, uid: int, template: str, **fmt) -> InlineKeyboardButton:
    """Telegram'ning ulashish oynasini ochadigan tugma. Havolada foydalanuvchining
    shaxsiy taklif kodi bor, shuning uchun ulashgan do'stlar referral bonus beradi."""
    username = await bot_username(bot)
    text = template.format(bot=f"@{username}", **fmt)
    link = f"https://t.me/{username}?start=ref_{uid}"
    url = "https://t.me/share/url?" + urlencode({"url": link, "text": text}, quote_via=quote)
    return InlineKeyboardButton(text=T["btn_share"], url=url)


async def reward_referrer(bot: Bot, uid: int, referrer: int | None):
    if not referrer:
        return
    try:
        await bot.send_message(uid, T["ref_reward_self"].format(days=REFERRAL_BONUS_DAYS))
        await bot.send_message(referrer, T["ref_reward"].format(days=REFERRAL_BONUS_DAYS))
    except Exception:  # foydalanuvchi botni bloklagan bo'lishi mumkin
        logging.exception("Referral xabarini yuborib bo'lmadi")


async def notify_streak(bot: Bot, uid: int, reward: tuple | None):
    if not reward:
        return
    streak, days = reward
    try:
        await bot.send_message(uid, T["streak_reward"].format(streak=streak, days=days))
    except Exception:
        logging.exception("Marafon mukofoti xabarini yuborib bo'lmadi")


# ---------------- /start va menyu ----------------
@router.message(CommandStart())
async def start(m: Message, command: CommandObject):
    arg = command.args or ""
    ref_by = int(arg[4:]) if arg.startswith("ref_") and arg[4:].isdigit() else None
    school_code = arg[7:] if arg.startswith("school_") else None

    res = await db.register(m.from_user.id, m.from_user.full_name, ref_by, school_code)
    await m.answer(T["welcome"].format(name=m.from_user.first_name), reply_markup=menu_kb())
    if res["school"]:
        await m.answer(T["school_welcome"].format(school=res["school"], days=SCHOOL_BONUS_DAYS))


@router.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(T["help"], reply_markup=menu_kb())


# ---------------- Mashq ----------------
@router.message(F.text == T["btn_practice"])
async def practice(m: Message):
    if not QUESTIONS:
        return await m.answer(T["no_questions"])
    uid = m.from_user.id
    left = await practice_left(uid)
    if left == 0:
        return await m.answer(T["limit_reached"].format(limit=FREE_PRACTICE_PER_DAY),
                              reply_markup=premium_cta_kb())
    await set_session(uid, {"mode": "practice"})
    q = random.choice(list(QUESTIONS.values()))
    await send_question(m, q, practice_header(q, left))


@router.callback_query(F.data == "next")
async def on_next(cb: CallbackQuery):
    left = await practice_left(cb.from_user.id)
    if left == 0:
        await cb.message.answer(T["limit_reached"].format(limit=FREE_PRACTICE_PER_DAY),
                                reply_markup=premium_cta_kb())
        return await cb.answer()
    q = random.choice(list(QUESTIONS.values()))
    await send_question(cb.message, q, practice_header(q, left))
    await cb.answer()


# ---------------- Imtihon ----------------
@router.message(F.text == T["btn_exam"])
async def exam(m: Message):
    uid = m.from_user.id
    if not QUESTIONS:
        return await m.answer(T["no_questions"])
    if not await db.is_premium(uid) and await db.exams_today(uid) >= FREE_EXAMS_PER_DAY:
        return await m.answer(T["exam_locked"], reply_markup=premium_cta_kb())

    ids = random.sample(list(QUESTIONS), min(EXAM_SIZE, len(QUESTIONS)))
    exam_id = await db.start_exam(uid)
    await set_session(uid, {"mode": "exam", "ids": ids, "i": 0, "errors": 0, "exam_id": exam_id})
    await send_exam_question(m, uid)


def exam_header(s: dict, q: dict) -> str:
    return T["exam_header"].format(i=s["i"] + 1, n=len(s["ids"]), num=q["id"])


async def send_exam_question(msg: Message, uid: int):
    s = SESSIONS[uid]
    q = QUESTIONS[s["ids"][s["i"]]]
    await send_question(msg, q, exam_header(s, q))


async def finish_exam(msg: Message, uid: int):
    s = await end_session(uid)
    total, errors = len(s["ids"]), s["errors"]
    passed = errors <= MAX_ERRORS
    await db.finish_exam(s["exam_id"], errors, passed)
    if not passed:
        return await msg.answer(T["exam_fail"].format(errors=errors, max_errors=MAX_ERRORS))
    score = total - errors
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [await share_button(msg.bot, uid, T["share_exam"], score=score, total=total)]])
    await msg.answer(
        T["exam_pass"].format(score=score, total=total, errors=errors, max_errors=MAX_ERRORS),
        reply_markup=kb)


# ---------------- Kunlik 10 ta savol (marafon) ----------------
def daily_ids() -> list[int]:
    """Bugungi kunlik savollar: hamma foydalanuvchi uchun bir xil (sana bo'yicha tanlanadi)."""
    rnd = random.Random(db.today_str())
    return rnd.sample(sorted(QUESTIONS), min(DAILY_CHALLENGE_SIZE, len(QUESTIONS)))


def daily_header(s: dict, q: dict) -> str:
    return T["daily_header"].format(i=s["i"] + 1, n=len(s["ids"]), num=q["id"])


async def send_daily_question(msg: Message, uid: int):
    s = SESSIONS[uid]
    if s.get("sent_i") == s["i"]:  # qayta bosilganda dublikat yuborilmasin
        return
    s["sent_i"] = s["i"]
    await touch_session(uid)
    q = QUESTIONS[s["ids"][s["i"]]]
    await send_question(msg, q, daily_header(s, q))


async def start_daily(msg: Message, uid: int, name: str):
    if not QUESTIONS:
        return await msg.answer(T["no_questions"])
    await db.register(uid, name)
    done = await db.daily_done(uid)
    if done:
        kb = InlineKeyboardMarkup(inline_keyboard=[[await share_button(
            msg.bot, uid, T["share_daily"], correct=done["correct"], total=done["total"])]])
        return await msg.answer(
            T["daily_already"].format(correct=done["correct"], total=done["total"]), reply_markup=kb)
    await set_session(uid, {"mode": "daily", "ids": daily_ids(), "i": 0, "correct": 0})
    await send_daily_question(msg, uid)


async def finish_daily(msg: Message, uid: int):
    s = await end_session(uid)
    if not s:
        return
    correct, total = s["correct"], len(s["ids"])
    await db.save_daily(uid, correct, total)
    p = await db.get_profile(uid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [await share_button(msg.bot, uid, T["share_daily"], correct=correct, total=total)]])
    await msg.answer(
        T["daily_done"].format(correct=correct, total=total, xp=DAILY_BONUS_XP, streak=p["streak"]),
        reply_markup=kb)


@router.message(F.text == T["btn_daily"])
async def daily_msg(m: Message):
    await start_daily(m, m.from_user.id, m.from_user.full_name)


@router.callback_query(F.data == "daily_start")
async def daily_cb(cb: CallbackQuery):
    await start_daily(cb.message, cb.from_user.id, cb.from_user.full_name)
    await cb.answer()


@router.callback_query(F.data == "dnext")
async def on_daily_next(cb: CallbackQuery):
    uid = cb.from_user.id
    s = SESSIONS.get(uid)
    if not s or s.get("mode") != "daily":
        return await cb.answer()
    if s["i"] >= len(s["ids"]):
        await finish_daily(cb.message, uid)
    else:
        await send_daily_question(cb.message, uid)
    await cb.answer()


# ---------------- Javob qabul qilish (mashq / imtihon / kunlik) ----------------
@router.callback_query(F.data.startswith("a:"))
async def on_answer(cb: CallbackQuery):
    uid = cb.from_user.id
    _, qid, choice = cb.data.split(":")
    q = QUESTIONS.get(int(qid))
    if not q:
        return await cb.answer()
    choice = int(choice)
    s = SESSIONS.get(uid, {"mode": "practice"})
    mode = s["mode"]

    # Eski/qayta bosilgan tugmalardan himoya: faqat joriy savolga javob olinadi
    if mode == "exam":
        if s["ids"][s["i"]] != q["id"]:
            return await cb.answer()
        header = exam_header(s, q)
    elif mode == "daily":
        if s["i"] >= len(s["ids"]) or s["ids"][s["i"]] != q["id"]:
            return await cb.answer()
        header = daily_header(s, q)
    else:
        mode, header = "practice", None

    correct = choice == q["answer"]
    res = await db.record_answer(uid, q["id"], q["topic"], correct, mode=mode)
    await reward_referrer(cb.bot, uid, res["referrer"])
    await notify_streak(cb.bot, uid, res["streak_reward"])

    if mode == "practice":
        header = practice_header(q, await practice_left(uid))
    body = f"{question_text(q, header)}\n\n{result_text(q, choice)}"

    if mode == "exam":
        await edit_message(cb.message, body)  # tugmalar olib tashlanadi
        if not correct:
            s["errors"] += 1
        s["i"] += 1
        await touch_session(uid)
        if s["errors"] > MAX_ERRORS or s["i"] >= len(s["ids"]):
            await finish_exam(cb.message, uid)
        else:
            await send_exam_question(cb.message, uid)
        return await cb.answer()

    if mode == "daily":
        s["i"] += 1
        s["correct"] += int(correct)
        await touch_session(uid)
        label = T["btn_finish_daily"] if s["i"] >= len(s["ids"]) else T["btn_next"]
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, callback_data="dnext")]])
        await edit_message(cb.message, body, kb)
        return await cb.answer()

    next_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=T["btn_next"], callback_data="next")]])
    await edit_message(cb.message, body, next_kb)
    await cb.answer()


# ---------------- Profil ----------------
def marathon_line(streak: int) -> str:
    upcoming = [k for k in sorted(STREAK_REWARDS) if k > streak]
    if not upcoming:
        return T["marathon_all"]
    k = upcoming[0]
    return T["marathon_next"].format(k=k, days=STREAK_REWARDS[k], left=k - streak)


def profile_text(p: dict) -> str:
    level, into = p["xp"] // 100 + 1, p["xp"] % 100
    bar = "▓" * (into // 10) + "░" * (10 - into // 10)
    pct = round(p["correct"] * 100 / p["total"]) if p["total"] else 0
    daily = (T["daily_status_done"].format(**p["daily"]) if p.get("daily")
             else T["daily_status_todo"])
    return T["profile"].format(
        name=p["name"], level=level, xp=p["xp"], bar=bar, to_next=100 - into,
        streak=p["streak"], marathon=marathon_line(p["streak"]), daily=daily,
        correct=p["correct"], total=p["total"], pct=pct,
        passed=p["passed"], exams=p["exams"], invited=p["invited"],
        school=T["profile_school"].format(school=p["school"]) if p["school"] else "",
        premium=p["premium"] or T["no_premium"],
        weak=T["weak_topic"].format(topic=p["weak_topic"]) if p["weak_topic"] else "",
    )


def topics_text(rows: list) -> str:
    if not rows:
        return T["topics_empty"]
    lines = []
    for topic, total, correct in rows:
        pct = round(correct * 100 / total)
        mark = "🟢" if pct >= 80 else "🟡" if pct >= 50 else "🔴"
        lines.append(f"{mark} {topic}: {pct}% ({correct}/{total})")
    return T["topics_title"] + "\n".join(lines)


def profile_kb(reminders_on: bool = True) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T["btn_topics"], callback_data="topics")],
        [InlineKeyboardButton(text=T["btn_invite_inline"], callback_data="invite")],
        [InlineKeyboardButton(text=T["btn_get_premium"], callback_data="premium")],
        [InlineKeyboardButton(text=T["btn_remind_on"] if reminders_on else T["btn_remind_off"],
                              callback_data="toggle_remind")],
    ])


@router.message(F.text.in_({T["btn_profile"], "📊 Statistika"}))
async def profile(m: Message):
    await db.register(m.from_user.id, m.from_user.full_name)  # allaqachon bo'lsa, hech narsa qilmaydi
    p = await db.get_profile(m.from_user.id)
    await m.answer(profile_text(p), reply_markup=profile_kb(p["reminders_on"]))


@router.callback_query(F.data == "toggle_remind")
async def on_toggle_remind(cb: CallbackQuery):
    on = await db.toggle_reminders(cb.from_user.id)
    p = await db.get_profile(cb.from_user.id)
    try:
        await edit_message(cb.message, profile_text(p), profile_kb(on))
    except Exception:
        logging.exception("Profilni yangilab bo'lmadi")
    await cb.answer(T["remind_toggled_on"] if on else T["remind_toggled_off"])


@router.callback_query(F.data == "topics")
async def on_topics(cb: CallbackQuery):
    await cb.message.answer(topics_text(await db.get_topic_stats(cb.from_user.id)))
    await cb.answer()


async def send_invite(msg: Message, user_id: int):
    username = await bot_username(msg.bot)
    link = f"https://t.me/{username}?start=ref_{user_id}"
    await msg.answer(T["invite"].format(
        min_answers=REFERRAL_MIN_ANSWERS, days=REFERRAL_BONUS_DAYS, link=link))


@router.message(F.text == T["btn_invite"])
async def invite(m: Message):
    await send_invite(m, m.from_user.id)


@router.callback_query(F.data == "invite")
async def on_invite(cb: CallbackQuery):
    await send_invite(cb.message, cb.from_user.id)
    await cb.answer()


# ---------------- Kunlik eslatmalar ----------------
async def send_reminders(bot: Bot) -> int:
    """Bugun hali faol bo'lmagan foydalanuvchilarga bitta eslatma yuboradi. Yuborilganlar soni."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T["btn_start_daily"], callback_data="daily_start")]])
    sent = 0
    for uid, streak in await db.get_reminder_targets():
        text = T["remind_streak"].format(streak=streak) if streak >= 1 else T["remind_plain"]
        try:
            await bot.send_message(uid, text, reply_markup=kb)
            await db.mark_reminded(uid)
            sent += 1
        except TelegramForbiddenError:  # foydalanuvchi botni bloklagan
            await db.disable_reminders(uid)
        except Exception:
            logging.exception("Eslatma yuborib bo'lmadi: %s", uid)
        await asyncio.sleep(0.05)  # Telegram limitlari uchun
    return sent


async def reminder_loop(bot: Bot):
    """Har daqiqa tekshiradi; Toshkent vaqti bilan REMINDER_HOUR da eslatmalarni yuboradi.
    Bir foydalanuvchiga kuniga bir martadan ortiq yuborilmaydi (bazada belgilanadi)."""
    last_run = None
    while True:
        try:
            now = datetime.now(db.TZ)
            if now.hour == REMINDER_HOUR and last_run != now.date():
                last_run = now.date()
                logging.info("Eslatmalar yuborildi: %s ta", await send_reminders(bot))
        except Exception:
            logging.exception("Eslatma tsiklida xato")
        await asyncio.sleep(60)


async def on_error(event: ErrorEvent):
    """Kutilmagan xatolar botni to'xtatib qo'ymasligi uchun: yozib qo'yiladi, bot ishlashda davom etadi."""
    logging.error("Kutilmagan xato", exc_info=event.exception)
    return True


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi. .env yoki muhit o'zgaruvchisiga qo'ying.")
    await db.init()
    await db.add_school("demo", "Demo avtomaktab")  # test uchun: t.me/<bot>?start=school_demo
    SESSIONS.update(await db.load_sessions())
    logging.info("Savollar: %s ta | tiklangan sessiyalar: %s ta", len(QUESTIONS), len(SESSIONS))
    bot = Bot(BOT_TOKEN)
    await bot.set_my_commands([BotCommand(command="start", description="Botni boshlash / menyuni yangilash"),
                               BotCommand(command="help", description="Yordam")])
    dp = Dispatcher()
    dp.errors.register(on_error)
    dp.include_router(payments.router)
    dp.include_router(router)
    reminders = asyncio.create_task(reminder_loop(bot))
    try:
        await dp.start_polling(bot)
    finally:
        reminders.cancel()


if __name__ == "__main__":
    asyncio.run(main())
