"""Backend message catalog for notifications and emails (uz default, en, ru)."""

from __future__ import annotations

SUPPORTED = ("uz", "en", "ru")

MESSAGES: dict[str, dict[str, str]] = {
    # ---- email subjects / bodies ----
    "email.verify.subject": {"uz": "VIMORA: elektron pochtangizni tasdiqlang", "en": "VIMORA: verify your email", "ru": "VIMORA: подтвердите email"},
    "email.verify.body": {
        "uz": "Assalomu alaykum!\n\nVIMORA hisobingizni faollashtirish uchun quyidagi havolani oching:\n{link}\n\nHavola {hours} soat davomida amal qiladi. Agar siz ro'yxatdan o'tmagan bo'lsangiz, bu xatni e'tiborsiz qoldiring.",
        "en": "Hello!\n\nOpen the link below to verify your VIMORA account:\n{link}\n\nThe link is valid for {hours} hours. If you did not register, ignore this email.",
        "ru": "Здравствуйте!\n\nОткройте ссылку ниже, чтобы подтвердить аккаунт VIMORA:\n{link}\n\nСсылка действительна {hours} ч. Если вы не регистрировались, проигнорируйте это письмо.",
    },
    "email.reset.subject": {"uz": "VIMORA: parolni tiklash", "en": "VIMORA: password reset", "ru": "VIMORA: сброс пароля"},
    "email.reset.body": {
        "uz": "Parolni tiklash uchun so'rov qabul qilindi. Yangi parol o'rnatish uchun havola:\n{link}\n\nHavola {minutes} daqiqa amal qiladi va faqat bir marta ishlatiladi. Agar so'rovni siz yubormagan bo'lsangiz, bu xatni e'tiborsiz qoldiring.",
        "en": "We received a password reset request. Set a new password here:\n{link}\n\nThe link is valid for {minutes} minutes and can be used once. If you did not request this, ignore this email.",
        "ru": "Получен запрос на сброс пароля. Установите новый пароль по ссылке:\n{link}\n\nСсылка действительна {minutes} минут и одноразовая. Если вы не запрашивали сброс, проигнорируйте письмо.",
    },
    # ---- customer notifications (title / body) ----
    "n.order.created.title": {"uz": "Buyurtma qabul qilindi: {order}", "en": "Order received: {order}", "ru": "Заказ получен: {order}"},
    "n.order.created.body": {"uz": "Buyurtmangiz ko'rib chiqish uchun qabul qilindi.", "en": "Your order has been received and will be reviewed.", "ru": "Ваш заказ получен и будет рассмотрен."},
    "n.quotation.available.title": {"uz": "Narx taklifi tayyor: {order}", "en": "Quotation available: {order}", "ru": "Готово коммерческое предложение: {order}"},
    "n.quotation.available.body": {"uz": "Jami: {total}. Oldindan to'lov: {deposit}. Taklifni kabinetingizda ko'rib chiqing.", "en": "Total: {total}. Deposit: {deposit}. Review it in your dashboard.", "ru": "Итого: {total}. Предоплата: {deposit}. Посмотрите предложение в личном кабинете."},
    "n.payment.confirmed.title": {"uz": "To'lov tasdiqlandi: {order}", "en": "Payment confirmed: {order}", "ru": "Оплата подтверждена: {order}"},
    "n.payment.confirmed.body": {"uz": "{amount} miqdoridagi to'lov qabul qilindi.", "en": "We received your payment of {amount}.", "ru": "Мы получили оплату на сумму {amount}."},
    "n.order.status.title": {"uz": "Buyurtma holati yangilandi: {order}", "en": "Order status updated: {order}", "ru": "Статус заказа обновлён: {order}"},
    "n.order.status.body": {"uz": "Yangi holat: {status}", "en": "New status: {status}", "ru": "Новый статус: {status}"},
    "n.work.completed.title": {"uz": "Ish yakunlandi: {order}", "en": "Work completed: {order}", "ru": "Работа выполнена: {order}"},
    "n.work.completed.body": {"uz": "Natijani olish uchun qolgan {amount} miqdorini to'lang.", "en": "Pay the remaining {amount} to receive the result.", "ru": "Оплатите оставшиеся {amount}, чтобы получить результат."},
    "n.final_payment.reminder.title": {"uz": "Yakuniy to'lov eslatmasi: {order}", "en": "Final payment reminder: {order}", "ru": "Напоминание об оплате: {order}"},
    "n.final_payment.reminder.body": {"uz": "Qolgan summa: {amount}.", "en": "Remaining balance: {amount}.", "ru": "Остаток к оплате: {amount}."},
    "n.local.ready.title": {"uz": "Buyurtma tayyor: {order}", "en": "Your order is ready: {order}", "ru": "Заказ готов: {order}"},
    "n.local.ready.pickup": {"uz": "Olib ketishingiz mumkin. Manzil buyurtma sahifasida.", "en": "You can pick it up. The address is on the order page.", "ru": "Можно забрать. Адрес на странице заказа."},
    "n.local.ready.meetup": {"uz": "Kelishilgan joy va vaqtda topshiramiz.", "en": "We will hand it over at the agreed place and time.", "ru": "Передадим в согласованном месте и время."},
    "n.local.handed.title": {"uz": "Buyurtma topshirildi: {order}", "en": "Order handed over: {order}", "ru": "Заказ передан: {order}"},
    "n.local.handed.body": {"uz": "Xizmatimizdan foydalanganingiz uchun rahmat.", "en": "Thank you for using VIMORA.", "ru": "Спасибо, что пользуетесь VIMORA."},
    "n.handover.proposed.title": {"uz": "Uchrashuv uchun yangi taklif: {order}", "en": "New meeting proposal: {order}", "ru": "Новое предложение встречи: {order}"},
    "n.handover.proposed.body": {"uz": "Taklif qilingan joy: {place}. Buyurtma sahifasida tasdiqlang.", "en": "Proposed place: {place}. Please confirm on the order page.", "ru": "Предложенное место: {place}. Подтвердите на странице заказа."},
    "n.handover.confirmed.title": {"uz": "Uchrashuv tasdiqlandi: {order}", "en": "Meeting confirmed: {order}", "ru": "Встреча подтверждена: {order}"},
    "n.handover.confirmed.body": {"uz": "Joy: {place}. Vaqti buyurtma sahifasida.", "en": "Place: {place}. The time is on the order page.", "ru": "Место: {place}. Время на странице заказа."},
    "n.payment.due.title": {"uz": "To'lov kutilmoqda: {order}", "en": "Payment due: {order}", "ru": "Ожидается оплата: {order}"},
    "n.payment.due.body": {"uz": "Ishni boshlash uchun {amount} oldindan to'lang.", "en": "Pay the {amount} deposit to start the work.", "ru": "Внесите предоплату {amount}, чтобы начать работу."},
    "n.work.started.title": {"uz": "Ish boshlandi: {order}", "en": "Work has started: {order}", "ru": "Работа начата: {order}"},
    "n.work.started.body": {"uz": "Buyurtmangiz ustida ishlayapmiz.", "en": "We are working on your order.", "ru": "Мы работаем над вашим заказом."},
    "n.delivered.title": {"uz": "Natija tayyor: {order}", "en": "Your delivery is ready: {order}", "ru": "Результат готов: {order}"},
    "n.delivered.body": {"uz": "Fayllarni kabinetingizdan yuklab oling.", "en": "Download your files from the dashboard.", "ru": "Скачайте файлы в личном кабинете."},
    "n.message.title": {"uz": "Yangi xabar: {order}", "en": "New message: {order}", "ru": "Новое сообщение: {order}"},
    "n.message.body": {"uz": "Buyurtma bo'yicha yangi xabar bor.", "en": "You have a new message about your order.", "ru": "У вас новое сообщение по заказу."},
    # ---- status labels ----
    **{
        f"status.{k}": v
        for k, v in {
            "SUBMITTED": {"uz": "Yuborildi", "en": "Submitted", "ru": "Отправлен"},
            "UNDER_REVIEW": {"uz": "Ko'rib chiqilmoqda", "en": "Under review", "ru": "На рассмотрении"},
            "QUOTATION_PENDING": {"uz": "Narx taklifi kutilmoqda", "en": "Quotation pending", "ru": "Ожидает решения по предложению"},
            "QUOTATION_ACCEPTED": {"uz": "Taklif qabul qilindi", "en": "Quotation accepted", "ru": "Предложение принято"},
            "DEPOSIT_PENDING": {"uz": "Oldindan to'lov kutilmoqda", "en": "Deposit pending", "ru": "Ожидается предоплата"},
            "PARTIALLY_PAID": {"uz": "Qisman to'langan", "en": "Partially paid", "ru": "Частично оплачен"},
            "PAID": {"uz": "To'langan", "en": "Paid", "ru": "Оплачен"},
            "QUEUED": {"uz": "Navbatda", "en": "Queued", "ru": "В очереди"},
            "AI_PROCESSING": {"uz": "Bajarilmoqda", "en": "In progress", "ru": "В работе"},
            "AI_REVIEW_REQUIRED": {"uz": "Sifat nazoratida", "en": "Quality review", "ru": "Проверка качества"},
            "MANUAL_PROCESSING": {"uz": "Bajarilmoqda", "en": "In progress", "ru": "В работе"},
            "REVISION_REQUESTED": {"uz": "Tuzatish so'raldi", "en": "Revision requested", "ru": "Запрошена доработка"},
            "COMPLETED_PENDING_FINAL_PAYMENT": {"uz": "Yakunlandi, to'lov kutilmoqda", "en": "Completed, awaiting payment", "ru": "Готово, ожидает оплаты"},
            "FINAL_PAYMENT_PENDING": {"uz": "Yakuniy to'lov kutilmoqda", "en": "Final payment pending", "ru": "Ожидается окончательная оплата"},
            "READY_FOR_DELIVERY": {"uz": "Topshirishga tayyor", "en": "Ready for delivery", "ru": "Готов к передаче"},
            "DELIVERED": {"uz": "Topshirildi", "en": "Delivered", "ru": "Передан"},
            "CLOSED": {"uz": "Yopildi", "en": "Closed", "ru": "Закрыт"},
            "CANCELLED": {"uz": "Bekor qilindi", "en": "Cancelled", "ru": "Отменён"},
            "REFUND_PENDING": {"uz": "Qaytarish kutilmoqda", "en": "Refund pending", "ru": "Ожидает возврата"},
            "REFUNDED": {"uz": "Qaytarildi", "en": "Refunded", "ru": "Возвращён"},
            "FAILED": {"uz": "Muvaffaqiyatsiz", "en": "Failed", "ru": "Не выполнен"},
        }.items()
    },
}


def t(key: str, lang: str = "uz", **kwargs) -> str:
    entry = MESSAGES.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry.get("en") or next(iter(entry.values()))
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text


def pick(translatable: dict | None, lang: str) -> str:
    if not translatable:
        return ""
    return translatable.get(lang) or translatable.get("en") or translatable.get("uz") or next(iter(translatable.values()), "")
