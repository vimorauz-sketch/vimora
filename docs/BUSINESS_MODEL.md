# VIMORA — biznes modeli va xizmatlar auditi (2026-11)

**Tamoyil:** har bir mijoz o'z hududida mavjud xizmatlardan foydalanadi. Raqamli xizmatlar esa butun O'zbekiston uchun ochiq.

| Tur | Qayerda | Qanday |
|---|---|---|
| **ONLINE** | Butun O'zbekiston | Internet orqali bajariladi: fayl va topshiriq olinadi, natija yuboriladi |
| **REMOTE** | Butun O'zbekiston | Mijoz kompyuteriga AnyDesk va shunga o'xshash dasturlar orqali faqat uning roziligi bilan ulaniladi. Seansni mijoz istalgan payt to'xtata oladi. Parol so'ralmaydi |
| **LOCAL** | Faqat Qarapchi qishlog'i | Bitta Canon PIXMA G3410 (rangli/oq-qora chop etish, skaner, nusxa, A4). Mijoz o'zi olib ketadi (pickup) yoki qishloq ichida uchrashiladi (meetup) |
| **FUTURE** | — | Katalogda ko'rinmaydi. Keyinchalik hamkorlar bilan yo'lga qo'yilishi mumkin |
| **DISABLED** | — | Arxivda saqlanadi (o'chirilmaydi): takroriy yoki bajarib bo'lmaydigan xizmat |

Zomin shahri va boshqa hududlar uchun oflayn buyurtma **qabul qilinmaydi**. Bu qoida backendda tekshiriladi. AI yordamchi ham bu qoidani chetlab o'ta olmaydi. Kuryer tizimi va hamkorlar kabineti hozircha yo'q, lekin hududlar jadvali va `provider_id` maydoni kelajakda kengaytirish uchun tayyorlab qo'yilgan.

## Natija
- **96 → 100 xizmat:** 81 ta ONLINE, 13 ta REMOTE, 4 ta LOCAL (yangi), 1 ta FUTURE, 1 ta DISABLED.
- **Matni o'zgartirilgan (MODIFY) 9 ta xizmat.** Ularning matni haqiqiy imkoniyatga moslab yozildi. Masalan, Windowsni noldan qayta o'rnatish masofadan bajarilmasligi, Green Card'da g'alaba kafolatlanmasligi, shartnoma shablonlari yuridik maslahat emasligi aniq ko'rsatildi.
- **FUTURE:** `phone-setup`, chunki telefon qo'lda bo'lishi kerak.
- **DISABLED:** `ai-text`, chunki u "Kopiraytingi" va "Xulosa va hisobot" xizmatlarini takrorlaydi.
- **Narxlar o'ylab topilmagan.** Hammasi "Individual narx". LOCAL xizmatlarda oldindan to'lov 0%, chunki naqd to'lov topshirishda qabul qilinadi.

## 100 ta xizmat tasnifi
AI ustunidagi qiymatlar: "Ha" — xizmatda AI imkoniyati ulangan. "Yordamchi sifatida" — AI faqat talabni tushunish va savol berishda yordam beradi. Har ikkala holatda ham natija mijozga **inson tekshiruvidan keyin** yuboriladi.

| # | Xizmat | Yo'nalish | Tur | Hudud | AI | Tavsiya |
|---|---|---|---|---|---|---|
| 1 | Windows sozlash va xatolarni tuzatish (masofadan) | Kompyuter yordami | REMOTE | Butun O'zbekiston | Yordamchi sifatida | MODIFY |
| 2 | Drayverlarni o'rnatish | Kompyuter yordami | REMOTE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 3 | Viruslarni tozalash | Kompyuter yordami | REMOTE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 4 | Kompyuterni tezlashtirish | Kompyuter yordami | REMOTE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 5 | Dasturlarni o'rnatish | Kompyuter yordami | REMOTE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 6 | O'chirilgan fayllarni tiklash (masofadan) | Kompyuter yordami | REMOTE | Butun O'zbekiston | Yordamchi sifatida | MODIFY |
| 7 | Printer va skanerni sozlash | Kompyuter yordami | REMOTE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 8 | Wi-Fi va internet muammolarini tekshirish | Kompyuter yordami | REMOTE | Butun O'zbekiston | Yordamchi sifatida | MODIFY |
| 9 | Zaxira nusxa sozlash | Kompyuter yordami | REMOTE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 10 | Masofaviy kompyuter yordami | Kompyuter yordami | REMOTE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 11 | Telefon sozlash va ma'lumot ko'chirish | Kompyuter yordami | FUTURE | — | Yordamchi sifatida | ARCHIVE (FUTURE) |
| 12 | Matn terish | Hujjatlar va PDF | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 13 | Word hujjatini rasmiylashtirish | Hujjatlar va PDF | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 14 | Rezyume (CV) tayyorlash | Hujjatlar va PDF | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 15 | Motivatsion xat va ariza yozish | Hujjatlar va PDF | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 16 | PDF konvertatsiya va tahrirlash | Hujjatlar va PDF | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 17 | Hujjatlarni raqamlashtirish | Hujjatlar va PDF | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 18 | Shartnoma va blanka shablonlari | Hujjatlar va PDF | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | MODIFY |
| 19 | Hujjat chop etish (rangli yoki oq-qora) | Chop etish va skanerlash (Qarapchi) | LOCAL | Qarapchi | Yordamchi sifatida | NEW |
| 20 | Hujjat nusxalash (kserokopiya) | Chop etish va skanerlash (Qarapchi) | LOCAL | Qarapchi | Yordamchi sifatida | NEW |
| 21 | Hujjatlarni skanerlash | Chop etish va skanerlash (Qarapchi) | LOCAL | Qarapchi | Yordamchi sifatida | NEW |
| 22 | Kitob va qo'llanma chop etish | Chop etish va skanerlash (Qarapchi) | LOCAL | Qarapchi | Yordamchi sifatida | NEW |
| 23 | Excel jadval tayyorlash | Excel va Office | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 24 | Excel formulalari va avtomatlashtirish | Excel va Office | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 25 | Grafik va hisobotlar | Excel va Office | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 26 | Taqdimot (PowerPoint) tayyorlash | Excel va Office | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 27 | Google Docs, Sheets va Forms | Excel va Office | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 28 | Tarjima xizmati | Matn va tarjima | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 29 | Matn yozish (kopirayting) | Matn va tarjima | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 30 | Matnni tahrirlash va xatolarni tuzatish | Matn va tarjima | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 31 | Lotin ↔ kirill o'girish | Matn va tarjima | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 32 | Qisqacha mazmun va referat | Matn va tarjima | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 33 | Logotip yaratish | Grafik dizayn | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 34 | Vizitka dizayni | Grafik dizayn | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 35 | Banner, afisha va flayer | Grafik dizayn | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 36 | Taklifnoma va tabriknoma | Grafik dizayn | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 37 | Brend uslubi (firma stili) | Grafik dizayn | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 38 | Menyu va narxnoma dizayni | Grafik dizayn | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 39 | Qadoq va yorliq dizayni | Grafik dizayn | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 40 | Foto retush | Foto va rasmlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 41 | Fonni olib tashlash yoki almashtirish | Foto va rasmlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 42 | Hujjat uchun rasm (3x4, viza) | Foto va rasmlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 43 | Eski rasmlarni tiklash | Foto va rasmlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 44 | Mahsulot rasmlarini tayyorlash | Foto va rasmlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 45 | Kollaj va fotokitob | Foto va rasmlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 46 | Video montaj | Video va audio | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 47 | Reels, Shorts va TikTok videolari | Video va audio | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 48 | Videoga subtitr qo'shish | Video va audio | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 49 | Audio tozalash va tahrirlash | Video va audio | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 50 | Audio va videoni matnga o'girish | Video va audio | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 51 | Video konvertatsiya va siqish | Video va audio | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 52 | Animatsiya va intro | Video va audio | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 53 | Instagram post va story dizayni | Ijtimoiy tarmoqlar va SMM | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 54 | Ijtimoiy tarmoq sahifasini ochish | Ijtimoiy tarmoqlar va SMM | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 55 | Kontent-reja va post matnlari | Ijtimoiy tarmoqlar va SMM | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 56 | YouTube kanal bezash | Ijtimoiy tarmoqlar va SMM | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 57 | Google va Yandex xaritaga qo'shish | Ijtimoiy tarmoqlar va SMM | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 58 | Landing sahifa | Veb-saytlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 59 | Kompaniya sayti | Veb-saytlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 60 | Internet-do'kon | Veb-saytlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 61 | Saytni tuzatish va yangilash | Veb-saytlar | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 62 | WordPress sayt | Veb-saytlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 63 | SEO va Google'da ko'rinish | Veb-saytlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 64 | Telegram bot yaratish | Telegram va avtomatlashtirish | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 65 | Telegram kanal va guruh sozlash | Telegram va avtomatlashtirish | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 66 | Telegram Mini App | Telegram va avtomatlashtirish | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 67 | Ish jarayonlarini avtomatlashtirish | Telegram va avtomatlashtirish | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 68 | Python skript yozish | Dasturlash | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 69 | Kompyuter dasturi yaratish | Dasturlash | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 70 | Mobil ilova | Dasturlash | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 71 | Dasturdagi xatolarni tuzatish | Dasturlash | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 72 | Talabalarga dasturlashni tushuntirish | Dasturlash | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | MODIFY |
| 73 | Ma'lumot kiritish | Ma'lumotlar bilan ishlash | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 74 | Ma'lumotlarni tozalash | Ma'lumotlar bilan ishlash | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 75 | Ma'lumotlar bazasi yaratish | Ma'lumotlar bilan ishlash | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 76 | Ma'lumotlar tahlili | Ma'lumotlar bilan ishlash | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 77 | Domen va hosting ulash | Hosting, domen va pochta | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 78 | Korporativ pochta (info@sizning.uz) | Hosting, domen va pochta | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 79 | Serverga joylashtirish | Hosting, domen va pochta | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 80 | SSL va sayt xavfsizligi | Hosting, domen va pochta | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 81 | Click / Payme to'lovini ulash | Integratsiyalar va to'lovlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 82 | Tizimlarni bir-biriga ulash | Integratsiyalar va to'lovlar | ONLINE | Butun O'zbekiston | Ha (inson tekshiradi) | KEEP |
| 83 | SMS va avtomatik xabarnomalar | Integratsiyalar va to'lovlar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 84 | AI yordamchi (chatbot) | Sun'iy intellekt xizmatlari | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 85 | AI yordamida rasm yaratish | Sun'iy intellekt xizmatlari | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 86 | AI yordamida matn tayyorlash | Sun'iy intellekt xizmatlari | DISABLED | — | Ha (inson tekshiradi) | ARCHIVE |
| 87 | ChatGPT va AI vositalaridan foydalanishni o'rgatish | Sun'iy intellekt xizmatlari | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 88 | my.gov.uz da ariza topshirish | Onlayn arizalar va ro'yxatdan o'tish | REMOTE | Butun O'zbekiston | Yordamchi sifatida | MODIFY |
| 89 | ERI (elektron imzo) o'rnatish | Onlayn arizalar va ro'yxatdan o'tish | REMOTE | Butun O'zbekiston | Yordamchi sifatida | MODIFY |
| 90 | Viza va xorij anketalarini to'ldirish | Onlayn arizalar va ro'yxatdan o'tish | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 91 | Green Card (DV Lottery) anketasi | Onlayn arizalar va ro'yxatdan o'tish | ONLINE | Butun O'zbekiston | Yordamchi sifatida | MODIFY |
| 92 | O'qishga onlayn hujjat topshirish | Onlayn arizalar va ro'yxatdan o'tish | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 93 | Onlayn kabinet va akkauntlarni ochish | Onlayn arizalar va ro'yxatdan o'tish | REMOTE | Butun O'zbekiston | Yordamchi sifatida | MODIFY |
| 94 | Uzum va marketplace'da do'kon ochish | Onlayn arizalar va ro'yxatdan o'tish | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 95 | Kompyuter savodxonligi darslari | Kompyuter darslari va maslahat | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 96 | Word, Excel, PowerPoint darslari | Kompyuter darslari va maslahat | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 97 | Dasturlashni o'rganish | Kompyuter darslari va maslahat | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 98 | IT maslahat | Kompyuter darslari va maslahat | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 99 | Kompyuter tanlashda yordam | Kompyuter darslari va maslahat | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |
| 100 | Maxsus raqamli vazifa | Boshqa raqamli vazifalar | ONLINE | Butun O'zbekiston | Yordamchi sifatida | KEEP |

## Buyurtma holatlari (mavjud tizim saqlandi)
To'lov tarixi va bazadagi himoyalar buzilmasligi uchun holatlar qayta nomlanmadi. So'ralgan nomlar mavjud holatlarga quyidagicha mos keladi:

| So'ralgan | Mavjud holat |
|---|---|
| PENDING | SUBMITTED |
| REVIEWING | UNDER_REVIEW |
| QUOTED | QUOTATION_PENDING |
| AWAITING_PAYMENT | DEPOSIT_PENDING / FINAL_PAYMENT_PENDING |
| PAID | PAID / PARTIALLY_PAID |
| IN_PROGRESS | QUEUED / MANUAL_PROCESSING / AI_* |
| READY | READY_FOR_DELIVERY (yoki ish tugab, qolgan to'lov kutilayotgan holat) |
| HANDOVER_PENDING | READY_FOR_DELIVERY + topshirish holati (`handover_status`) |
| COMPLETED | DELIVERED → CLOSED |
| REVISION_REQUESTED, CANCELLED, REFUNDED | o'zgarishsiz |

Topshirish holati (`handover_status`) to'lov va buyurtma holatidan **alohida** saqlanadi. Uning qiymatlari:
- **Pickup:** WAITING → READY_FOR_PICKUP → HANDED_OVER
- **Meetup:** PROPOSED_BY_CUSTOMER ⇄ PROPOSED_BY_ADMIN → CONFIRMED → HANDED_OVER

Buyurtmani "topshirildi" deb belgilash uchun ikki shart bor:
- buyurtma to'liq to'langan bo'lishi kerak (naqd pul "Qo'lda to'lov" orqali qayd etiladi; bitta ma'lumotnoma ikki marta hisoblanmaydi);
- meetup bo'lsa, uchrashuv tasdiqlangan bo'lishi kerak.

## Maxfiylik
Uy manzili (olib ketish manzili) faqat **Admin → Hududlar** sahifasida saqlanadi. U hech qanday ommaviy API'da qaytarilmaydi. Mijoz manzilni faqat o'zining pickup buyurtmasida, ish tayyor bo'lganidan keyin ko'radi; topshirilgandan keyin manzil yana yashiriladi. Audit jurnaliga manzilning o'zi yozilmaydi, faqat o'zgargani qayd etiladi.

## Prices

Every catalogue service has a suggested starting price in `backend/app/catalog_prices.py`
(UZS, chosen in November 2026 from public listings for similar work in Uzbekistan and set a
little below Tashkent agency rates). Suggestions are only applied to services that still have
no price; a price the owner set is never overwritten.

* **Admin → Prices** shows every service grouped by category, with quick editing of the
  price type (fixed, per unit, volume discount, "from", individual), price, unit, quantity
  limits, volume discounts and deposit. "Use suggestion" restores the suggested price for one
  service; "Use suggested prices for unpriced" fills every unpriced service at once.
* CLI: `python -m app.cli apply-prices` does the same as the "fill unpriced" button.
* "From" prices (`STARTING_FROM`) are always confirmed by the owner in a quotation.
* Printing in Qarapchi is priced per sheet for black & white; colour is confirmed in the quote.
