from __future__ import annotations

import time
from datetime import timedelta

from sqlalchemy import delete, select

from app.core.db import SessionLocal, utcnow
from app.core.logging import get_logger
from app.models import AIExecution, EmailVerification, Notification, Order, PasswordReset, Payment, Session, TelegramLinkCode, User
from app.models.enums import ActorType as A
from app.models.enums import AIExecutionStatus as X
from app.models.enums import NotificationStatus as NS
from app.models.enums import OrderStatus as S
from app.models.enums import PaymentProvider, PaymentStatus
from app.tasks.celery_app import celery

log = get_logger("jobs")


@celery.task(name="app.tasks.jobs.deliver_notification", bind=True, max_retries=5, default_retry_delay=30)
def deliver_notification(self, notification_id: int) -> str:
    from app.services.notifications import MAX_ATTEMPTS, deliver

    with SessionLocal() as db:
        status = deliver(db, notification_id)
        if status == NS.FAILED:
            n = db.get(Notification, notification_id)
            if n and n.attempts < MAX_ATTEMPTS:
                raise self.retry(countdown=min(30 * 2 ** n.attempts, 1800))
        return status


@celery.task(name="app.tasks.jobs.sweep_notifications")
def sweep_notifications() -> int:
    from app.services.notifications import MAX_ATTEMPTS

    with SessionLocal() as db:
        ids = db.scalars(
            select(Notification.id).where(Notification.status.in_([NS.PENDING, NS.FAILED]), Notification.attempts < MAX_ATTEMPTS,
                                          Notification.created_at < utcnow() - timedelta(minutes=1)).limit(200)
        ).all()
    for nid in ids:
        deliver_notification.delay(nid)
    return len(ids)


@celery.task(name="app.tasks.jobs.run_ai_execution", acks_late=True)
def run_ai_execution(execution_id: int) -> str:
    from app.ai.pipeline import run

    with SessionLocal() as db:
        return run(db, execution_id)


@celery.task(name="app.tasks.jobs.recover_stuck_ai")
def recover_stuck_ai() -> int:
    """Executions stuck in a running state (worker crash) are transferred to manual handling."""
    from app.ai.pipeline import _fallback

    n = 0
    with SessionLocal() as db:
        stuck = db.scalars(select(AIExecution).where(AIExecution.status.in_([X.PLANNING, X.RUNNING, X.VALIDATING]), AIExecution.updated_at < utcnow() - timedelta(minutes=30))).all()
        for ex in stuck:
            _fallback(db, ex, db.get(Order, ex.order_id), "WORKER", "Execution did not finish within 30 minutes")
            n += 1
        pending = db.scalars(select(AIExecution.id).where(AIExecution.status == X.PENDING, AIExecution.created_at < utcnow() - timedelta(minutes=5))).all()
    for eid in pending:
        run_ai_execution.delay(eid)  # re-enqueue if the original enqueue was lost
    return n


@celery.task(name="app.tasks.jobs.expire_stale_payments")
def expire_stale_payments() -> int:
    from app.payments.service import cancel_payment

    n = 0
    with SessionLocal() as db:
        # Payme manages its own 12h timeout; Click/Stripe/manual pending attempts expire after 24h.
        rows = db.scalars(select(Payment).where(Payment.status == PaymentStatus.PENDING, Payment.provider != PaymentProvider.PAYME, Payment.created_at < utcnow() - timedelta(hours=24))).all()
        for p in rows:
            cancel_payment(db, p, "Expired without confirmation")
            n += 1
        db.commit()
    return n


@celery.task(name="app.tasks.jobs.cleanup_auth")
def cleanup_auth() -> None:
    with SessionLocal() as db:
        now = utcnow()
        db.execute(delete(Session).where(Session.expires_at < now - timedelta(days=7)))
        db.execute(delete(EmailVerification).where(EmailVerification.expires_at < now - timedelta(days=7)))
        db.execute(delete(PasswordReset).where(PasswordReset.expires_at < now - timedelta(days=7)))
        db.execute(delete(TelegramLinkCode).where(TelegramLinkCode.expires_at < now - timedelta(days=1)))
        db.commit()


@celery.task(name="app.tasks.jobs.auto_close_delivered")
def auto_close_delivered() -> int:
    from app.services import order_state
    from app.services.settings_service import get_setting

    n = 0
    with SessionLocal() as db:
        days = int(get_setting(db, "orders.auto_close_days"))
        rows = db.scalars(select(Order).where(Order.status == S.DELIVERED, Order.delivered_at < utcnow() - timedelta(days=days)).with_for_update(skip_locked=True)).all()
        for o in rows:
            order_state.transition(db, o, S.CLOSED, actor_type=A.SYSTEM, message=f"Closed automatically {days} days after delivery")
            n += 1
        db.commit()
    return n


@celery.task(name="app.tasks.jobs.final_payment_reminders")
def final_payment_reminders() -> int:
    from app.services.notifications import notify_customer
    from app.services.pricing import format_money

    n = 0
    with SessionLocal() as db:
        rows = db.scalars(select(Order).where(Order.status == S.FINAL_PAYMENT_PENDING, Order.completed_at < utcnow() - timedelta(days=2))).all()
        for o in rows:
            user = db.get(User, o.customer_id)
            notify_customer(db, user, "final_payment.reminder", key_suffix=f"{o.id}:{utcnow():%Y%m%d}", title_key="n.final_payment.reminder.title",
                            body_key="n.final_payment.reminder.body", params={"order": o.order_number, "amount": format_money(o.remaining_minor, o.currency)},
                            order=o, link=f"/dashboard/orders/{o.id}")
            n += 1
        db.commit()
    return n


OPEN_WORK = [S.SUBMITTED, S.UNDER_REVIEW, S.QUOTATION_PENDING, S.QUOTATION_ACCEPTED, S.DEPOSIT_PENDING, S.PARTIALLY_PAID, S.PAID, S.QUEUED,
             S.AI_PROCESSING, S.AI_REVIEW_REQUIRED, S.MANUAL_PROCESSING, S.REVISION_REQUESTED]


@celery.task(name="app.tasks.jobs.deadline_reminders")
def deadline_reminders() -> int:
    """Tell the owner (admin bell, Telegram) about orders whose deadline is within 24 hours. Once per order."""
    from app.services.notifications import notify_admins

    n = 0
    with SessionLocal() as db:
        now = utcnow()
        rows = db.scalars(select(Order).where(Order.deadline.is_not(None), Order.deadline > now, Order.deadline <= now + timedelta(hours=24),
                                              Order.status.in_(OPEN_WORK))).all()
        for o in rows:
            notify_admins(db, "order.deadline_soon", key_suffix=f"{o.id}:{o.deadline:%Y%m%d%H}", title="DEADLINE WITHIN 24 HOURS",
                          lines=[("Order", f"#{o.order_number}"), ("Deadline", o.deadline.isoformat(timespec="minutes"))], order=o)
            n += 1
        db.commit()
    return n


@celery.task(name="app.tasks.jobs.heartbeat")
def heartbeat() -> None:
    from app.core.redis import get_redis

    get_redis().set("worker:heartbeat", str(int(time.time())), ex=300)
