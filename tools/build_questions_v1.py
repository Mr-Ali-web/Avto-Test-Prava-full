"""YHQ asosidagi original savollar bazasi (1-partiya).

Manba: O'zbekiston Respublikasi Vazirlar Mahkamasining 12.04.2022 dagi 172-son qarori bilan
tasdiqlangan Yo'l harakati qoidalari (lex.uz/acts/-5953883), 2026-03-30 tahririgacha.
Bu partiya Qoidalarning 1-13 boblarini (6-90-bandlar) qamrab oladi.

Ishga tushirish:  python3 tools/build_questions_v1.py
Natija: data/questions_yhq_v1.json (bot uchun) va data/review_sheet_v1.csv (ustoz uchun)
"""
import csv
import json
import os
import random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "YHQ"  # manba nomi; band raqami har savolda alohida

# Mavzular
UM = "Umumiy qoidalar va hujjatlar"
HM = "Haydovchining majburiyatlari va taqiqlari"
YTH = "Yo'l-transport hodisasi"
PI = "Piyodalar"
YOL = "Yo'lovchilar"
MX = "Maxsus transport vositalari"
SV = "Svetofor va tartibga soluvchi ishoralari"
OG = "Ogohlantiruvchi va avariya ishoralari"
MN = "Manyovr qilish"
JL = "Transport vositalarining joylashuvi"
TZ = "Harakatlanish tezligi"
QO = "Quvib o'tish"
TX = "To'xtash va to'xtab turish"
AT = "Asosiy atamalar"
IH = "Individual harakatlanish vositalari"

# (mavzu, savol, to'g'ri javob, [noto'g'ri javoblar], band, tushuntirish)
D = [
    # --- Umumiy qoidalar va hujjatlar ---
    (UM, "Transport vositasi egasining fuqarolik javobgarligini majburiy sug'urta qilish polisi qanday ko'rinishda bo'lishi mumkin?",
     "Elektron ko'rinishda ham", ["Faqat qog'oz ko'rinishida", "Faqat sug'urta kompaniyasi ofisida saqlanadi"], "7", ""),
    (UM, "DYHXX xodimlari planshet orqali quyidagilardan qaysi birini tekshiradi?",
     "Transport vositasining texnik ko'rikdan o'tganligi to'g'risidagi ma'lumotni",
     ["Haydovchining oilaviy ahvolini", "Avtomaktab bitiruv diplomini", "Haydovchining ish haqi haqidagi ma'lumotni"], "7", ""),
    (UM, "Haydovchining yonida biometrik pasport yoki ID-karta bo'lsa, uning haydovchilik guvohnomasi va transport vositasi hujjatlari qanday tekshiriladi?",
     "Planshet orqali tekshiriladi", ["Umuman tekshirilmaydi", "Faqat qog'oz nusxalari bo'yicha tekshiriladi"], "7",
     "Planshetda aniqlash imkoni bo'lmagan va favqulodda holatlar bundan mustasno."),
    (UM, "«B» toifasi ruxsat etilgan to'liq vazni qancha kilogrammdan oshmaydigan avtotransport vositalarini boshqarish huquqini beradi?",
     "3 500 kg", ["2 500 kg", "4 500 kg", "7 500 kg"], "8", ""),
    (UM, "«C» toifasi ruxsat etilgan to'liq vazni qancha kilogrammdan ortiq bo'lgan avtotransport vositalarini boshqarish huquqini beradi?",
     "3 500 kg", ["2 500 kg", "4 500 kg", "7 500 kg"], "8", ""),
    (UM, "«D» toifasi qanday transport vositalarini boshqarish huquqini beradi?",
     "Yo'lovchi tashishga mo'ljallangan, haydovchi o'rindig'idan tashqari o'rindiqlar soni sakkiztadan ortiq bo'lgan avtotransport vositalarini",
     ["Ruxsat etilgan to'liq vazni 3 500 kg gacha bo'lgan yuk avtomobillarini", "Faqat mototsikllarni"], "8", ""),
    (UM, "«A» toifasi qaysi transport vositalarini boshqarish huquqini beradi?",
     "Mototsikllar va elektromototsikllarni",
     ["Faqat velosipedlarni", "Ruxsat etilgan to'liq vazni 3 500 kg gacha bo'lgan avtomobillarni", "Yo'lovchi tashiydigan avtobuslarni"], "8", ""),
    (UM, "Xavfsizlik kamari nazarda tutilgan transport vositasida haydovchi va old o'rindiqdagi yo'lovchilar kamarni qachon taqib olishlari shart?",
     "Harakatni boshlashdan oldin", ["Aholi punktidan chiqqandan keyin", "Tezlik soatiga 60 km dan oshganda", "Faqat tungi vaqtda"], "9", ""),
    (UM, "Mototsikl, moped va skuterda harakatlanayotgan haydovchi hamda yo'lovchilar nima qilishlari shart?",
     "Maxsus motoshlem kiyib, uni qadab olishlari shart",
     ["Faqat shahar tashqarisida motoshlem kiyishlari", "Motoshlem tavsiya etiladi, lekin majburiy emas"], "9", ""),

    # --- Haydovchining majburiyatlari va taqiqlari ---
    (HM, "Haydovchi yo'lga chiqishdan oldin nimani tekshirishi shart?",
     "Transport vositasining texnik sozligini, tozaligini va to'liq jihozlanganligini",
     ["Yo'l bo'yidagi shoxobchalar ishlashini", "Faqat salon tozaligini"], "11", ""),
    (HM, "Harakatlanishni boshlashdan oldin haydovchi nimaga ishonch hosil qilishi shart?",
     "Yo'lovchilar joylarini egallaganiga va transport vositasining eshiklari yopilganiga",
     ["Yo'lovchilar telefonlarini o'chirganiga", "Yo'lovchilar yoqilg'i uchun to'lov qilganiga"], "11", ""),
    (HM, "Qorong'i vaqtda majburiy to'xtagan haydovchi ta'mirlash uchun qatnov qismiga chiqishdan oldin nima qilishi kerak?",
     "Nur qaytargichli maxsus jilet kiyib olishi",
     ["Transport vositasining faralarini o'chirishi", "Hech qanday qo'shimcha chora ko'rmasligi"], "11",
     "Bu talab yengil va yuk avtomobili, avtobus va g'ildirakli traktorlar haydovchilariga taalluqli."),
    (HM, "IIO xodimlari talab qilganda haydovchi nimadan o'tishi shart?",
     "Mastlik holatini aniqlovchi maxsus tekshiruvdan yoki tibbiy tekshiruvdan",
     ["Faqat ko'z tekshiruvidan", "Yo'l harakati qoidalari bo'yicha og'zaki imtihondan"], "11", ""),
    (HM, "Haydovchi yo'lovchilarni nimadan ogohlantirishi shart?",
     "Harakatlanayotgan vaqtda salondan tana qismlarini (qo'ldan tashqari) chiqarish taqiqlanganligidan",
     ["Salonda gaplashish taqiqlanganligidan", "Salonda ovqatlanish taqiqlanganligidan"], "11", ""),
    (HM, "Quyidagi holatlardan qaysi birida transport vositasini boshqarish taqiqlanadi?",
     "Yo'l harakati xavfsizligiga tahdid soladigan charchoqlik yoki betoblik holatida",
     ["Sutkaning yorug' vaqtida yaqinni yorituvchi faralar yoqilganda", "Yo'lovchilar bilan birga harakatlanganda"], "12", ""),
    (HM, "Transport vositasini boshqarish paytida telefondan foydalanishga qanday holatda ruxsat etiladi?",
     "Quloqchin yoki qo'llarni ishlatmasdan gaplashish imkonini beradigan boshqa uskunalar orqali",
     ["Qo'lda ushlab, qisqa gaplashish uchun", "Tezlik soatiga 40 km dan past bo'lganda"], "12", ""),
    (HM, "Salonning old qismiga o'rnatilgan monitorda tele- yoki video dasturlarni tomosha qilish haydovchiga nisbatan qanday?",
     "Boshqarish paytida taqiqlanadi", ["Faqat aholi punktidan tashqarida ruxsat etiladi", "Doim ruxsat etiladi"], "12", ""),
    (HM, "Transport vositasiga ratsiya yoki sirena kabi maxsus texnik jihozlarni o'rnatish qachon taqiqlanadi?",
     "Tegishli ruxsat bo'lmaganda", ["Faqat tungi vaqtda", "Faqat aholi punktlarida"], "12", ""),
    (HM, "Quyidagi nosozliklardan qaysi biri mavjud bo'lganda transport vositasini boshqarish taqiqlanadi?",
     "Tormoz tizimi yoki rul boshqaruvi ishlamasa",
     ["Konditsioner ishlamasa", "Magnitola ishlamasa", "Salon chirog'i yonmasa"], "12", ""),
    (HM, "Yomg'ir yoki qor yog'ayotgan vaqtda qaysi nosozlik bilan transport vositasini boshqarish taqiqlanadi?",
     "Oyna tozalagich ishlamasa", ["Radiopriyomnik ishlamasa", "Salon isitgichi ishlamasa"], "12", ""),
    (HM, "Aholi punktlarida magnitofon va boshqa ovoz chiqaruvchi apparaturalardan foydalanish qanday?",
     "Belgilangan me'yordan baland ovozda foydalanish taqiqlanadi",
     ["Umuman foydalanish taqiqlanadi", "Hech qanday cheklov yo'q"], "12", ""),
    (HM, "Xavfsizlik kamari nazarda tutilgan transport vositasini haydovchining o'zi kamar taqmagan holda boshqarishi:",
     "Taqiqlanadi", ["Shahar ichida ruxsat etiladi", "Tezlik soatiga 60 km dan past bo'lsa ruxsat etiladi"], "12", ""),

    # --- Yo'l-transport hodisasi ---
    (YTH, "YTH sodir bo'lganda unga daxldor haydovchi dastlab nima qilishi shart?",
     "Transport vositasini darhol to'xtatishi, avariya ishorasini yoqishi va avariya sababli to'xtash belgisini o'rnatishi",
     ["Hodisa joyini tezda tark etishi", "Transport vositasi va buyumlarni darhol boshqa joyga olib qo'yishi",
      "Faqat sug'urta kompaniyasiga xabar berishi"], "13",
     "Transport vositasini va hodisaga daxldor buyumlarni joyidan qo'zg'atmasligi kerak. Boshqalarga to'sqinlik qilsa, avval holatni qayd etib, keyin qatnov qismini bo'shatadi."),
    (YTH, "YTH da tan jarohati olganlarga nisbatan haydovchi nima qilishi shart?",
     "Birinchi tibbiy yordam ko'rsatish choralarini ko'rishi, tez tibbiy yordam va favqulodda qutqaruv xizmatlarini chaqirishi",
     ["Ularni o'z holiga qoldirib ketishi", "Faqat guvohlarning ismini yozib olishi"], "13", ""),
    (YTH, "YTH sodir bo'lganda haydovchi hodisa haqida kimga xabar berishi va nimani kutishi shart?",
     "IIOga xabar berishi, guvohlarning ism-familiyasi va manzilini yozib olib, IIO xodimlarining kelishini kutishi",
     ["Faqat qarindoshlariga xabar berishi", "Hech kimga xabar bermasdan ketishi"], "13", ""),
    (YTH, "Majburiy sug'urta bo'yicha YTH haqidagi xabarnoma tuzilgan hollarda haydovchi:",
     "DYHXX yoki IIO xodimlariga hodisa haqida xabar bermasligi mumkin",
     ["Baribir DYHXX ga xabar berishi shart", "Hodisa joyida 24 soat kutishi shart"], "14", ""),

    # --- Piyodalar ---
    (PI, "Piyodalar qayerdan harakatlanishlari kerak?",
     "Trotuar, piyodalar yo'lkasi, piyoda va velosiped yo'lkalaridan, ular bo'lmaganda yo'l yoqalaridan",
     ["Doim qatnov qismining o'rtasidan", "Doim qatnov qismining chap chetidan", "Faqat velosiped yo'lkasidan"], "15", ""),
    (PI, "Trotuar va yo'l yoqasi bo'lmaganda qatnov qismi chetida harakatlanayotgan piyodalar qaysi yo'nalishda yurishlari kerak?",
     "Transport vositalarining harakatlanishiga qarama-qarshi yo'nalishda",
     ["Transport vositalari bilan bir yo'nalishda", "Qatnov qismining o'rtasi bo'ylab"], "15", ""),
    (PI, "Velosiped yoki mototsiklni yetaklab ketayotgan shaxslar qatnov qismi chetida qaysi yo'nalishda yurishlari kerak?",
     "Transport vositalarining harakatlanish yo'nalishi bo'ylab",
     ["Transport vositalariga qarama-qarshi yo'nalishda", "Qatnov qismining o'rtasida"], "15", ""),
    (PI, "Piyodalarning tashkiliy jamlanmasi qatnov qismida bir qatorda nechta kishidan ortiq bo'lmasligi kerak?",
     "To'rt kishidan", ["Ikki kishidan", "Olti kishidan", "Sakkiz kishidan"], "16", "Faqat transport harakati yo'nalishi bo'ylab, o'ng tomondan harakatlanishga ruxsat etiladi."),
    (PI, "Bolalar guruhini yo'l yoqasidan olib yurishga qachon ruxsat etiladi?",
     "Trotuar va piyodalar yo'lkasi bo'lmaganda, faqat sutkaning yorug' vaqtida va katta yoshdagilar kuzatuvida",
     ["Istalgan vaqtda, kuzatuvchisiz", "Faqat sutkaning qorong'i vaqtida"], "16", ""),
    (PI, "Piyodalar yo'lning qatnov qismini qayerdan kesib o'tishlari kerak?",
     "Piyodalar o'tish joylaridan, shuningdek, yer osti va yer usti o'tish joylaridan",
     ["Istalgan joydan", "Faqat transport vositalari orasidan"], "17", ""),
    (PI, "Ko'rinadigan oraliqda o'tish joyi yoki chorraha bo'lmasa, ajratuvchi mintaqasiz va to'siqsiz yo'ldan piyoda qanday o'tishi mumkin?",
     "Yo'lning ikki tomoni yaxshi ko'rinadigan joyidan, qatnov qismi chetiga nisbatan to'g'ri burchak ostida",
     ["Qatnov qismi bo'ylab diagonal yo'nalishda", "Ko'rinishi cheklangan joydan, yugurib"], "17", ""),
    (PI, "Tartibga solinmaydigan piyodalar o'tish joyida piyoda qatnov qismiga qachon chiqishi mumkin?",
     "Yaqinlashayotgan transport vositalarigacha masofa va tezlikni chamalab, o'tish xavfsiz ekaniga ishonch hosil qilgach",
     ["Darhol, haydovchi to'xtaydi deb hisoblab", "Faqat guruh bo'lib"], "19", ""),
    (PI, "Qatnov qismida va piyodalar o'tish joylarida harakatlanayotgan piyodalarga nima taqiqlanadi?",
     "Telefondan foydalanish, tele-video mahsulotlarni ko'rish, audio mahsulotlarni eshitish va e'tiborni chalg'itadigan boshqa elektron vositalardan foydalanish",
     ["Shoshilmasdan yurish", "Qo'lida sumka ko'tarib yurish"], "19", ""),
    (PI, "Piyodalar to'xtab turgan avtobus va trolleybusning, shuningdek tramvayning qaysi tomonidan yo'lni kesib o'tishlari shart?",
     "Avtobus va trolleybusning orqa tomonidan, tramvayning esa oldi tomonidan",
     ["Avtobus va trolleybusning oldi tomonidan", "Hammasining oldi tomonidan", "Hammasining orqa tomonidan"], "19", ""),
    (PI, "Qatnov qismiga chiqib, o'tishga ulgurmagan piyoda qayerda to'xtashi lozim?",
     "Xavfsizlik orolchasida, u bo'lmasa qarama-qarshi oqimlarni ajratuvchi chiziqda",
     ["Qatnov qismining o'rtasida, harakatlanayotgan transport oldida", "Orqaga yugurib qaytishi shart"], "20", ""),
    (PI, "Ko'k/qizil mayoqchali va maxsus tovushli ishorali tezkor transport vositasi yaqinlashganda piyodalar nima qilishi kerak?",
     "Qatnov qismidan o'tmasligi, unda harakatlanayotganlari esa yo'l berib, zudlik bilan uni bo'shatishi",
     ["Tezroq yo'lni kesib o'tishga shoshilishi", "Qatnov qismida to'xtab turishi"], "21", ""),
    (PI, "Yo'nalishli transport vositalarini piyodalar qayerda kutishlari kerak?",
     "Qatnov qismidan baland joylashgan kutish maydonchalarida, ular bo'lmasa trotuar yoki yo'l yoqasida",
     ["Qatnov qismining chetida", "Qatnov qismining o'rtasida"], "22", ""),

    # --- Yo'lovchilar ---
    (YOL, "Yo'lovchilar transport vositasiga qachon chiqishlari va tushishlari shart?",
     "U to'liq to'xtagandan so'ng, trotuar yoki yo'l yoqasi tomondan",
     ["Harakat davomida, tezlik pasayganda", "Faqat qatnov qismi tomondan"], "23", ""),
    (YOL, "Yo'lovchilarga quyidagilardan qaysi biri taqiqlanadi?",
     "Transport vositasi harakatlanayotgan vaqtda uning eshiklarini ochish",
     ["Transport vositasi to'liq to'xtagach tushish", "Xavfsizlik kamarini taqib olish"], "24", ""),

    # --- Maxsus transport vositalari ---
    (MX, "Maxsus transport vositalari boshqa ishtirokchilarga nisbatan imtiyozdan foydalanishi uchun nima yoqilgan bo'lishi shart?",
     "Ko'k yoki qizil yoxud ko'k va qizil rangli yalt-yalt etuvchi mayoqcha va maxsus tovushli ishora",
     ["Faqat zarg'aldoq mayoqcha", "Faqat avariya ishorasi", "Faqat yaqinni yorituvchi faralar"], "25", ""),
    (MX, "Ko'k/qizil mayoqcha va tovushli ishorasi yoqilgan holda yaqinlashayotgan transport vositasiga nisbatan haydovchi nima qilishi shart?",
     "Yo'l berishi shart; bunday transport vositalarini quvib o'tish taqiqlanadi",
     ["Tezlikni oshirib, undan oldin o'tishi", "Uni quvib o'tishi mumkin", "E'tibor bermay harakatini davom ettirishi"], "26", ""),
    (MX, "Zarg'aldoq yoki sariq rangli yalt-yalt etuvchi mayoqcha yoqilgan transport vositasi:",
     "Imtiyoz bermaydi, boshqa ishtirokchilarni faqat xavf haqida ogohlantiradi",
     ["Boshqa transport vositalariga nisbatan to'liq imtiyoz beradi", "Svetofor qizil bo'lganda ham o'tishga ruxsat beradi"], "28", ""),
    (MX, "Maxsus transport vositalarini kuzatib kelayotgan transport vositalarida nima yoqilgan bo'lishi shart?",
     "Yaqinni yorituvchi fara chiroqlari",
     ["Uzoqni yorituvchi fara chiroqlari", "Faqat orqa tuman chirog'i", "Faqat avariya ishorasi"], "25", ""),

    # --- Svetofor va tartibga soluvchi ---
    (SV, "Svetoforning yashil ishorasi nimani bildiradi?",
     "Harakatlanishga ruxsat beradi",
     ["Harakatlanishni taqiqlaydi", "Faqat o'ngga burilishga ruxsat beradi", "Ishoralar almashuvi haqida ogohlantiradi"], "31", ""),
    (SV, "Miltillovchi yashil ishora nimani bildiradi?",
     "Harakatlanishga ruxsat beradi, ta'sir vaqti tugayotganini va ko'p o'tmay taqiqlovchi ishora yonishini bildiradi",
     ["Harakatlanishni taqiqlaydi", "Tartibga solinmagan chorraha borligini bildiradi"], "31", ""),
    (SV, "Sariq ishora (42-bandda ko'zda tutilgan holatlardan tashqari) nimani bildiradi?",
     "Harakatlanishni taqiqlaydi va ishoralar almashuvi haqida ogohlantiradi",
     ["Tezlikni oshirishga ruxsat beradi", "Harakatlanishga to'liq ruxsat beradi"], "31", ""),
    (SV, "Miltillovchi sariq ishora nimani bildiradi?",
     "Ehtiyotkorlik choralarini ko'rgan holda harakatlanishga ruxsat beradi va tartibga solinmagan chorraha yoki piyodalar o'tish joyi borligidan xabardor qiladi",
     ["Harakatlanishni qat'iyan taqiqlaydi", "Faqat velosipedchilar uchun ruxsat beradi"], "31", ""),
    (SV, "Qizil ishora, shuningdek, miltillovchi qizil ishora nimani bildiradi?",
     "Harakatlanishni taqiqlaydi",
     ["Harakatlanishga ruxsat beradi", "Ehtiyotkorlik bilan harakatlanishga ruxsat beradi",
      "Tezlikni kamaytirib davom ettirishga ruxsat beradi"], "31", ""),
    (SV, "Qizil va sariq ishoralarning bir vaqtda yonishi nimani bildiradi?",
     "Harakatlanishni taqiqlaydi va ko'p o'tmay yashil ishora yonishi haqida axborot beradi",
     ["Harakatlanishga ruxsat beradi", "Svetofor nosozligini bildiradi"], "31", ""),
    (SV, "Piyoda tasviri tushirilgan svetofor ishorasi kimning harakatlanishiga ta'sir qiladi?",
     "Faqat piyodalarga", ["Faqat haydovchilarga", "Barcha yo'l harakati ishtirokchilariga", "Faqat tramvaylarga"], "34", ""),
    (SV, "Velosiped tasviri tushirilgan svetofor ishorasi kimlarning harakatlanishiga ta'sir qiladi?",
     "Velosipedchilar va individual harakatlanish vositalarini boshqargan shaxslarga",
     ["Faqat yengil avtomobillar haydovchilariga", "Faqat piyodalarga"], "34", ""),
    (SV, "Reversiv svetoforning X-simon qizil ishorasi nimani bildiradi?",
     "Shu tasmada harakatlanishni taqiqlaydi",
     ["Shu tasmada harakatlanishga ruxsat beradi", "Tasmada tezlikni 20 km/soatgacha kamaytirishni talab qiladi"], "35", ""),
    (SV, "Temir yo'l kesishmasidagi doirasimon oq rangli miltillovchi ishora nimani bildiradi?",
     "Transport vositalarining kesishma orqali harakatlanishiga ruxsat beradi",
     ["Harakatlanishni taqiqlaydi", "Poyezd yaqinlashayotganini bildiradi"], "37", ""),
    (SV, "Tartibga soluvchi qo'llarini yon tomonga uzatganda yoki tushirganda, uning old va orqa tomonidan harakat qanday bo'ladi?",
     "Barcha transport vositalari va piyodalarning harakatlanishi taqiqlanadi",
     ["Barcha transport vositalariga ruxsat beriladi", "Faqat piyodalarga ruxsat beriladi"], "38", ""),
    (SV, "Tartibga soluvchi qo'llarini yon tomonga uzatganda, uning chap va o'ng yon tomonidan relssiz transport vositalariga qaysi yo'nalishlarda harakatlanishga ruxsat beriladi?",
     "To'g'riga va o'ngga", ["Faqat chapga", "Faqat to'g'riga", "Barcha yo'nalishlarda"], "38", ""),
    (SV, "Tartibga soluvchi qo'lini yuqoriga ko'targanda nima bo'ladi?",
     "42-bandda ko'rsatilgan hollardan tashqari, barcha yo'nalishlarda transport vositalari va piyodalarning harakatlanishi taqiqlanadi",
     ["Barcha yo'nalishlarda harakatlanishga ruxsat beriladi", "Faqat piyodalarga ruxsat beriladi"], "38", ""),
    (SV, "Tartibga soluvchining ishorasi svetofor ishorasiga yoki yo'l belgilariga zid bo'lsa, qaysi biriga amal qilinadi?",
     "Tartibga soluvchining ishoralari va ko'rsatmalariga",
     ["Svetofor ishorasiga", "Yo'l belgisiga", "Yo'l chizig'iga"], "43", ""),
    (SV, "Svetofor ishoralari imtiyoz belgilari talablariga zid bo'lsa, haydovchilar qaysi biriga amal qilishlari kerak?",
     "Svetofor ishoralariga", ["Imtiyoz belgilariga", "O'z xohishiga ko'ra"], "43", ""),
    (SV, "Svetoforning ishoralari ishlamayotgan bo'lsa, haydovchi harakatni qachon davom ettirishi mumkin?",
     "Boshqa (ko'ndalang) yo'nalishdagi svetofor ishoralari ham ishlamayotganiga ishonch hosil qilgandan so'ng, xavfsizlikni ta'minlagan holda",
     ["Darhol, tezlikni oshirib", "Faqat tovushli ishora berib"], "43", ""),
    (SV, "Svetofor yoki tartibga soluvchining taqiqlovchi ishorasida haydovchi (to'xtash chizig'i mavjud bo'lsa) qayerda to'xtashi kerak?",
     "To'xtash chizig'i (5.33 belgisi) oldida; transport vositasining eng oldingi nuqtasi chiziq ustiga chiqib ketmasligi kerak",
     ["To'xtash chizig'idan o'tib, chorrahaning o'rtasida", "Piyodalar o'tish joyining ichida"], "41", ""),
    (SV, "Yashil ishoradan keyin sariq ishora yonganda, keskin tormoz bermasdan to'xtashga ulgura olmaydigan haydovchi nima qiladi?",
     "Harakatlanishni davom ettirishi mumkin",
     ["Keskin tormoz berib to'xtashi shart", "Orqaga qaytishi shart"], "42", ""),
    (SV, "Tartibga soluvchi yoki IIO xodimi haydovchidan transport vositasini to'xtatishni talab qilganda:",
     "Haydovchi ko'rsatilgan joyda to'xtashi shart",
     ["Haydovchi harakatini davom ettirishi mumkin", "Faqat kunduzi to'xtashi shart"], "39", ""),

    # --- Ogohlantiruvchi va avariya ishoralari ---
    (OG, "Quyidagilardan qaysi biri ogohlantiruvchi ishora hisoblanadi?",
     "Fara chiroqlarini yoqib-o'chirish",
     ["Konditsionerni yoqish", "Radioni o'chirish", "Oyna tozalagichni yoqish"], "44", ""),
    (OG, "Chapga burilish (qayrilib olish)ni bildiruvchi qo'l ishorasi qanday beriladi?",
     "Chap qo'lni yonga uzatish yoki o'ng qo'lni tirsakdan to'g'ri burchak ostida bukib, yuqoriga ko'tarish",
     ["O'ng qo'lni yonga uzatish", "Ikkala qo'lni pastga tushirish"], "45", ""),
    (OG, "O'ngga burilish (qayrilib olish)ni bildiruvchi qo'l ishorasi qanday beriladi?",
     "O'ng qo'lni yonga uzatish yoki chap qo'lni tirsakdan to'g'ri burchak ostida bukib, yuqoriga ko'tarish",
     ["Chap qo'lni yonga uzatish", "Ikkala qo'lni yuqoriga ko'tarish"], "45", ""),
    (OG, "Qo'l bilan to'xtash ishorasi qanday beriladi?",
     "Chap yoki o'ng qo'lni yuqoriga ko'tarib",
     ["Ikkala qo'lni yonga uzatib", "Qo'lni pastga tushirib"], "45", ""),
    (OG, "Harakatlanishni boshlash, qayta tizilish, burilish va to'xtashdan oldin haydovchi nima qilishi shart?",
     "Tegishli yo'nalishni ko'rsatuvchi yorug'lik ishoralarini yoqishi, ular bo'lmasa yoki ishlamasa qo'l bilan ishora berishi",
     ["Faqat tovushli ishora berishi", "Hech qanday ishora bermasligi mumkin"], "45", ""),
    (OG, "Burilish ko'rsatkichi yoki qo'l ishorasi qachon berilishi kerak?",
     "Manyovrni bajarishdan oldinroq berilishi va uni tugallagach darhol to'xtatilishi",
     ["Manyovrni tugatgandan keyin", "Manyovr boshlangandan keyingina"], "46", ""),
    (OG, "Ogohlantiruvchi ishora berish haydovchiga nimani beradi?",
     "Oldin o'tish huquqini bermaydi va zaruriy ehtiyot choralarini ko'rish mas'uliyatidan ozod etmaydi",
     ["Oldin o'tish huquqini beradi", "Ehtiyot choralarini ko'rishdan ozod qiladi"], "46", ""),
    (OG, "Tovushli ishoralar qachon qo'llanilishi mumkin?",
     "Aholi punktlaridan tashqarida boshqa haydovchilarni quvib o'tish haqida ogohlantirish uchun va YTH ning oldini olish zarur bo'lgan hollarda",
     ["Aholi punktlarida ham, salomlashish uchun", "Istalgan joyda, haydovchining xohishiga ko'ra"], "48", ""),
    (OG, "Burilishni ko'rsatuvchi barcha yorug'lik ishoralarining bir vaqtda miltillashi nima hisoblanadi?",
     "Avariya (xavf-xatar) ishorasi",
     ["Chapga burilish ishorasi", "To'xtash ishorasi", "Quvib o'tish ishorasi"], "50", ""),
    (OG, "Quyidagi hollarning qaysi birida avariya ishorasi yoqilishi kerak?",
     "Shatakka olishda (shatakka olingan mexanik transport vositasida)",
     ["Chorrahada chapga burilishda", "Quvib o'tishni boshlashda", "Aholi punktida harakatlanishda"], "50", ""),
    (OG, "Fara chiroqlari yorug'ligi haydovchining ko'zini qamashtirganda nima yoqilishi kerak?",
     "Avariya ishorasi", ["Orqa tuman chirog'i", "Hech narsa yoqilmaydi"], "50", ""),
    (OG, "Avariya sababli to'xtash belgisi aholi punktlaridan tashqarida transport vositasidan kamida necha metr masofada o'rnatilishi kerak?",
     "30 metr", ["15 metr", "10 metr", "50 metr"], "51", ""),
    (OG, "Avariya sababli to'xtash belgisi aholi punktlarida transport vositasidan kamida necha metr masofada o'rnatilishi kerak?",
     "15 metr", ["5 metr", "10 metr", "30 metr"], "51", ""),

    # --- Manyovr qilish ---
    (MN, "Yondosh hududdan yo'lga chiqayotgan haydovchi kimga yo'l berishi kerak?",
     "Yo'lda harakatlanayotgan piyodalar va transport vositalariga",
     ["Faqat tez tibbiy yordam mashinasiga", "Hech kimga, chunki yo'lga chiqayotgan imtiyozga ega"], "54", ""),
    (MN, "Bir yo'nalishda harakatlanayotgan transport vositalari bir vaqtda qayta tizilayotganda haydovchi kimga yo'l berishi kerak?",
     "O'ng tomondagi transport vositasiga",
     ["Chap tomondagi transport vositasiga", "Kattaroq transport vositasiga"], "55", ""),
    (MN, "Burilish (qayrilib olish)dan oldin haydovchi qatnov qismida qaysi holatni egallashi shart?",
     "Shu yo'nalishda harakatlanish uchun mo'ljallangan qatnov qismining eng chetki holatini",
     ["Qatnov qismining o'rtasidagi holatni", "Har doim chap chetki holatni"], "56", "Aylanma harakatli chorrahaga kirish uchun burilish bundan mustasno."),
    (MN, "O'ngga burilishda transport vositasi qanday joylashishi kerak?",
     "Iloji boricha qatnov qismining o'ng chetiga yaqinroq",
     ["Qatnov qismining chap chetiga yaqinroq", "Qarama-qarshi yo'nalish tasmasida"], "57", ""),
    (MN, "Chorrahadan tashqarida chapga burilish yoki qayrilib olishda relssiz transport vositasi haydovchisi kimga yo'l berishi shart?",
     "Qarama-qarshi yo'nalishdan harakatlanayotgan transport vositalariga va bir yo'nalishdagi tramvayga",
     ["Faqat orqadan kelayotgan transport vositalariga", "Hech kimga"], "59", ""),
    (MN, "Yo'nalishlar kesishganda va o'tish navbati Qoidalarda ko'zda tutilmagan hollarda haydovchi kimga yo'l berishi kerak?",
     "O'ng tomondan yaqinlashayotgan transport vositasiga",
     ["Chap tomondan yaqinlashayotgan transport vositasiga", "Tezroq yaqinlashayotgan transport vositasiga"], "60", ""),
    (MN, "Sekinlashish bo'lagi bo'lgan yo'lda burilmoqchi bo'lgan haydovchi nima qilishi kerak?",
     "O'z vaqtida shu tasmaga qayta tizilib, tezlikni faqat unda kamaytirishi",
     ["Asosiy tasmada tezlikni keskin kamaytirib, so'ng burilishi", "Qayta tizilmasdan chapga burilishi"], "61", ""),
    (MN, "Yo'lning ko'rinishi biror yo'nalishda necha metrdan kam bo'lgan joylarda qayrilib olish taqiqlanadi?",
     "100 metrdan", ["50 metrdan", "200 metrdan", "300 metrdan"], "62", ""),
    (MN, "Quyidagi joylarning qaysi birida qayrilib olish taqiqlanadi?",
     "Piyodalar o'tish joylarida",
     ["Yo'l yoqasi kengaygan joyda", "Keng va bo'sh, belgi bilan taqiqlanmagan to'g'ri yo'l qismida"], "62", "Shuningdek: tunnellarda, ko'priklarda, temir yo'l kesishmalarida."),
    (MN, "Orqaga harakatlanish qayerlarda taqiqlanadi?",
     "Chorrahalarda va qayrilib olish mumkin bo'lmagan joylarda",
     ["Faqat tunda", "Hech qayerda taqiqlanmaydi"], "63", ""),

    # --- Transport vositalarining joylashuvi ---
    (JL, "To'rt va undan ortiq tasmali, ikki tomonlama harakatli yo'llarda qarama-qarshi yo'nalish tasmalariga chiqish:",
     "Taqiqlanadi", ["Quvib o'tish uchun ruxsat etiladi", "Tezlikni oshirish uchun ruxsat etiladi"], "65", ""),
    (JL, "Uch tasmali, ikki tomonlama harakatli yo'lda o'rta qatorga qachon chiqishga ruxsat etiladi?",
     "Faqat quvib o'tish, aylanib o'tish, chapga burilish va qayrilib olish uchun",
     ["Doimiy harakatlanish uchun", "Faqat to'xtash uchun"], "66", ""),
    (JL, "Aholi punktlaridan tashqaridagi yo'llarda haydovchilar qaysi qatorda harakatlanishlari kerak?",
     "Mumkin qadar qatnov qismining o'ng chetiga yaqinroq; o'ng tasmalar bo'sh bo'lganda chap tasmalarni egallash taqiqlanadi",
     ["Doim eng chap qatorda", "Istalgan qatorda"], "67", ""),
    (JL, "Tezligini soatiga necha kilometrdan oshirishi mumkin bo'lmagan transport vositalari asosan chetki o'ng qatorda harakatlanishi kerak?",
     "40 km/soat", ["20 km/soat", "60 km/soat", "80 km/soat"], "68", ""),
    (JL, "Qatnov qismi yo'l chiziqlari bilan tasmalarga ajratilgan bo'lsa, harakatlanish qanday amalga oshiriladi?",
     "Qat'iy belgilangan tasmalarda; faqat qayta tizilishda uzuq-uzuq chiziqlarni bosib o'tish mumkin",
     ["Istalgan tasmada, chiziqlarni bosib o'tgan holda", "Faqat o'ng tasmada"], "70", ""),
    (JL, "Mexanik transport vositalarining ajratuvchi mintaqalar, yo'l yoqalari, trotuarlar va piyodalar yo'lkalarida harakatlanishi:",
     "Taqiqlanadi (Qoidalarda ko'zda tutilgan istisnolardan tashqari)",
     ["Doim ruxsat etiladi", "Faqat yengil avtomobillarga ruxsat etiladi"], "72", ""),
    (JL, "Haydovchi oldinda harakatlanayotgan transport vositasi keskin tormoz berganda to'qnashmaslik uchun nimani saqlashi kerak?",
     "To'qnashib ketmaslik kafolatini beradigan oraliq masofani",
     ["Iloji boricha yaqin masofani", "Faqat yonlama oraliqni"], "73", ""),
    (JL, "Qarama-qarshi yo'nalishlarda harakatlanish to'siq sababli qiyin bo'lsa, kim yo'l berishi kerak?",
     "To'siq o'z tomonida bo'lgan haydovchi",
     ["To'siq bo'lmagan tomondagi haydovchi", "Kichik transport vositasining haydovchisi"], "75", ""),
    (JL, "Boshqa belgilar bo'lmasa, ajratuvchi bo'lagi yo'q ikki tomonlama yo'ldagi xavfsizlik orolchalari va ustunchalar qaysi tomondan aylanib o'tiladi?",
     "O'ng tomondan", ["Chap tomondan", "Qaysi tomondan qulay bo'lsa"], "76", ""),

    # --- Harakatlanish tezligi ---
    (TZ, "Aholi punktlarida transport vositalarining tezligi umumiy qoidaga ko'ra soatiga necha kilometrdan oshmasligi kerak?",
     "70 km/soat", ["50 km/soat", "60 km/soat", "90 km/soat"], "78", ""),
    (TZ, "Maktab va maktabgacha ta'lim tashkilotlariga yetmasdan va o'tib ketib 300 metrdan kam masofada (tegishli belgi o'rnatilgan joylarda) tezlik soatiga necha kilometrdan oshmasligi kerak?",
     "30 km/soat", ["20 km/soat", "40 km/soat", "60 km/soat"], "78", ""),
    (TZ, "Turar joy dahalari va yondosh hududlarda (uy-joy binolari orasidagi yer uchastkasida) tezlik soatiga necha kilometrdan oshmasligi kerak?",
     "20 km/soat", ["10 km/soat", "30 km/soat", "40 km/soat"], "78", ""),
    (TZ, "Nukus va Toshkent shaharlarida, viloyat va tuman markazlarida, shuningdek shaharlar hududlarida tezlik soatiga necha kilometrdan oshmasligi kerak?",
     "60 km/soat", ["40 km/soat", "70 km/soat", "80 km/soat"], "78", ""),
    (TZ, "Aholi punktlaridan tashqarida yengil avtomobillar tezligi soatiga necha kilometrdan oshmasligi kerak?",
     "100 km/soat", ["80 km/soat", "90 km/soat", "120 km/soat"], "79", ""),
    (TZ, "Aholi punktlaridan tashqarida shaharlararo qatnaydigan avtobus va mikroavtobuslar tezligi soatiga necha kilometrdan oshmasligi kerak?",
     "90 km/soat", ["70 km/soat", "100 km/soat", "110 km/soat"], "79", ""),
    (TZ, "Aholi punktlaridan tashqarida ruxsat etilgan to'liq vazni 3,5 tonnadan ortiq yuk avtomobillari tezligi soatiga necha kilometrdan oshmasligi kerak?",
     "80 km/soat", ["60 km/soat", "90 km/soat", "100 km/soat"], "79", ""),
    (TZ, "Aholi punktlaridan tashqarida tirkamali yuk avtomobillari tezligi soatiga necha kilometrdan oshmasligi kerak?",
     "70 km/soat", ["50 km/soat", "80 km/soat", "90 km/soat"], "79", ""),
    (TZ, "Yukxonasida odam tashiyotgan yuk avtomobillari har qanday yo'llarda soatiga necha kilometrdan oshmagan tezlikda harakatlanishi mumkin?",
     "60 km/soat", ["40 km/soat", "70 km/soat", "80 km/soat"], "80", ""),
    (TZ, "Bolalar guruhini tashkiliy tashiyotgan transport vositalari tezligi soatiga necha kilometrdan oshmasligi kerak?",
     "60 km/soat", ["40 km/soat", "70 km/soat", "90 km/soat"], "80", ""),
    (TZ, "Mexanik transport vositalarini shatakka olgan transport vositalari tezligi soatiga necha kilometrdan oshmasligi kerak?",
     "50 km/soat", ["30 km/soat", "60 km/soat", "70 km/soat"], "80", ""),
    (TZ, "Haydovchiga quyidagilardan qaysi biri taqiqlanadi?",
     "YTH ning oldini olish zarurati bo'lmaganda keskin tormoz berish",
     ["Yo'l sharoitini hisobga olib tezlikni kamaytirish", "Xavfsiz oraliq masofani saqlash"], "81", ""),
    (TZ, "Haydovchi tezlikni tanlashda nimalarni hisobga olishi kerak?",
     "Serqatnovlikni, transport vositasi va yukning xususiyati hamda holatini, yo'l va ob-havo sharoitini, harakat yo'nalishidagi ko'rinishni",
     ["Faqat transport vositasining rusumini", "Faqat boshqa haydovchilarning tezligini"], "77", ""),

    # --- Quvib o'tish ---
    (QO, "Quvib o'tishni boshlashdan oldin haydovchi nimaga ishonch hosil qilishi shart?",
     "Orqadagi transport vositasi quvib o'tishni boshlamaganiga, oldindagisi quvib o'tish yoki chapga burilish ishorasini bermayotganiga va bo'lak yetarlicha masofada bo'shligiga",
     ["Faqat tezligi 100 km/soatdan yuqori ekaniga", "Faqat oldindagi haydovchi yo'l berishiga"], "82", ""),
    (QO, "Chapga burilish ishorasini berib, burilishga kirishgan transport vositasini qaysi tomondan o'zib ketish kerak?",
     "O'ng tomondan", ["Chap tomondan", "O'zib ketish taqiqlanadi"], "83", ""),
    (QO, "Quvib o'tilayotgan transport vositasining haydovchisiga nima taqiqlanadi?",
     "Tezlikni oshirish yoki boshqa xatti-harakatlar bilan quvib o'tishga to'sqinlik qilish",
     ["Tezlikni pasaytirish", "Chap burilish ishorasini yoqish"], "84", ""),
    (QO, "Quyidagi joylarning qaysi birida quvib o'tish taqiqlanadi?",
     "Piyodalar o'tish joylarida",
     ["Aholi punktidan tashqaridagi, ko'rinishi yaxshi tekis yo'l qismida", "Ikki tasmali yo'lning belgisiz to'g'ri qismida"], "86", "Shuningdek: tartibga solingan chorrahalarda, ko'priklarda, yo'l o'tkazgichlarda, temir yo'l kesishmalarida."),
    (QO, "Temir yo'l kesishmasigacha necha metrdan kam masofa qolganda quvib o'tish taqiqlanadi?",
     "100 metrdan", ["50 metrdan", "30 metrdan", "200 metrdan"], "86", ""),
    (QO, "Quvib o'tishni tugallagandan so'ng haydovchi nima qilishi shart?",
     "Ilgari egallagan harakatlanish yo'nalishiga qaytishi",
     ["Chap tasmada harakatni davom ettirishi", "Tezlikni keskin oshirishi"], "85", ""),
    (QO, "Tepalikning oxirida va yo'lning ko'rinishi cheklangan joylarda quvib o'tish:",
     "Taqiqlanadi", ["Ruxsat etiladi", "Faqat tungi vaqtda ruxsat etiladi"], "86", ""),
    (QO, "Aholi punktlaridan tashqarida sekin harakatlanadigan, katta hajmli transport vositasining haydovchisi orqasida transport vositalari to'planib qolsa, nima qilishi kerak?",
     "Iloji boricha yo'lning o'ng tomoniga olishi, zarur bo'lsa to'xtab, orqasidagilarni o'tkazib yuborishi",
     ["Tezlikni yanada kamaytirishi", "Yo'lning o'rtasida harakatni davom ettirishi"], "87", ""),

    # --- To'xtash va to'xtab turish ---
    (TX, "Transport vositalariga yo'lning qaysi tomonida to'xtash va to'xtab turishga ruxsat etiladi?",
     "Yo'lning o'ng tomonida, yo'l yoqasida, u bo'lmasa qatnov qismining chetida",
     ["Yo'lning chap tomonida", "Qatnov qismining o'rtasida", "Ajratuvchi mintaqada"], "88", ""),
    (TX, "Aholi punktlarida yo'lning chap tomonida to'xtash va to'xtab turishga qachon ruxsat etiladi?",
     "O'rtada tramvay yo'li bo'lmagan, har yo'nalishda bittadan tasmasi bor yo'llarda hamda bir tomonlama harakatli yo'llarda",
     ["Istalgan yo'lda", "Hech qachon ruxsat etilmaydi"], "88", ""),
    (TX, "Qatnov qismida kajavasi bo'lmagan ikki g'ildirakli transport vositalarini qanday joylashtirishga ruxsat etiladi?",
     "Boshqalarga xalaqit bermaslik sharti bilan, qatnov qismi chetiga parallel ravishda ikki qator qilib",
     ["Qatnov qismining o'rtasida ko'ndalang", "Faqat bir qator bo'lib"], "89", ""),
    (TX, "Aholi punktlaridan tashqarida tunab qolish yoki dam olish uchun uzoq vaqt to'xtab turishga qayerda ruxsat etiladi?",
     "Buning uchun ko'zda tutilgan maydonchalarda yoki yo'ldan tashqarida",
     ["Yo'lning qatnov qismida", "Yo'l yoqasida"], "90", ""),
    (TX, "Transport vositalarining qayrilib olish joylarida va unga necha metr yetmasdan yoki o'tib to'xtash taqiqlanadi?",
     "30 metr", ["10 metr", "15 metr", "50 metr"], "VM 172-son qarori 1-band g)", ""),

    # --- Asosiy atamalar ---
    (AT, "Transport vositasi harakatini necha daqiqagacha bo'lgan muddatga to'xtatish «to'xtash» deyiladi?",
     "10 daqiqagacha", ["5 daqiqagacha", "15 daqiqagacha", "30 daqiqagacha"], "6", ""),
    (AT, "«To'xtab turish» nima?",
     "Yo'lovchi chiqarish/tushirish yoki yuk ortish/tushirish bilan bog'liq bo'lmagan hollarda harakatni 10 daqiqadan ko'proq vaqtga atayin to'xtatish",
     ["Harakatni 10 daqiqagacha to'xtatish", "Svetoforda kutib turish"], "6", ""),
    (AT, "Yo'lning ko'rinish masofasi necha metrdan kam bo'lsa, «yetarlicha ko'rinmaslik» deb hisoblanadi?",
     "300 metrdan", ["100 metrdan", "200 metrdan", "500 metrdan"], "6", "Yomg'ir, qor, tuman va kunning g'ira-shira vaqtida."),
    (AT, "«Sutkaning qorong'i vaqti» qaysi oraliq?",
     "Kechki g'ira-shiraning oxiridan tonggi g'ira-shiraning boshlanishigacha bo'lgan vaqt",
     ["Soat 18:00 dan 06:00 gacha", "Soat 21:00 dan 05:00 gacha"], "6", ""),
    (AT, "Mopedning dvigateli ish hajmi qanday bo'ladi?",
     "25 sm³ va undan ortiq, lekin 50 sm³ dan oshmaydigan",
     ["25 sm³ gacha", "50 sm³ va undan ortiq", "125 sm³ gacha"], "6", ""),
    (AT, "Mototsiklning dvigateli ish hajmi va konstruktiv tezligi qanday?",
     "Ish hajmi 50 sm³ va undan oshadigan, konstruktiv tezligi soatiga 50 km va undan oshadigan",
     ["Ish hajmi 25 sm³ gacha, tezligi 25 km/soatgacha", "Ish hajmi 25 dan 50 sm³ gacha"], "6", ""),
    (AT, "Quyidagilardan qaysi biri chorraha hisoblanmaydi?",
     "Yondosh hududlardan chiqish joylari",
     ["Yo'llarning bir sathda kesishadigan joyi", "Yo'llarning bir sathda tutashadigan joyi"], "6", ""),
    (AT, "Aholi punkti qanday hudud?",
     "Kirish va chiqish yo'llari 5.22 — 5.25 yo'l belgilari bilan belgilangan hudud",
     ["Faqat shahar markazi", "Faqat 5.1 belgisi bilan belgilangan hudud"], "6", ""),
    (AT, "Avtomagistral qaysi yo'l belgisi bilan belgilanadi?",
     "5.1", ["5.22", "2.1", "5.16.1"], "6", ""),
    (AT, "Piyodalar o'tish joyi qaysi belgilar va chiziqlar bilan belgilanadi?",
     "5.16.1, 5.16.2, 5.48 yo'l belgilari hamda 1.14.1 — 1.14.4 yoki 1.29.1 — 1.29.3 yo'l chiziqlari bilan",
     ["Faqat 5.1 belgisi bilan", "5.22 — 5.25 belgilari bilan"], "6", ""),
    (AT, "Dvigatelli velosipedning nominal quvvati va tezligi qanday bo'lishi mumkin?",
     "Nominal quvvati 0,25 kW dan, tezligi soatiga 25 km dan oshmaydigan",
     ["1 kW gacha va 50 km/soatgacha", "4 kW gacha"], "6", ""),
    (AT, "Velosipedchilar qorong'i vaqtda velosiped yo'lkasi bo'lmaganda qatnov qismida harakatlanayotganda nima kiyishlari shart?",
     "Nur qaytargichli kamzul yoki nur qaytaruvchi elementlari bor ustki kiyim",
     ["Oq rangli kiyim", "Hech qanday maxsus kiyim talab etilmaydi"], "VM 172-son qarori 1-band d)", ""),
    (AT, "Yengil avtomobil tomiga o'rnatilgan yukxonadagi yukning balandligi qancha bo'lganda yuk tashishga yo'l qo'yiladi?",
     "1 metrdan oshmasa", ["2 metrdan oshmasa", "0,5 metrdan oshmasa"], "VM 172-son qarori 1-band b)", "Uzunligi avtomobil gabaritidan 0,5 metrdan oshmasligi ham shart."),

    # --- Individual harakatlanish vositalari ---
    (IH, "Individual harakatlanish vositalarini (masalan, elektrosamokat) umumiy qoidaga ko'ra necha yoshdan kichik shaxslar boshqarishi taqiqlanadi?",
     "14 yoshdan", ["12 yoshdan", "16 yoshdan", "18 yoshdan"], "121", "Turar joy dahalari, istirohat bog'lari, bolalar maydonchalari va yopiq hududlar bundan mustasno."),
    (IH, "Individual harakatlanish vositasini boshqarayotgan shaxs trotuar, piyodalar yo'lkasi yoki piyoda va velosiped yo'lkasida soatiga necha kilometrdan oshmagan tezlikda harakatlanishi kerak?",
     "10 km/soat", ["5 km/soat", "20 km/soat", "25 km/soat"], "122", ""),
    (IH, "Individual harakatlanish vositalarini boshqaruvchi shaxslarga quyidagilardan qaysi biri taqiqlanadi?",
     "Odam tashish",
     ["Harakat yo'nalishi bo'yicha harakatlanish", "Velosipedchilar tasmasi bor joyda shu tasmadan harakatlanish"], "121", ""),
    (IH, "Individual harakatlanish vositasini boshqargan shaxslarning harakati piyodalarning harakati bilan birlashganda kim ustunlikka ega?",
     "Piyodalar", ["Individual harakatlanish vositasini boshqargan shaxs", "Tezroq harakatlanayotgan"], "123", ""),
    (IH, "Velosipedchilar uchun tasma yoki piyoda va velosiped yo'lkasi mavjud bo'lganda individual harakatlanish vositasini boshqaruvchi qayerdan harakatlanishi kerak?",
     "Shu tasma yoki yo'lkadan (harakatlanish imkoni bo'lmagan holatlardan tashqari)",
     ["Yo'lning qatnov qismidan", "Yo'l yoqasidan"], "121", ""),
    (IH, "Trotuar va yo'lkalar bo'lmaganda individual harakatlanish vositasini boshqargan shaxs yo'lning o'ng chetida soatiga necha kilometrdan oshmagan tezlikda harakatlanishi kerak?",
     "20 km/soat", ["10 km/soat", "30 km/soat", "40 km/soat"], "122", ""),
]


def build():
    rows, seen = [], set()
    for i, (topic, text, correct, wrongs, band, expl) in enumerate(D):
        qid = 1001 + i
        opts = [correct] + wrongs
        assert len(set(opts)) == len(opts), f"Takroriy variant: {qid}"
        assert text not in seen, f"Takroriy savol: {qid}"
        seen.add(text)
        random.Random(qid).shuffle(opts)
        band_txt = band if band.startswith("VM") else f"{band}-band"
        rows.append({
            "id": qid, "topic": topic, "text": text, "options": opts,
            "answer": opts.index(correct), "explain": expl,
            "source": f"{SRC}, {band_txt}", "status": "draft",
        })
    return rows


def main():
    rows = build()
    out = os.path.join(BASE, "data")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "questions_yhq_v1.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out, "review_sheet_v1.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Mavzu", "Savol", "A", "B", "C", "D", "To'g'ri javob", "Manba",
                    "Tushuntirish", "Ekspert xulosasi (to'g'ri / noto'g'ri / o'zgartirish)", "Izoh"])
        for r in rows:
            o = r["options"] + [""] * (4 - len(r["options"]))
            w.writerow([r["id"], r["topic"], r["text"], *o, "ABCD"[r["answer"]], r["source"], r["explain"], "", ""])
    by_topic = {}
    for r in rows:
        by_topic[r["topic"]] = by_topic.get(r["topic"], 0) + 1
    print(f"Jami: {len(rows)} ta savol")
    for t, n in by_topic.items():
        print(f"  {n:3d}  {t}")
    pos = [r["answer"] for r in rows]
    print("To'g'ri javob o'rinlari (A,B,C,D):", [pos.count(k) for k in range(4)])


if __name__ == "__main__":
    main()
