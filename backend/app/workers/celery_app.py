from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "clarifi",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=10,
    task_routes={
        "app.workers.tasks.run_financial_analysis": {"queue": "workflows"},
        "app.workers.tasks.sync_connector": {"queue": "connectors"},
    },
)

