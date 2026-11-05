# VIMORA xato kodlari

Har bir xato xabari oxirida kod ko'rsatiladi, masalan: *(Xato kodi: E7003 · SERVICE_NOT_IN_AREA)*.
Server xatolarida qo'shimcha `ID` ham chiqadi — u bilan server jurnalidan aynan shu so'rovni topish mumkin (`docker compose logs backend-api | findstr <ID>`).


## 1xxx — Umumiy va kirish

| Raqam | Kod | Ma'nosi |
|---|---|---|
| E1000 | `BAD_REQUEST` | So'rov noto'g'ri tuzilgan. |
| E1001 | `VALIDATION_ERROR` | Ayrim maydonlarni tekshiring. |
| E1002 | `UNAUTHORIZED` | Davom etish uchun kiring. |
| E1003 | `FORBIDDEN` | Bunga ruxsatingiz yo'q. |
| E1004 | `NOT_FOUND` | Topilmadi. |
| E1005 | `CONFLICT` | Amalni hozir bajarib bo'lmaydi — ma'lumot o'zgargan bo'lishi mumkin. Sahifani yangilang. |
| E1006 | `RATE_LIMITED` | Juda ko'p urinish. Biroz kuting. |
| E1007 | `CSRF_FAILED` | Seans muddati tugadi. Sahifani yangilab, qayta urinib ko'ring. |
| E1008 | `MAINTENANCE` | VIMORA da texnik ishlar olib borilmoqda. Birozdan keyin urinib ko'ring. |
| E1009 | `PAYLOAD_TOO_LARGE` | Yuborilgan ma'lumot juda katta. |
| E1010 | `METHOD_NOT_ALLOWED` | Bu amal qo'llab-quvvatlanmaydi. |
| E1011 | `HTTP_ERROR` | So'rovni bajarib bo'lmadi. |
| E1012 | `INTERNAL_ERROR` | Bizning tomonda kutilmagan xatolik yuz berdi. |
| E1013 | `CONFIGURATION_REQUIRED` | Bu funksiya hali sozlanmagan. |
| E1014 | `IDEMPOTENCY_CONFLICT` | Bu so'rov allaqachon boshqa ma'lumot bilan yuborilgan. |
| E1015 | `DUPLICATE` | Bunday yozuv allaqachon mavjud. |
| E1101 | `INVALID_CREDENTIALS` | Email yoki parol noto'g'ri. |
| E1102 | `EMAIL_NOT_VERIFIED` | Avval email manzilingizni tasdiqlang. |
| E1103 | `WEAK_PASSWORD` | Parol yetarlicha kuchli emas. |
| E1104 | `TOKEN_INVALID` | Havola noto'g'ri yoki allaqachon ishlatilgan. |
| E1105 | `LINK_EXPIRED` | Havolaning muddati tugagan. Yangisini so'rang. |
| E1106 | `REGISTRATION_CLOSED` | Ro'yxatdan o'tish vaqtincha yopiq. |
| E1107 | `MFA_REQUIRED` | Ikki bosqichli tasdiqlash kodi kerak. |
| E1108 | `MFA_PENDING` | Kirishni tasdiqlash kodi bilan yakunlang. |
| E1109 | `MFA_INVALID` | Tasdiqlash kodi noto'g'ri. |
| E1110 | `MFA_NOT_SETUP` | Ikki bosqichli himoya hali sozlanmagan. |
| E1111 | `MFA_NOT_ENABLED` | Ikki bosqichli himoya yoqilmagan. |
| E1112 | `MFA_ALREADY_ENABLED` | Ikki bosqichli himoya allaqachon yoqilgan. |
| E1113 | `LAST_SUPER_ADMIN` | Oxirgi bosh administratorni o'chirib yoki pasaytirib bo'lmaydi. |
| E1114 | `FORBIDDEN_TARGET` | Bu foydalanuvchiga nisbatan bu amalga ruxsat yo'q. |
| E1116 | `EMAIL_NOT_CONFIGURED` | Serverda email (SMTP) sozlanmagan. Lokal kompyuterda tasdiqlash havolasi ekranda ko'rsatiladi; administrator ham qo'lda tasdiqlashi mumkin. |
| E1117 | `EMAIL_DELIVERY_FAILED` | Emailni yuborib bo'lmadi. |
| E1115 | `FORBIDDEN_FOR_OWNER` | Loyiha egasiga nisbatan bu amal mumkin emas. |

## 2xxx — Buyurtmalar

| Raqam | Kod | Ma'nosi |
|---|---|---|
| E2001 | `SERVICE_UNAVAILABLE` | Bu xizmat hozir buyurtma qabul qilmayapti. |
| E2002 | `MISSING_REQUIREMENT` | Majburiy maydon to'ldirilmagan. |
| E2003 | `INVALID_REQUIREMENT` | Maydonga noto'g'ri qiymat kiritilgan. |
| E2004 | `INVALID_DEADLINE` | Muddat kelajakdagi sana bo'lishi kerak. |
| E2005 | `DESCRIPTION_TOO_SHORT` | Vazifani batafsilroq yozing (kamida 30 ta belgi). |
| E2006 | `INVALID_QUANTITY` | Miqdor ruxsat etilgan chegaradan tashqarida. |
| E2007 | `INVALID_ADDON` | Tanlangan qo'shimcha xizmat mavjud emas. |
| E2008 | `ATTACHMENTS_NOT_ALLOWED` | Bu xizmatga fayl biriktirib bo'lmaydi. |
| E2009 | `FILE_REQUIRED` | Bu xizmat uchun fayl biriktirish majburiy. |
| E2010 | `INVALID_STATE` | Buyurtma hozirgi holatida bu amalni bajarib bo'lmaydi. |
| E2011 | `INVALID_STATUS_TRANSITION` | Buyurtmani bu holatga o'tkazib bo'lmaydi. |
| E2012 | `NOT_CANCELLABLE` | Bu buyurtmani endi bekor qilib bo'lmaydi. |
| E2013 | `QUOTATION_CLOSED` | Bu narx taklifi endi amal qilmaydi. |
| E2014 | `QUOTATION_EXPIRED` | Narx taklifining muddati tugagan. |
| E2015 | `REVISION_LIMIT` | Tuzatishlar soni chegarasiga yetdingiz. |
| E2016 | `ALREADY_REVIEWED` | Siz allaqachon baho qoldirgansiz. |
| E2017 | `INVALID_RATING` | Baho 1 dan 5 gacha bo'lishi kerak. |
| E2018 | `NO_REVIEW` | Bu buyurtmada sharh yo'q. |
| E2019 | `EMPTY_MESSAGE` | Xabar bo'sh bo'lmasligi kerak. |
| E2020 | `NO_APPROVED_DELIVERABLE` | Avval kamida bitta natija faylini tasdiqlang. |
| E2021 | `ALREADY_RELEASED` | Natija allaqachon topshirilgan. |
| E2022 | `USE_DEDICATED_ACTION` | Buning uchun alohida tugmadan foydalaning. |
| E2023 | `INVALID_LINE_ITEM` | Narx qatorlaridan biri noto'g'ri. |

## 3xxx — To'lovlar va promokodlar

| Raqam | Kod | Ma'nosi |
|---|---|---|
| E3001 | `NO_PAYMENT_DUE` | Hozir to'lanadigan summa yo'q. |
| E3002 | `ALREADY_PAID` | Bu summa allaqachon to'langan. |
| E3003 | `AMOUNT_MISMATCH` | Summa oldindan to'lov yoki qolgan summaga teng bo'lishi kerak. |
| E3004 | `DUPLICATE_PAYMENT` | Bu to'lov allaqachon qayd etilgan. |
| E3005 | `INVALID_AMOUNT` | Summa noto'g'ri. |
| E3006 | `INVALID_CURRENCY` | Valyuta noto'g'ri. |
| E3007 | `CURRENCY_NOT_SUPPORTED` | Bu to'lov usuli tanlangan valyutani qabul qilmaydi. |
| E3008 | `PROVIDER_UNAVAILABLE` | Bu to'lov usuli hozir ishlamayapti. |
| E3009 | `PROVIDER_ERROR` | To'lov tizimi xato qaytardi. Birozdan keyin urinib ko'ring. |
| E3010 | `UNKNOWN_PROVIDER` | Noma'lum to'lov usuli. |
| E3011 | `REFUND_TOO_LARGE` | Qaytariladigan summa to'langan summadan katta. |
| E3012 | `BALANCE_OUTSTANDING` | Avval qolgan summa to'lanishi (yoki naqd qayd etilishi) kerak. |
| E3013 | `INVALID_PROMO` | Promokod noto'g'ri. |
| E3014 | `PROMO_INVALID` | Promokod noto'g'ri. |
| E3015 | `PROMO_EXPIRED` | Promokod muddati tugagan. |
| E3016 | `PROMO_EXHAUSTED` | Promokod ishlatib bo'lingan. |
| E3017 | `PROMO_MINIMUM` | Buyurtma summasi promokod uchun yetarli emas. |
| E3018 | `PROMO_NOT_APPLICABLE` | Promokod bu xizmatga tegishli emas. |
| E3019 | `PRICING_ERROR` | Narxni hisoblab bo'lmadi. |
| E3020 | `INVALID_PRICING` | Narx sozlamalari noto'g'ri. |

## 4xxx — Fayllar

| Raqam | Kod | Ma'nosi |
|---|---|---|
| E4001 | `UPLOAD_EMPTY` | Fayl bo'sh. |
| E4002 | `UPLOAD_TOO_LARGE` | Fayl hajmi juda katta. |
| E4003 | `UPLOAD_TYPE_NOT_ALLOWED` | Bu turdagi faylni yuklab bo'lmaydi. |
| E4004 | `UPLOAD_CONTENT_MISMATCH` | Fayl ichi kengaytmasiga mos emas. |
| E4005 | `UPLOAD_CONTENT_REJECTED` | Fayl xavfsizlik tekshiruvidan o'tmadi. |
| E4006 | `UPLOAD_MALWARE` | Faylda zararli kod topildi. |
| E4007 | `STORAGE_QUOTA_EXCEEDED` | Fayllar uchun joy limiti tugagan. |
| E4008 | `ATTACHMENT_NOT_FOUND` | Fayl topilmadi yoki sizga tegishli emas. |
| E4009 | `NO_FILES_SELECTED` | Fayl tanlanmagan. |

## 5xxx — Sun'iy intellekt

| Raqam | Kod | Ma'nosi |
|---|---|---|
| E5001 | `AI_NOT_ELIGIBLE` | Bu buyurtmani AI bajara olmaydi. |
| E5002 | `AI_BUDGET_EXCEEDED` | AI uchun ajratilgan byudjet tugagan. |
| E5003 | `AI_DAILY_LIMIT` | AI kunlik limiti tugagan. |
| E5004 | `AI_ATTEMPTS_EXCEEDED` | AI urinishlari soni chegarasiga yetildi. |
| E5005 | `UNKNOWN_CAPABILITY` | Noma'lum AI imkoniyati. |
| E5006 | `CAPABILITY_REQUIRED` | AI uchun imkoniyat turini tanlang. |

## 6xxx — Katalog va admin

| Raqam | Kod | Ma'nosi |
|---|---|---|
| E6001 | `DUPLICATE_SLUG` | Bu kod (slug) band. Boshqasini yozing. |
| E6002 | `CATEGORY_IN_USE` | Yo'nalishda xizmatlar bor, uni o'chirib bo'lmaydi. |
| E6003 | `SERVICE_IN_USE` | Xizmatda buyurtmalar bor, uni o'chirib bo'lmaydi. |
| E6004 | `UNKNOWN_SETTING` | Noma'lum sozlama. |
| E6005 | `INVALID_SETTING` | Sozlama qiymati noto'g'ri. |
| E6006 | `INVALID_PROVIDER` | Xizmat ko'rsatuvchi xodim bo'lishi kerak. |

## 7xxx — Mahalliy xizmatlar (Qarapchi)

| Raqam | Kod | Ma'nosi |
|---|---|---|
| E7001 | `AREA_REQUIRED` | Hududingizni tanlang. |
| E7002 | `INVALID_AREA` | Tanlangan hudud mavjud emas yoki yopiq. |
| E7003 | `SERVICE_NOT_IN_AREA` | Bu xizmat siz tanlagan hududda mavjud emas. |
| E7004 | `AREA_NOT_LOCAL` | Bu hududda mahalliy xizmatlar yoqilmagan. |
| E7005 | `HANDOVER_REQUIRED` | Olib ketish yoki uchrashuvni tanlang. |
| E7006 | `HANDOVER_NOT_APPLICABLE` | Olib ketish/uchrashuv faqat mahalliy xizmatlar uchun. |
| E7007 | `INVALID_MEETUP` | Uchrashuv joyi va kelajakdagi vaqtni kiriting. |
| E7008 | `MEETUP_NOT_CONFIRMED` | Avval uchrashuv joyi va vaqtini tasdiqlang. |
| E7009 | `NOT_LOCAL` | Bu buyurtmada jismoniy topshirish yo'q. |
| E7010 | `NOT_MEETUP` | Bu buyurtma uchrashuv orqali topshirilmaydi. |
| E7011 | `USE_HANDOVER` | Mahalliy buyurtma «Topshirildi» tugmasi bilan yakunlanadi. |
