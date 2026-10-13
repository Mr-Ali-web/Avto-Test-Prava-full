# Pravaga Baza — Telegram bot

Haydovchilik guvohnomasi nazariy imtihoniga tayyorlovchi bot: mashq, imtihon (20 savol, 2 xato), kunlik 10 ta savol, streak va marafon mukofotlari, eslatmalar, profil, do'st taklif qilish, avtomaktab havolalari, premium va to'lov (Click/Payme yoki karta orqali).

## Papka tuzilmasi

| Fayl | Vazifasi |
|---|---|
| `bot.py` | Asosiy bot: mashq, imtihon, kunlik test, profil, eslatmalar |
| `payments.py` | Premium, Click/Payme, karta orqali to'lov, admin buyruqlari |
| `db.py` | SQLite baza (foydalanuvchilar, javoblar, to'lovlar, sessiyalar) |
| `config.py` | Barcha sozlamalar: limitlar, narxlar, mukofotlar, eslatma vaqti |
| `texts_uz.py` | Barcha matnlar (rus tilini qo'shish uchun shu faylni nusxalang) |
| `data/questions_all.json` | Savollar bazasi (bot shuni o'qiydi) |
| `data/review_sheet_all.csv` | Ustoz/mutaxassis tekshirishi uchun jadval |
| `tools/` | Savollar partiyasini qurish, birlashtirish va bazadan zaxira olish |
| `Dockerfile`, `docker-compose.yml` | Serverga joylash uchun |

## 1. Kompyuterda sinab ko'rish

```bash
cd pravaga_bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # keyin .env ni to'ldiring (BOT_TOKEN va ADMIN_IDS)
python3 bot.py
```

## 2. Serverga joylash (tavsiya etiladi: Docker)

Istalgan VPS yetadi (Ubuntu 22.04/24.04, 1 yadro, 1 GB xotira). Bot ishlab turishi uchun doim yoniq server kerak, aks holda kunlik eslatmalar ketmaydi.

```bash
# 1) Serverga ulaning
ssh root@SERVER_IP

# 2) Docker o'rnating
curl -fsSL https://get.docker.com | sh

# 3) Loyihani yuklang (o'z kompyuteringizdan):
#    scp -r pravaga_bot root@SERVER_IP:/opt/
cd /opt/pravaga_bot

# 4) Sozlamalarni kiriting
cp .env.example .env
nano .env                    # BOT_TOKEN, ADMIN_IDS, CARD_NUMBER... ni to'ldiring

# 5) Ishga tushiring
docker compose up -d --build

# 6) Tekshiring
docker compose logs -f       # "Savollar: ... ta" yozuvi chiqishi kerak (chiqish: Ctrl+C)
```

- **Yangilash:** yangi fayllarni `/opt/pravaga_bot` ga yuklang va `docker compose up -d --build` ni qayta bajaring. Baza `./storage` papkasida saqlanadi, yangilashda yo'qolmaydi. Davom etayotgan imtihonlar ham saqlanib qoladi.
- **To'xtatish:** `docker compose down`
- **Muhim:** bitta token bilan faqat BITTA nusxa ishlashi kerak (kompyuteringizda sinab bo'lgach, o'sha botni to'xtating).

### Docker'siz (systemd)

```bash
cd /opt/pravaga_bot && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env
cp deploy/pravaga-bot.service /etc/systemd/system/
useradd -r pravaga; chown -R pravaga /opt/pravaga_bot
systemctl enable --now pravaga-bot
journalctl -u pravaga-bot -f        # loglar
```

## 3. Zaxira nusxa (har kuni)

```bash
crontab -e
# quyidagi qatorni qo'shing (har kuni soat 03:00):
0 3 * * * cd /opt/pravaga_bot && python3 tools/backup_db.py
```
Docker bilan: `DB_PATH=/opt/pravaga_bot/storage/pravaga.db python3 tools/backup_db.py`. Oxirgi 14 ta nusxa `storage/backups/` da saqlanadi. Vaqti-vaqti bilan bitta nusxani boshqa joyga ham ko'chirib qo'ying.

## 4. BotFather sozlamalari

1. `/newbot` — bot yarating va tokenni `.env` ga qo'ying.
2. `/setdescription`, `/setuserpic`, `/setabouttext` — tavsif va rasm.
3. Click/Payme uchun: `/mybots` → botingiz → **Payments** → provayderni tanlab, tokenni `.env` dagi `PAYMENT_PROVIDER_TOKEN` ga qo'ying. Provayder bilan shartnoma kerak bo'lishi mumkin, shartlarini ulardan so'rang.
4. `/start` va `/help` buyruqlari menyusini bot o'zi o'rnatadi.

## 5. Admin buyruqlari (faqat `ADMIN_IDS` dagilar uchun)

- `/admin` — foydalanuvchilar, premium, to'lovlar statistikasi
- `/pending` — tekshiruv kutayotgan cheklar (✅ / ❌ tugmalari bilan)
- `/grant <telegram_id> <kun>` — qo'lda premium berish

Avtomaktab uchun havola: `https://t.me/<bot>?start=school_<kod>`. Yangi avtomaktab qo'shish `db.add_school("kod", "Nomi")` orqali (`bot.py` dagi `main()` ichida `demo` namunasi bor).

## 6. Savollar bazasini yangilash

1. `tools/build_questions_vN.py` yozing (`tools/build_questions_v1.py` ni namuna qiling), ishga tushiring.
2. `python3 tools/merge_questions.py` — hamma partiyalarni `data/questions_all.json` ga birlashtiradi va `review_sheet_all.csv` ni yangilaydi.
3. Botni qayta ishga tushiring.

Savol rasmi: savolga `"image": "fayl.png"` qo'shing va rasmni `data/images/` ga qo'ying.

## 7. Ishga tushirishdan oldingi ro'yxat

- [ ] `config.py`: narxlar (`PLANS`), limitlar, mukofotlar (`STREAK_REWARDS`) o'zingizga mosligini tekshiring
- [ ] `data/review_sheet_all.csv` ni avtomaktab ustozi/mutaxassisga tekshirtiring. Savollar hozircha `draft` holatida
- [ ] Tekshiruv tugagach `texts_uz.py` dagi "Beta" eslatmasini olib tashlang
- [ ] Karta orqali pul qabul qilish: soliq va ro'yxatdan o'tish masalasini buxgalter/bank bilan aniqlashtiring
- [ ] `.env` faylini hech kimga yubormang
- [ ] Zaxira nusxa (cron) sozlangan

## Muammolar

| Belgi | Yechim |
|---|---|
| `BOT_TOKEN topilmadi` | `.env` fayli bot.py yonida ekanini va tokenni to'g'ri yozganingizni tekshiring |
| `Conflict: terminated by other getUpdates` | Shu token bilan boshqa joyda ham bot ishlayapti, birini to'xtating |
| To'lov tugmalari chiqmayapti | `.env` da `CARD_NUMBER` yoki `PAYMENT_PROVIDER_TOKEN` bo'sh |
| Eslatmalar kelmayapti | Bot soat 19:00 (Toshkent) da ishlab turgan bo'lishi kerak |
# Avto-Test-Prava-full
