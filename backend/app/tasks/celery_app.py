from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
from app.core.logging import configure_logging

configure_logging(settings.LOG_LEVEL)

celery = Celery("vimora", broker=settings.broker_url, backend=None, include=["app.tasks.jobs"])
celery.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=900,
    task_soft_time_limit=840,
    task_default_queue="default",
    task_routes={"app.tasks.jobs.run_ai_execution": {"queue": "ai"}},
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    broker_connection_retry_on_startup=True,
    timezone="UTC",
    beat_schedule={
        "retry-notifications": {"task": "app.tasks.jobs.sweep_notifications", "schedule": 60.0},
        "expire-stale-payments": {"task": "app.tasks.jobs.expire_stale_payments", "schedule": 600.0},
        "recover-stuck-ai": {"task": "app.tasks.jobs.recover_stuck_ai", "schedule": 300.0},
        "cleanup-auth-tokens": {"task": "app.tasks.jobs.cleanup_auth", "schedule": crontab(minute=17, hour="*/6")},
        "auto-close-delivered": {"task": "app.tasks.jobs.auto_close_delivered", "schedule": crontab(minute=5, hour=3)},
        "final-payment-reminders": {"task": "app.tasks.jobs.final_payment_reminders", "schedule": crontab(minute=0, hour=6)},
        "deadline-reminders": {"task": "app.tasks.jobs.deadline_reminders", "schedule": 1800.0},
        "worker-heartbeat": {"task": "app.tasks.jobs.heartbeat", "schedule": 60.0},
    },
)
