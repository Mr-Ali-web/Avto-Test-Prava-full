"""Premium va to'lovlar.

Ikki to'lov usuli:
1) Click/Payme - Telegram Payments orqali (PAYMENT_PROVIDER_TOKEN bo'lsa yoqiladi)
2) Karta orqali o'tkazma - foydalanuvchi chek yuboradi, admin tasdiqlaydi (CARD_NUMBER bo'lsa yoqiladi)
"""
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, LabeledPrice, Message,
                           PreCheckoutQuery)

import db
from config import (ADMIN_IDS, CARD_NUMBER, CARD_OWNER, FREE_EXAMS_PER_DAY,
                    FREE_PRACTICE_PER_DAY, PAYMENT_PROVIDER_TOKEN, PLANS)
from texts_uz import T

router = Router()


def money(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " so'm"


def premium_cta_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=T["btn_get_premium"], callback_data="premium")]])


def plans_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"{p['title']} — {money(p['price'])}", callback_data=f"plan:{k}")]
            for k, p in PLANS.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_kb(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"apr:{pid}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"rej:{pid}"),
    ]])


# ---------------- Foydalanuvchi qismi ----------------
async def show_premium(msg: Message, uid: int):
    until = await db.premium_until_str(uid)
    status = T["premium_active"].format(date=until) if until else T["premium_inactive"]
    await msg.answer(
        T["premium_screen"].format(status=status, free_practice=FREE_PRACTICE_PER_DAY,
                                   free_exams=FREE_EXAMS_PER_DAY),
        reply_markup=plans_kb())


@router.message(F.text == T["btn_premium"])
async def premium_msg(m: Message):
    await db.register(m.from_user.id, m.from_user.full_name)
    await show_premium(m, m.from_user.id)


@router.callback_query(F.data == "premium")
async def premium_cb(cb: CallbackQuery):
    await show_premium(cb.message, cb.from_user.id)
    await cb.answer()


@router.callback_query(F.data.startswith("plan:"))
async def choose_plan(cb: CallbackQuery):
    plan = cb.data.split(":")[1]
    if plan not in PLANS:
        return await cb.answer()
    rows = []
    if PAYMENT_PROVIDER_TOKEN:
        rows.append([InlineKeyboardButton(text=T["btn_pay_invoice"], callback_data=f"pay:invoice:{plan}")])
    if CARD_NUMBER:
        rows.append([InlineKeyboardButton(text=T["btn_pay_card"], callback_data=f"pay:card:{plan}")])
    if not rows:
        await cb.message.answer(T["pay_unavailable"])
    else:
        await cb.message.answer(T["choose_method"], reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await cb.answer()


@router.callback_query(F.data.startswith("pay:"))
async def pay(cb: CallbackQuery):
    _, method, plan = cb.data.split(":")
    if plan not in PLANS:
        return await cb.answer()
    p, uid = PLANS[plan], cb.from_user.id
    if method == "invoice" and PAYMENT_PROVIDER_TOKEN:
        await cb.bot.send_invoice(
            chat_id=uid,
            title=T["invoice_title"].format(title=p["title"]),
            description=T["invoice_desc"].format(days=p["days"]),
            payload=f"plan:{plan}",
            provider_token=PAYMENT_PROVIDER_TOKEN,
            currency="UZS",
            prices=[LabeledPrice(label=p["title"], amount=p["price"] * 100)],  # tiyinda
        )
    elif method == "card" and CARD_NUMBER:
        pid = await db.create_payment(uid, plan, p["price"], "card")
        await cb.message.answer(T["card_instruction"].format(
            title=p["title"], amount=money(p["price"]), card=CARD_NUMBER,
            owner=CARD_OWNER or "-", pid=pid))
    else:
        await cb.message.answer(T["pay_unavailable"])
    await cb.answer()


# ---------------- Chek yuborish (karta orqali) ----------------
async def send_proof(bot: Bot, chat_id: int, proof: str, caption: str, kb: InlineKeyboardMarkup):
    kind, file_id = proof.split(":", 1)
    if kind == "d":
        await bot.send_document(chat_id, file_id, caption=caption, reply_markup=kb)
    else:
        await bot.send_photo(chat_id, file_id, caption=caption, reply_markup=kb)


def admin_caption(pay: dict, name: str | None = None) -> str:
    plan = PLANS.get(pay["plan"], {"title": pay["plan"]})
    who = f"{name} ({pay['tg_id']})" if name else str(pay["tg_id"])
    return (f"💳 To'lov #{pay['id']}\nFoydalanuvchi: {who}\n"
            f"Tarif: {plan['title']}\nSumma: {money(pay['amount'])}\n\n"
            f"Bank ilovasida summa va izohni tekshirib, keyin tasdiqlang.")


@router.message(F.photo | F.document)
async def on_proof(m: Message):
    uid = m.from_user.id
    pay_row = await db.latest_open_payment(uid)
    if not pay_row:
        return  # chek kutilmayapti
    if not ADMIN_IDS:
        return await m.answer(T["proof_no_admin"])
    proof = f"p:{m.photo[-1].file_id}" if m.photo else f"d:{m.document.file_id}"
    await db.attach_proof(pay_row["id"], proof)
    caption, kb = admin_caption(pay_row, m.from_user.full_name), admin_kb(pay_row["id"])
    for admin in ADMIN_IDS:
        try:
            await send_proof(m.bot, admin, proof, caption, kb)
        except Exception:
            logging.exception("Adminga chek yuborib bo'lmadi: %s", admin)
    await m.answer(T["proof_received"])


@router.callback_query(F.data.startswith(("apr:", "rej:")))
async def on_decision(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        return await cb.answer("Ruxsat yo'q", show_alert=True)
    action, pid = cb.data.split(":")
    approve = action == "apr"
    pay_row = await db.decide_payment(int(pid), approve, cb.from_user.id)
    if not pay_row:
        return await cb.answer("Bu to'lov allaqachon ko'rib chiqilgan", show_alert=True)

    verdict = "✅ TASDIQLANDI" if approve else "❌ RAD ETILDI"
    try:
        await cb.message.edit_caption(
            caption=f"{cb.message.caption or ''}\n\n{verdict} ({cb.from_user.full_name})")
    except Exception:
        logging.exception("Admin xabarini tahrirlab bo'lmadi")
    try:
        if approve:
            until = await db.premium_until_str(pay_row["tg_id"])
            await cb.bot.send_message(pay_row["tg_id"], T["pay_approved"].format(date=until))
        else:
            await cb.bot.send_message(pay_row["tg_id"], T["pay_rejected"])
    except Exception:
        logging.exception("Foydalanuvchiga xabar yuborib bo'lmadi")
    await cb.answer()


# ---------------- Click/Payme (Telegram Payments) ----------------
@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)


@router.message(F.successful_payment)
async def on_paid(m: Message):
    sp = m.successful_payment
    plan = sp.invoice_payload.split(":", 1)[1] if sp.invoice_payload.startswith("plan:") else None
    if plan not in PLANS:
        logging.error("Noma'lum reja bilan to'lov: %s", sp.invoice_payload)
        return
    charge = sp.provider_payment_charge_id or sp.telegram_payment_charge_id
    if await db.record_invoice_payment(m.from_user.id, plan, sp.total_amount // 100, charge):
        until = await db.premium_until_str(m.from_user.id)
        await m.answer(T["pay_approved"].format(date=until))


# ---------------- Admin buyruqlari ----------------
@router.message(Command("pending"))
async def cmd_pending(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    rows = await db.list_pending()
    if not rows:
        return await m.answer("Kutilayotgan to'lovlar yo'q.")
    for pay_row in rows:
        await send_proof(m.bot, m.from_user.id, pay_row["proof_file_id"],
                         admin_caption(pay_row), admin_kb(pay_row["id"]))


@router.message(Command("grant"))
async def cmd_grant(m: Message, command: CommandObject):
    if m.from_user.id not in ADMIN_IDS:
        return
    parts = (command.args or "").split()
    if len(parts) != 2 or not all(x.isdigit() for x in parts):
        return await m.answer("Format: /grant <telegram_id> <kunlar>")
    ok = await db.grant_days_admin(int(parts[0]), int(parts[1]))
    await m.answer("✅ Premium berildi." if ok else "Bunday foydalanuvchi topilmadi.")


@router.message(Command("admin"))
async def cmd_admin(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    s = await db.admin_stats()
    await m.answer(
        f"📈 Statistika\n\nFoydalanuvchilar: {s['users']}\nPremium faol: {s['premium']}\n"
        f"To'lovlar: {s['paid_count']} ta, jami {money(s['paid_sum'])}\n"
        f"Tekshiruv kutayotgan: {s['pending']}\n\n"
        f"Buyruqlar: /pending, /grant <id> <kun>")
