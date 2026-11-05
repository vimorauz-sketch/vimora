"""Default VIMORA catalog: computer-related services people actually look for.

Prices are not set here: new services get the owner's suggested starting prices from
app/catalog_prices.py (or stay an individual quote), editable in Admin -> Prices.
Format: (slug, category, (uz, en, ru) name, (uz, en, ru) short description, ai capability)
"""

from __future__ import annotations


def T(uz: str, en: str, ru: str) -> dict:
    return {"uz": uz, "en": en, "ru": ru}


CATEGORIES: list[tuple[str, str, dict]] = [
    ("computer-assistance", "monitor-cog", T("Kompyuter yordami", "Computer help", "Компьютерная помощь")),
    ("documents-pdf", "file-text", T("Hujjatlar va PDF", "Documents & PDF", "Документы и PDF")),
    ("printing-local", "printer", T("Chop etish va skanerlash (Qarapchi)", "Printing & scanning (Qarapchi)", "Печать и сканирование (Карапчи)")),
    ("excel-office", "sheet", T("Excel va Office", "Excel & Office", "Excel и Office")),
    ("text-translation", "languages", T("Matn va tarjima", "Text & translation", "Тексты и перевод")),
    ("graphic-design", "pen-tool", T("Grafik dizayn", "Graphic design", "Графический дизайн")),
    ("image-processing", "image", T("Foto va rasmlar", "Photos & images", "Фото и изображения")),
    ("video-audio", "clapperboard", T("Video va audio", "Video & audio", "Видео и аудио")),
    ("smm-social-media", "instagram", T("Ijtimoiy tarmoqlar va SMM", "Social media & SMM", "Соцсети и SMM")),
    ("web-development", "globe", T("Veb-saytlar", "Websites", "Веб-сайты")),
    ("telegram-automation", "send", T("Telegram va avtomatlashtirish", "Telegram & automation", "Telegram и автоматизация")),
    ("software-development", "code-xml", T("Dasturlash", "Software development", "Разработка ПО")),
    ("data-processing", "database", T("Ma'lumotlar bilan ishlash", "Data processing", "Работа с данными")),
    ("hosting-deployment", "server", T("Hosting, domen va pochta", "Hosting, domains & email", "Хостинг, домены и почта")),
    ("api-integration", "plug", T("Integratsiyalar va to'lovlar", "Integrations & payments", "Интеграции и платежи")),
    ("ai-services", "brain-circuit", T("Sun'iy intellekt xizmatlari", "AI services", "Услуги ИИ")),
    ("online-services", "landmark", T("Onlayn arizalar va ro'yxatdan o'tish", "Online applications & sign-ups", "Онлайн-заявки и регистрации")),
    ("lessons-consulting", "graduation-cap", T("Kompyuter darslari va maslahat", "Computer lessons & advice", "Уроки и консультации")),
    ("custom-digital-tasks", "sparkles", T("Boshqa raqamli vazifalar", "Other digital tasks", "Другие цифровые задачи")),
]

S = tuple  # readability alias

SERVICES: list[tuple] = [
    # --- Computer help -------------------------------------------------------------
    S(("windows-install", "computer-assistance", T("Windows o'rnatish va sozlash", "Windows installation & setup", "Установка и настройка Windows"),
       T("Windows 10/11 ni qayta o'rnatish, drayverlar va kerakli dasturlar bilan", "Clean Windows 10/11 install with drivers and essential apps", "Чистая установка Windows 10/11 с драйверами и программами"), None)),
    S(("drivers-install", "computer-assistance", T("Drayverlarni o'rnatish", "Driver installation", "Установка драйверов"),
       T("Ovoz, video, Wi-Fi, printer va boshqa qurilmalar drayverlari", "Sound, video, Wi-Fi, printer and other device drivers", "Драйверы звука, видео, Wi-Fi, принтера и других устройств"), None)),
    S(("virus-removal", "computer-assistance", T("Viruslarni tozalash", "Virus & malware removal", "Удаление вирусов"),
       T("Kompyuterni viruslar va reklama dasturlaridan tozalash, himoyani sozlash", "Remove viruses and adware, set up protection", "Очистка от вирусов и рекламы, настройка защиты"), None)),
    S(("pc-speedup", "computer-assistance", T("Kompyuterni tezlashtirish", "Speed up your computer", "Ускорение компьютера"),
       T("Sekin ishlayotgan kompyuterni tozalash va optimallashtirish", "Clean up and optimise a slow computer", "Очистка и оптимизация медленного компьютера"), None)),
    S(("software-install", "computer-assistance", T("Dasturlarni o'rnatish", "Software installation", "Установка программ"),
       T("Office, brauzerlar, grafik va ish dasturlarini o'rnatish va sozlash", "Install and configure Office, browsers, design and work apps", "Установка Office, браузеров, графических и рабочих программ"), None)),
    S(("data-recovery", "computer-assistance", T("Ma'lumotlarni tiklash", "Data recovery", "Восстановление данных"),
       T("O'chib ketgan fayllarni fleshka, disk yoki xotira kartadan tiklash", "Recover deleted files from USB drives, disks and memory cards", "Восстановление удалённых файлов с флешек, дисков и карт памяти"), None)),
    S(("printer-setup", "computer-assistance", T("Printer va skanerni sozlash", "Printer & scanner setup", "Настройка принтера и сканера"),
       T("Printer, skaner va MFU ni ulash, drayver va tarmoqqa sozlash", "Connect printers, scanners and MFPs, drivers and network setup", "Подключение принтеров, сканеров и МФУ"), None)),
    S(("wifi-network-setup", "computer-assistance", T("Wi-Fi va tarmoqni sozlash", "Wi-Fi & network setup", "Настройка Wi-Fi и сети"),
       T("Router, Wi-Fi parol, uy yoki ofis tarmog'ini sozlash", "Router, Wi-Fi password, home or office network", "Роутер, пароль Wi-Fi, домашняя или офисная сеть"), None)),
    S(("backup-setup", "computer-assistance", T("Zaxira nusxa sozlash", "Backup setup", "Настройка резервного копирования"),
       T("Fayllaringizni bulut yoki diskka avtomatik saqlashni sozlash", "Automatic backups of your files to cloud or disk", "Автоматическое копирование файлов в облако или на диск"), None)),
    S(("remote-help", "computer-assistance", T("Masofaviy kompyuter yordami", "Remote computer help", "Удалённая компьютерная помощь"),
       T("Muammoni masofadan ulanib hal qilish (AnyDesk va h.k.)", "We connect remotely and fix the issue (AnyDesk etc.)", "Подключаемся удалённо и решаем проблему (AnyDesk и др.)"), None)),
    S(("phone-setup", "computer-assistance", T("Telefon sozlash va ma'lumot ko'chirish", "Phone setup & data transfer", "Настройка телефона и перенос данных"),
       T("Yangi telefonni sozlash, kontakt va rasmlarni ko'chirish", "Set up a new phone, move contacts and photos", "Настройка нового телефона, перенос контактов и фото"), None)),
    # --- Documents -----------------------------------------------------------------
    S(("typing", "documents-pdf", T("Matn terish", "Typing services", "Набор текста"),
       T("Qo'lyozma, rasm yoki skanerdan matnni kompyuterda terish", "Type text from handwriting, photos or scans", "Набор текста с рукописи, фото или скана"), "document_writing")),
    S(("word-formatting", "documents-pdf", T("Word hujjatini rasmiylashtirish", "Word document formatting", "Оформление документов Word"),
       T("Diplom, kurs ishi, referat va rasmiy hujjatlarni talab bo'yicha rasmiylashtirish", "Format theses, coursework and official documents to requirements", "Оформление дипломов, курсовых и официальных документов"), None)),
    S(("cv-resume", "documents-pdf", T("Rezyume (CV) tayyorlash", "CV / résumé writing", "Составление резюме"),
       T("Ish uchun zamonaviy rezyume — o'zbek, rus yoki ingliz tilida", "A modern CV in Uzbek, Russian or English", "Современное резюме на узбекском, русском или английском"), "document_writing")),
    S(("cover-letter", "documents-pdf", T("Motivatsion xat va ariza yozish", "Cover & motivation letters", "Мотивационные и сопроводительные письма"),
       T("Ish, o'qish yoki grant uchun xat va arizalar", "Letters and applications for jobs, study or grants", "Письма и заявления для работы, учёбы или грантов"), "document_writing")),
    S(("pdf-convert", "documents-pdf", T("PDF konvertatsiya va tahrirlash", "PDF conversion & editing", "Конвертация и редактирование PDF"),
       T("PDF ↔ Word/Excel, birlashtirish, ajratish, siqish, tahrirlash", "PDF ↔ Word/Excel, merge, split, compress, edit", "PDF ↔ Word/Excel, объединение, разделение, сжатие"), None)),
    S(("scan-digitize", "documents-pdf", T("Hujjatlarni raqamlashtirish", "Document digitisation", "Оцифровка документов"),
       T("Skan qilingan hujjatlarni tahrirlanadigan matnga aylantirish (OCR)", "Turn scanned documents into editable text (OCR)", "Преобразование сканов в редактируемый текст (OCR)"), None)),
    S(("contracts-templates", "documents-pdf", T("Shartnoma va blanka shablonlari", "Contract & form templates", "Шаблоны договоров и бланков"),
       T("Hujjat, blanka, dalolatnoma va hisob-faktura shablonlarini tayyorlash", "Templates for documents, forms, acts and invoices", "Шаблоны документов, бланков, актов и счетов"), "document_writing")),
    # --- Printing & scanning: LOCAL, Qarapchi only (one Canon PIXMA G3410: colour/B&W print, scan, copy; A4) ----
    S(("document-printing", "printing-local", T("Hujjat chop etish (rangli yoki oq-qora)", "Document printing (colour or B&W)", "Печать документов (цветная или ч/б)"),
       T("PDF, Word va rasmlarni A4 formatda chop etish. Faqat Qarapchi qishlog'ida", "Print PDF, Word files and images on A4. Qarapchi village only", "Печать PDF, Word и изображений формата A4. Только Карапчи"), None)),
    S(("photocopy", "printing-local", T("Hujjat nusxalash (kserokopiya)", "Photocopying", "Ксерокопия документов"),
       T("Pasport, guvohnoma va boshqa hujjatlardan A4 nusxa. Faqat Qarapchi qishlog'ida", "A4 copies of passports, certificates and other papers. Qarapchi village only", "Копии паспорта, свидетельств и других документов A4. Только Карапчи"), None)),
    S(("scanning", "printing-local", T("Hujjatlarni skanerlash", "Document scanning", "Сканирование документов"),
       T("Qog'oz hujjatlarni skanerlab PDF yoki rasm qilib berish. Faqat Qarapchi qishlog'ida", "Scan paper documents to PDF or image files. Qarapchi village only", "Сканирование бумажных документов в PDF или изображения. Только Карапчи"), None)),
    S(("book-printing", "printing-local", T("Kitob va qo'llanma chop etish", "Book & manual printing", "Печать книг и пособий"),
       T("Ko'p sahifali kitob, qo'llanma yoki referatni A4 da chop etish (muqovalash hozircha yo'q). Faqat Qarapchi", "Print multi-page books, manuals or essays on A4 (no binding yet). Qarapchi only", "Печать многостраничных книг и пособий A4 (без переплёта). Только Карапчи"), None)),
    # --- Excel & Office ------------------------------------------------------------
    S(("excel-tables", "excel-office", T("Excel jadval tayyorlash", "Excel spreadsheets", "Таблицы Excel"),
       T("Hisob-kitob, ombor, savdo va xodimlar jadvallari formulalar bilan", "Spreadsheets for accounting, stock, sales and staff with formulas", "Таблицы учёта, склада, продаж и персонала с формулами"), "data_transformation")),
    S(("excel-formulas-automation", "excel-office", T("Excel formulalari va avtomatlashtirish", "Excel formulas & automation", "Формулы и автоматизация Excel"),
       T("Murakkab formulalar, makroslar va avtomatik hisobotlar", "Advanced formulas, macros and automatic reports", "Сложные формулы, макросы и автоматические отчёты"), None)),
    S(("excel-charts-reports", "excel-office", T("Grafik va hisobotlar", "Charts & reports", "Графики и отчёты"),
       T("Ma'lumotlaringizdan diagramma, dashboard va hisobot yasash", "Charts, dashboards and reports from your data", "Диаграммы, дашборды и отчёты из ваших данных"), None)),
    S(("powerpoint-presentation", "excel-office", T("Taqdimot (PowerPoint) tayyorlash", "PowerPoint presentations", "Презентации PowerPoint"),
       T("Dars, himoya, biznes yoki loyiha uchun chiroyli taqdimot", "Presentations for classes, defences, business or projects", "Презентации для уроков, защиты, бизнеса и проектов"), None)),
    S(("google-workspace", "excel-office", T("Google Docs, Sheets va Forms", "Google Docs, Sheets & Forms", "Google Docs, Sheets и Forms"),
       T("Onlayn jadval, so'rovnoma va hamkorlikdagi hujjatlarni sozlash", "Online sheets, surveys and shared documents", "Онлайн-таблицы, опросы и совместные документы"), None)),
    # --- Text & translation ---------------------------------------------------------
    S(("translation", "text-translation", T("Tarjima xizmati", "Translation", "Перевод"),
       T("O'zbek, rus, ingliz va boshqa tillar o'rtasida matn tarjimasi", "Translation between Uzbek, Russian, English and more", "Перевод между узбекским, русским, английским и др."), "translation")),
    S(("copywriting", "text-translation", T("Matn yozish (kopirayting)", "Copywriting", "Копирайтинг"),
       T("Sayt, reklama, mahsulot tavsifi va postlar uchun matnlar", "Texts for websites, ads, product descriptions and posts", "Тексты для сайтов, рекламы, описаний товаров и постов"), "document_writing")),
    S(("proofreading", "text-translation", T("Matnni tahrirlash va xatolarni tuzatish", "Proofreading & editing", "Редактура и корректура"),
       T("Imlo, uslub va mazmunni tekshirish va tuzatish", "Check and fix spelling, style and clarity", "Проверка и исправление орфографии и стиля"), "document_writing")),
    S(("transliteration", "text-translation", T("Lotin ↔ kirill o'girish", "Latin ↔ Cyrillic conversion", "Перевод латиница ↔ кириллица"),
       T("O'zbek matnini lotin va kirill alifbolari orasida o'girish", "Convert Uzbek text between Latin and Cyrillic scripts", "Перевод узбекского текста между латиницей и кириллицей"), "translation")),
    S(("summary-report", "text-translation", T("Qisqacha mazmun va referat", "Summaries & reports", "Конспекты и рефераты"),
       T("Katta hujjat yoki kitobning qisqa mazmuni, referat tayyorlash", "Summaries of long documents, reports and essays", "Краткое содержание документов, рефераты"), "summarization")),
    # --- Graphic design --------------------------------------------------------------
    S(("logo-design", "graphic-design", T("Logotip yaratish", "Logo design", "Создание логотипа"),
       T("Biznesingiz uchun original logotip va uning variantlari", "An original logo for your business with variations", "Оригинальный логотип для вашего бизнеса"), None)),
    S(("business-card", "graphic-design", T("Vizitka dizayni", "Business card design", "Дизайн визиток"),
       T("Bosmaga tayyor zamonaviy vizitka", "Print-ready modern business cards", "Современные визитки, готовые к печати"), None)),
    S(("banner-poster", "graphic-design", T("Banner, afisha va flayer", "Banners, posters & flyers", "Баннеры, афиши и флаеры"),
       T("Ko'cha banneri, afisha, flayer va buklet dizayni", "Street banners, posters, flyers and booklets", "Баннеры, афиши, флаеры и буклеты"), None)),
    S(("invitation-design", "graphic-design", T("Taklifnoma va tabriknoma", "Invitations & greeting cards", "Приглашения и открытки"),
       T("To'y, tug'ilgan kun va tadbirlar uchun taklifnoma dizayni", "Invitations for weddings, birthdays and events", "Приглашения на свадьбы, дни рождения и события"), None)),
    S(("brand-identity", "graphic-design", T("Brend uslubi (firma stili)", "Brand identity", "Фирменный стиль"),
       T("Logotip, ranglar, shriftlar va blankalar to'plami", "Logo, colours, fonts and stationery set", "Логотип, цвета, шрифты и бланки"), None)),
    S(("menu-price-list", "graphic-design", T("Menyu va narxnoma dizayni", "Menu & price list design", "Дизайн меню и прайс-листов"),
       T("Kafe, restoran va do'konlar uchun menyu va narxnomalar", "Menus and price lists for cafes, restaurants and shops", "Меню и прайсы для кафе, ресторанов и магазинов"), None)),
    S(("packaging-label", "graphic-design", T("Qadoq va yorliq dizayni", "Packaging & label design", "Дизайн упаковки и этикеток"),
       T("Mahsulot qadog'i, yorliq va stiker dizayni", "Product packaging, labels and stickers", "Упаковка, этикетки и наклейки"), None)),
    # --- Photos & images ------------------------------------------------------------
    S(("photo-retouch", "image-processing", T("Foto retush", "Photo retouching", "Ретушь фото"),
       T("Yuz, teri, yorug'lik va rangni professional tuzatish", "Professional skin, light and colour retouching", "Профессиональная ретушь кожи, света и цвета"), None)),
    S(("background-removal", "image-processing", T("Fonni olib tashlash yoki almashtirish", "Background removal & replacement", "Удаление и замена фона"),
       T("Mahsulot yoki portret rasmlari uchun toza fon", "Clean backgrounds for product or portrait photos", "Чистый фон для фото товаров и портретов"), None)),
    S(("document-photo", "image-processing", T("Hujjat uchun rasm (3x4, viza)", "Document photos (3x4, visa)", "Фото на документы (3х4, виза)"),
       T("Pasport, viza va hujjatlar talablariga mos rasm tayyorlash", "Photos that meet passport, visa and ID requirements", "Фото по требованиям паспорта, визы и документов"), None)),
    S(("old-photo-restoration", "image-processing", T("Eski rasmlarni tiklash", "Old photo restoration", "Реставрация старых фото"),
       T("Yirtilgan, xira yoki oq-qora rasmlarni tiklash va ranglash", "Repair torn, faded or black-and-white photos and colourise", "Восстановление и раскрашивание старых фото"), None)),
    S(("product-photos", "image-processing", T("Mahsulot rasmlarini tayyorlash", "Product photo editing", "Обработка фото товаров"),
       T("Uzum, Instagram va marketplace uchun mahsulot rasmlari", "Product images for Uzum, Instagram and marketplaces", "Фото товаров для Uzum, Instagram и маркетплейсов"), None)),
    S(("collage-photobook", "image-processing", T("Kollaj va fotokitob", "Collages & photo books", "Коллажи и фотокниги"),
       T("Oilaviy, to'y yoki bitiruv rasmlaridan kollaj va albom", "Collages and albums from family, wedding or graduation photos", "Коллажи и альбомы из семейных и свадебных фото"), None)),
    # --- Video & audio --------------------------------------------------------------
    S(("video-editing", "video-audio", T("Video montaj", "Video editing", "Видеомонтаж"),
       T("To'y, tadbir, reklama va YouTube videolarini montaj qilish", "Editing for weddings, events, ads and YouTube", "Монтаж свадебных, рекламных и YouTube-видео"), None)),
    S(("reels-shorts", "video-audio", T("Reels, Shorts va TikTok videolari", "Reels, Shorts & TikTok videos", "Reels, Shorts и TikTok"),
       T("Ijtimoiy tarmoqlar uchun qisqa vertikal videolar", "Short vertical videos for social media", "Короткие вертикальные видео для соцсетей"), None)),
    S(("subtitles", "video-audio", T("Videoga subtitr qo'shish", "Video subtitles", "Субтитры к видео"),
       T("Videoni matnga o'girish va subtitr qo'shish (tarjima bilan)", "Transcribe and add subtitles, with translation if needed", "Расшифровка и субтитры, при необходимости с переводом"), None)),
    S(("audio-cleanup", "video-audio", T("Audio tozalash va tahrirlash", "Audio cleanup & editing", "Очистка и обработка аудио"),
       T("Shovqinni olib tashlash, ovozni yaxshilash, kesish va birlashtirish", "Noise removal, voice enhancement, cutting and joining", "Удаление шума, улучшение голоса, нарезка"), None)),
    S(("transcription", "video-audio", T("Audio va videoni matnga o'girish", "Audio & video transcription", "Расшифровка аудио и видео"),
       T("Intervyu, dars yoki yig'ilish yozuvini matnga aylantirish", "Turn interviews, lessons or meetings into text", "Расшифровка интервью, уроков и встреч"), None)),
    S(("video-convert", "video-audio", T("Video konvertatsiya va siqish", "Video conversion & compression", "Конвертация и сжатие видео"),
       T("Format o'zgartirish, hajmini kichraytirish, kesish", "Change format, reduce size, trim", "Смена формата, уменьшение размера, обрезка"), None)),
    S(("animation-intro", "video-audio", T("Animatsiya va intro", "Animations & intros", "Анимация и интро"),
       T("Logotip animatsiyasi, kanal intro va animatsion reklama", "Logo animation, channel intros and animated ads", "Анимация логотипа, интро и анимированная реклама"), None)),
    # --- Social media / SMM ---------------------------------------------------------
    S(("instagram-design", "smm-social-media", T("Instagram post va story dizayni", "Instagram post & story design", "Дизайн постов и сторис Instagram"),
       T("Sahifangiz uchun bir xil uslubdagi post va storylar", "Consistent posts and stories for your page", "Посты и сторис в едином стиле"), None)),
    S(("social-setup", "smm-social-media", T("Ijtimoiy tarmoq sahifasini ochish", "Social media page setup", "Оформление страниц в соцсетях"),
       T("Instagram, Telegram kanal va Facebook sahifasini ochish va bezash", "Create and design Instagram, Telegram channel and Facebook pages", "Создание и оформление Instagram, Telegram и Facebook"), None)),
    S(("content-plan", "smm-social-media", T("Kontent-reja va post matnlari", "Content plan & post copy", "Контент-план и тексты постов"),
       T("Bir oylik kontent-reja va tayyor post matnlari", "A monthly content plan with ready-to-post texts", "Контент-план на месяц и готовые тексты"), "document_writing")),
    S(("youtube-channel", "smm-social-media", T("YouTube kanal bezash", "YouTube channel design", "Оформление YouTube-канала"),
       T("Banner, avatar va video muqovalari (thumbnail)", "Banner, avatar and video thumbnails", "Баннер, аватар и обложки видео"), None)),
    S(("google-maps-business", "smm-social-media", T("Google va Yandex xaritaga qo'shish", "Add your business to Google & Yandex Maps", "Добавление на Google и Яндекс Карты"),
       T("Biznesingizni xaritalarda ro'yxatdan o'tkazish va sozlash", "Register and set up your business on maps", "Регистрация и настройка бизнеса на картах"), None)),
    # --- Websites -------------------------------------------------------------------
    S(("landing-page", "web-development", T("Landing sahifa", "Landing page", "Лендинг"),
       T("Mahsulot yoki xizmatingiz uchun bir sahifali sayt", "A one-page website for your product or service", "Одностраничный сайт для товара или услуги"), None)),
    S(("business-website", "web-development", T("Kompaniya sayti", "Business website", "Сайт компании"),
       T("Bir necha sahifali korporativ sayt, admin paneli bilan", "A multi-page company website with an admin panel", "Многостраничный корпоративный сайт с админкой"), None)),
    S(("online-store", "web-development", T("Internet-do'kon", "Online store", "Интернет-магазин"),
       T("Katalog, savat va onlayn to'lov bilan internet-do'kon", "Store with catalogue, cart and online payments", "Магазин с каталогом, корзиной и оплатой"), None)),
    S(("website-fixes", "web-development", T("Saytni tuzatish va yangilash", "Website fixes & updates", "Доработка и исправление сайта"),
       T("Mavjud saytdagi xatolarni tuzatish, yangi bo'lim qo'shish", "Fix bugs and add sections to an existing site", "Исправление ошибок и новые разделы"), "code_generation")),
    S(("wordpress", "web-development", T("WordPress sayt", "WordPress website", "Сайт на WordPress"),
       T("WordPress'da sayt yaratish, mavzu va plaginlarni sozlash", "WordPress site with theme and plugin setup", "Сайт на WordPress с настройкой темы и плагинов"), None)),
    S(("seo-basic", "web-development", T("SEO va Google'da ko'rinish", "SEO & Google visibility", "SEO и видимость в Google"),
       T("Saytni qidiruv tizimlariga moslashtirish va ro'yxatdan o'tkazish", "Optimise and register your site with search engines", "Оптимизация и регистрация сайта в поисковиках"), None)),
    # --- Telegram & automation ------------------------------------------------------
    S(("telegram-bot-development", "telegram-automation", T("Telegram bot yaratish", "Telegram bot development", "Разработка Telegram-бота"),
       T("Buyurtma, savdo, so'rovnoma yoki xizmat uchun Telegram bot", "Telegram bots for orders, sales, surveys or support", "Боты для заказов, продаж, опросов или поддержки"), "code_generation")),
    S(("telegram-channel-setup", "telegram-automation", T("Telegram kanal va guruh sozlash", "Telegram channel & group setup", "Настройка Telegram-канала и группы"),
       T("Kanal/guruh ochish, bezash, administrator botlarini ulash", "Create and design channels and groups, add admin bots", "Создание, оформление и боты-модераторы"), None)),
    S(("telegram-mini-app", "telegram-automation", T("Telegram Mini App", "Telegram Mini App", "Telegram Mini App"),
       T("Telegram ichida ochiladigan do'kon yoki xizmat ilovasi", "A store or service app that opens inside Telegram", "Магазин или сервис внутри Telegram"), None)),
    S(("process-automation", "telegram-automation", T("Ish jarayonlarini avtomatlashtirish", "Workflow automation", "Автоматизация процессов"),
       T("Takroriy ishlarni skript va xizmatlar bilan avtomatlashtirish", "Automate repetitive work with scripts and tools", "Автоматизация рутинных задач скриптами"), "code_generation")),
    # --- Software development -------------------------------------------------------
    S(("python-script", "software-development", T("Python skript yozish", "Python scripts", "Скрипты на Python"),
       T("Fayllar, ma'lumotlar yoki saytlar bilan ishlovchi skriptlar", "Scripts that work with files, data or websites", "Скрипты для работы с файлами, данными и сайтами"), "code_generation")),
    S(("desktop-app", "software-development", T("Kompyuter dasturi yaratish", "Desktop application", "Десктопная программа"),
       T("Hisob-kitob, ombor yoki kassa uchun oddiy kompyuter dasturi", "Simple desktop apps for accounting, stock or cash desk", "Простые программы для учёта, склада или кассы"), None)),
    S(("mobile-app", "software-development", T("Mobil ilova", "Mobile app", "Мобильное приложение"),
       T("Android va iOS uchun ilova", "Apps for Android and iOS", "Приложения для Android и iOS"), None)),
    S(("bug-fixing", "software-development", T("Dasturdagi xatolarni tuzatish", "Bug fixing", "Исправление ошибок в коде"),
       T("Mavjud kodingizdagi xatolarni topish va tuzatish", "Find and fix bugs in your existing code", "Поиск и исправление ошибок в коде"), "code_generation")),
    S(("student-projects", "software-development", T("Talabalar uchun dasturlash topshiriqlari", "Student programming help", "Помощь студентам с программированием"),
       T("Laboratoriya ishlari va loyihalarni tushuntirib yordam berish", "Help with labs and projects, with explanations", "Помощь с лабораторными и проектами с объяснениями"), "code_generation")),
    # --- Data ------------------------------------------------------------------------
    S(("data-entry", "data-processing", T("Ma'lumot kiritish", "Data entry", "Ввод данных"),
       T("Hujjat, jadval yoki saytlardan ma'lumotlarni kiritish va tartiblash", "Enter and organise data from documents, sheets or websites", "Ввод и упорядочивание данных из документов и сайтов"), "data_transformation")),
    S(("data-cleanup", "data-processing", T("Ma'lumotlarni tozalash", "Data cleanup", "Очистка данных"),
       T("Takrorlarni o'chirish, formatlash va bazani tartibga keltirish", "Remove duplicates, format and tidy up your data", "Удаление дублей, форматирование и упорядочивание"), "data_transformation")),
    S(("database-setup", "data-processing", T("Ma'lumotlar bazasi yaratish", "Database setup", "Создание базы данных"),
       T("Mijozlar, mahsulotlar yoki hisob uchun baza yaratish", "Databases for clients, products or records", "Базы данных клиентов, товаров и учёта"), None)),
    S(("data-analysis", "data-processing", T("Ma'lumotlar tahlili", "Data analysis", "Анализ данных"),
       T("Savdo va hisobotlarni tahlil qilib, xulosa va grafiklar tayyorlash", "Analyse sales and reports, with findings and charts", "Анализ продаж и отчётов с выводами и графиками"), "summarization")),
    # --- Hosting ---------------------------------------------------------------------
    S(("domain-hosting", "hosting-deployment", T("Domen va hosting ulash", "Domain & hosting setup", "Подключение домена и хостинга"),
       T("Domen sotib olish, hosting tanlash va saytni ulashda yordam", "Help buying a domain, choosing hosting and connecting your site", "Покупка домена, выбор хостинга и подключение сайта"), None)),
    S(("corporate-email", "hosting-deployment", T("Korporativ pochta (info@sizning.uz)", "Business email (info@yourdomain)", "Корпоративная почта"),
       T("Domeningizda pochta ochish va telefon/kompyuterga ulash", "Email on your domain, set up on phone and computer", "Почта на вашем домене с настройкой на устройствах"), None)),
    S(("vps-deployment", "hosting-deployment", T("Serverga joylashtirish", "Server deployment", "Развёртывание на сервере"),
       T("Sayt yoki botni VPS serverga joylashtirish va sozlash", "Deploy and configure your site or bot on a VPS", "Размещение сайта или бота на VPS"), None)),
    S(("ssl-security", "hosting-deployment", T("SSL va sayt xavfsizligi", "SSL & website security", "SSL и безопасность сайта"),
       T("HTTPS ulash, zaxira nusxa va asosiy himoyani sozlash", "HTTPS, backups and basic protection", "HTTPS, резервные копии и базовая защита"), None)),
    # --- Integrations ----------------------------------------------------------------
    S(("payment-integration", "api-integration", T("Click / Payme to'lovini ulash", "Click / Payme payment integration", "Подключение Click / Payme"),
       T("Sayt yoki botga onlayn to'lov tizimini ulash", "Add online payments to your site or bot", "Онлайн-оплата для сайта или бота"), None)),
    S(("api-integration-custom", "api-integration", T("Tizimlarni bir-biriga ulash", "System integrations", "Интеграция систем"),
       T("CRM, 1C, Google Sheets, Telegram va boshqa tizimlarni ulash", "Connect CRM, 1C, Google Sheets, Telegram and more", "Связка CRM, 1С, Google Sheets, Telegram и др."), "code_generation")),
    S(("sms-notifications", "api-integration", T("SMS va avtomatik xabarnomalar", "SMS & automatic notifications", "SMS и автоуведомления"),
       T("Mijozlarga SMS, Telegram yoki email xabarlarini avtomatik yuborish", "Automatic SMS, Telegram or email messages to customers", "Автоматические SMS, Telegram и email-уведомления"), None)),
    # --- AI ----------------------------------------------------------------------------
    S(("ai-chatbot", "ai-services", T("AI yordamchi (chatbot)", "AI assistant chatbot", "ИИ-ассистент (чат-бот)"),
       T("Sayt yoki Telegram uchun savollarga javob beruvchi AI yordamchi", "An AI assistant that answers questions on your site or Telegram", "ИИ-ассистент для сайта или Telegram"), None)),
    S(("ai-images", "ai-services", T("AI yordamida rasm yaratish", "AI image creation", "Создание изображений с ИИ"),
       T("Reklama, post va dizayn uchun AI rasmlar", "AI-generated images for ads, posts and design", "ИИ-изображения для рекламы и постов"), None)),
    S(("ai-text", "ai-services", T("AI yordamida matn tayyorlash", "AI-assisted writing", "Тексты с помощью ИИ"),
       T("Maqola, tavsif va xatlar — mutaxassis tekshiruvi bilan", "Articles, descriptions and letters, checked by a specialist", "Статьи, описания и письма с проверкой специалиста"), "document_writing")),
    S(("ai-training", "ai-services", T("ChatGPT va AI vositalaridan foydalanishni o'rgatish", "Learn to use ChatGPT & AI tools", "Обучение работе с ChatGPT и ИИ"),
       T("Ishingizda AI vositalaridan to'g'ri foydalanishni o'rganing", "Learn how to use AI tools well in your work", "Научим эффективно использовать ИИ в работе"), None)),
    # --- Online applications --------------------------------------------------------
    S(("gov-services", "online-services", T("my.gov.uz da ariza topshirish", "Applications on my.gov.uz", "Заявки на my.gov.uz"),
       T("Davlat xizmatlari portalida ariza va hujjat topshirishda yordam", "Help submitting applications on the public services portal", "Помощь с заявками на портале госуслуг"), None)),
    S(("e-signature", "online-services", T("ERI (elektron imzo) o'rnatish", "E-signature (ERI) setup", "Установка ЭЦП"),
       T("Elektron raqamli imzoni kompyuterga o'rnatish va sozlash", "Install and configure your digital signature", "Установка и настройка электронной подписи"), None)),
    S(("visa-forms", "online-services", T("Viza va xorij anketalarini to'ldirish", "Visa & travel form filling", "Заполнение визовых анкет"),
       T("Onlayn viza anketalari va xorijiy saytlarda ro'yxatdan o'tish", "Online visa forms and registrations on foreign websites", "Онлайн-визовые анкеты и регистрации"), None)),
    S(("green-card", "online-services", T("Green Card (DV Lottery) anketasi", "Green Card (DV Lottery) entry", "Анкета Green Card (DV Lottery)"),
       T("Rasmiy saytda anketani to'g'ri to'ldirish va rasm talablari", "Correctly fill in the official form and meet photo rules", "Правильное заполнение анкеты и требования к фото"), None)),
    S(("university-applications", "online-services", T("O'qishga onlayn hujjat topshirish", "University online applications", "Онлайн-подача документов в вуз"),
       T("OTM, xorijiy universitet va imtihonlarga ro'yxatdan o'tish", "Register for universities, foreign schools and exams", "Регистрация в вузы, зарубежные университеты и экзамены"), None)),
    S(("online-accounts", "online-services", T("Onlayn kabinet va akkauntlarni ochish", "Online account setup", "Создание онлайн-аккаунтов"),
       T("Email, bank ilovasi, marketplace va boshqa kabinetlarni ochish", "Email, banking apps, marketplaces and other accounts", "Email, банковские приложения, маркетплейсы"), None)),
    S(("marketplace-seller", "online-services", T("Uzum va marketplace'da do'kon ochish", "Open a marketplace store", "Открытие магазина на маркетплейсе"),
       T("Sotuvchi kabinetini ochish va mahsulot kartochkalarini yaratish", "Seller account setup and product listings", "Кабинет продавца и карточки товаров"), None)),
    # --- Lessons ---------------------------------------------------------------------
    S(("computer-basics", "lessons-consulting", T("Kompyuter savodxonligi darslari", "Computer basics lessons", "Уроки компьютерной грамотности"),
       T("Noldan: Windows, internet, pochta va xavfsizlik", "From zero: Windows, internet, email and safety", "С нуля: Windows, интернет, почта и безопасность"), None)),
    S(("office-lessons", "lessons-consulting", T("Word, Excel, PowerPoint darslari", "Word, Excel & PowerPoint lessons", "Уроки Word, Excel, PowerPoint"),
       T("Ishda kerakli Office ko'nikmalarini o'rganish", "Learn the Office skills you need at work", "Навыки Office для работы"), None)),
    S(("programming-lessons", "lessons-consulting", T("Dasturlashni o'rganish", "Programming lessons", "Уроки программирования"),
       T("Python, veb-dasturlash va botlar bo'yicha individual darslar", "1:1 lessons in Python, web development and bots", "Индивидуальные уроки Python, веба и ботов"), None)),
    S(("it-consulting", "lessons-consulting", T("IT maslahat", "IT consultation", "IT-консультация"),
       T("Kompyuter, dastur yoki biznes uchun texnik yechim tanlashda maslahat", "Advice on choosing computers, software or tech for your business", "Совет по выбору техники, программ и решений"), None)),
    S(("pc-buying-advice", "lessons-consulting", T("Kompyuter tanlashda yordam", "Help choosing a computer", "Помощь в выборе компьютера"),
       T("Byudjetingiz va ishingizga mos kompyuter yoki noutbuk tanlash", "Pick a computer or laptop that fits your budget and work", "Подбор компьютера или ноутбука под задачи"), None)),
    # --- Other -----------------------------------------------------------------------
    S(("custom-task", "custom-digital-tasks", T("Maxsus raqamli vazifa", "Custom digital task", "Индивидуальная задача"),
       T("Ro'yxatda yo'q bo'lsa — vazifangizni yozing, biz baholaymiz", "Not listed? Describe your task and we'll quote it", "Нет в списке? Опишите задачу — мы оценим"), None)),
]

FEATURED = {"windows-install", "typing", "cv-resume", "excel-tables", "powerpoint-presentation", "translation", "logo-design",
            "video-editing", "instagram-design", "telegram-bot-development", "landing-page", "gov-services"}


# ---------------------------------------------------------------- business model (audit 2026-11)
# ONLINE: anywhere in Uzbekistan over the internet. REMOTE: remote tech help (AnyDesk etc., customer consent).
# LOCAL: physical, Qarapchi only. FUTURE: hidden until partners/equipment exist. DISABLED: archived duplicate.
REMOTE_SLUGS = {
    "windows-install", "drivers-install", "virus-removal", "pc-speedup", "software-install", "data-recovery", "printer-setup",
    "wifi-network-setup", "backup-setup", "remote-help", "gov-services", "e-signature", "online-accounts",
}
LOCAL_SLUGS = {"document-printing", "photocopy", "scanning", "book-printing"}
FUTURE_SLUGS = {"phone-setup"}  # needs the physical phone; may become LOCAL later
DISABLED_SLUGS = {"ai-text"}  # duplicates "copywriting" / "summary-report"
LOCAL_AREA = "qarapchi"


def mode_for(slug: str) -> str:
    if slug in LOCAL_SLUGS:
        return "LOCAL"
    if slug in REMOTE_SLUGS:
        return "REMOTE"
    if slug in FUTURE_SLUGS:
        return "FUTURE"
    if slug in DISABLED_SLUGS:
        return "DISABLED"
    return "ONLINE"


# Honest wording for services whose scope changed in the audit. Applied only while a service still has
# the original seed wording (admin edits are never overwritten).
MODIFIED_TEXT: dict[str, tuple[dict, dict]] = {
    "windows-install": (T("Windows sozlash va xatolarni tuzatish (masofadan)", "Windows setup & fixes (remote)", "Настройка и исправление Windows (удалённо)"),
                        T("Sozlamalar, yangilanishlar va xatolarni AnyDesk orqali, roziligingiz bilan tuzatamiz. Noldan qayta o'rnatish masofadan bajarilmaydi",
                          "Settings, updates and errors fixed over AnyDesk with your consent. A clean reinstall cannot be done remotely",
                          "Настройки, обновления и ошибки через AnyDesk с вашего согласия. Переустановка с нуля удалённо невозможна")),
    "wifi-network-setup": (T("Wi-Fi va internet muammolarini tekshirish", "Wi-Fi & internet troubleshooting", "Проверка Wi-Fi и интернета"),
                           T("Kompyuterdagi Wi-Fi, internet va router sozlamalarini masofadan tekshirish", "Check Wi-Fi, internet and router settings on your computer remotely",
                             "Удалённая проверка Wi-Fi, интернета и настроек роутера")),
    "data-recovery": (T("O'chirilgan fayllarni tiklash (masofadan)", "Deleted file recovery (remote)", "Восстановление удалённых файлов (удалённо)"),
                      T("Dastur yordamida fleshka, disk yoki xotira kartadan tiklashga urinish. Shikastlangan diskni ta'mirlash emas",
                        "Software recovery from USB drives, disks or memory cards. Not physical repair of damaged drives",
                        "Программное восстановление с флешек, дисков и карт памяти. Не ремонт повреждённых дисков")),
    "contracts-templates": (T("Shartnoma va blanka shablonlari", "Contract & form templates", "Шаблоны договоров и бланков"),
                            T("Hujjat, blanka, dalolatnoma va hisob-faktura shablonlari. Yuridik maslahat emas", "Templates for documents, forms, acts and invoices. Not legal advice",
                              "Шаблоны документов, бланков, актов и счетов. Не юридическая консультация")),
    "student-projects": (T("Talabalarga dasturlashni tushuntirish", "Programming help for students", "Помощь студентам в программировании"),
                         T("Laboratoriya ishlari va loyihalarni tushuntirib o'rgatamiz (imtihon o'rniga topshirib berish emas)",
                           "We explain labs and projects so you learn them (not doing exams for you)", "Объясняем лабораторные и проекты (не сдаём экзамены за вас)")),
    "green-card": (T("Green Card (DV Lottery) anketasi", "Green Card (DV Lottery) entry", "Анкета Green Card (DV Lottery)"),
                   T("Rasmiy va bepul saytda anketani to'g'ri to'ldirishga yordam. G'olib bo'lish kafolatlanmaydi",
                     "Help filling in the official, free form correctly. Winning is not guaranteed", "Помощь с заполнением официальной бесплатной анкеты. Выигрыш не гарантируется")),
    "gov-services": (T("my.gov.uz da ariza topshirish", "Applications on my.gov.uz", "Заявки на my.gov.uz"),
                     T("Ariza topshirishga masofadan yordam: tizimga o'zingiz kirasiz, parollaringizni so'ramaymiz",
                       "Remote help with applications: you sign in yourself, we never ask for passwords", "Удалённая помощь: вы входите сами, пароли мы не спрашиваем")),
    "e-signature": (T("ERI (elektron imzo) o'rnatish", "E-signature (ERI) setup", "Установка ЭЦП"),
                    T("Elektron imzo kalitini kompyuteringizga masofadan o'rnatish va sozlash", "Install and configure your e-signature key remotely",
                      "Удалённая установка и настройка ключа ЭЦП")),
    "online-accounts": (T("Onlayn kabinet va akkauntlarni ochish", "Online account setup", "Создание онлайн-аккаунтов"),
                        T("Email, bank ilovasi, marketplace kabinetlarini ochish. SMS kod va parollarni o'zingiz kiritasiz",
                          "Email, banking apps and marketplace accounts. You enter SMS codes and passwords yourself",
                          "Email, банковские приложения, маркетплейсы. SMS-коды и пароли вводите вы сами")),
}

_COPIES = {"key": "copies", "label": T("Nusxalar soni", "Number of copies", "Количество копий"), "type": "number", "required": True, "options": []}
_COLOR = {"key": "color", "label": T("Rang", "Colour", "Цвет"), "type": "select", "required": True, "options": ["bw", "color"]}
_PAGES = {"key": "pages", "label": T("Taxminiy sahifalar soni", "Approximate number of pages", "Примерное количество страниц"), "type": "number", "required": False, "options": []}
LOCAL_FIELDS: dict[str, list[dict]] = {
    "document-printing": [_COPIES, _COLOR, _PAGES],
    "book-printing": [_COPIES, _COLOR, {**_PAGES, "required": True}],
    "photocopy": [_COPIES, _COLOR, {"key": "originals", "label": T("Qanday hujjat (masalan, pasport)", "What document (e.g. passport)", "Какой документ (например, паспорт)"),
                                    "type": "text", "required": True, "options": []}],
    "scanning": [{"key": "pages", "label": T("Sahifalar soni", "Number of pages", "Количество страниц"), "type": "number", "required": True, "options": []},
                 {"key": "output", "label": T("Natija formati", "Output format", "Формат результата"), "type": "select", "required": True, "options": ["pdf", "jpg"]}],
}
REQUIRES_FILE = {"document-printing", "book-printing"}

# Customer-selectable areas (no GPS). Only Qarapchi has LOCAL services today. Admins manage areas later.
DEFAULT_AREAS: list[tuple] = [
    # slug, kind, name, region, district, locality, local_services_enabled, sort
    ("qarapchi", "LOCALITY", T("Qarapchi qishlog'i", "Qarapchi village", "Кишлак Карапчи"), "Jizzax viloyati", "Zomin tumani", "Qarapchi", True, 10),
    ("zomin-city", "LOCALITY", T("Zomin shahri", "Zomin town", "Город Зомин"), "Jizzax viloyati", "Zomin tumani", "Zomin", False, 20),
    ("zomin-district", "DISTRICT", T("Zomin tumani (boshqa joy)", "Zomin district (elsewhere)", "Зоминский район (другое место)"), "Jizzax viloyati", "Zomin tumani", "", False, 30),
    ("jizzakh-region", "REGION", T("Jizzax viloyati (boshqa joy)", "Jizzakh region (elsewhere)", "Джизакская область (другое место)"), "Jizzax viloyati", "", "", False, 40),
    ("other", "OTHER", T("Boshqa hudud (O'zbekiston)", "Other region (Uzbekistan)", "Другой регион (Узбекистан)"), "", "", "", False, 90),
]
