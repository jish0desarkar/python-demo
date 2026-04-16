from celery import Celery

from app.config import settings
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


celery_app = Celery(
    "python-demo",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    task_ignore_result=False,
    beat_schedule={
        "generate-random-event-every-20s": {
            "task": "tasks.generate_event.generate_random_event",
            "schedule": 30.0,
        },
    },
)

celery_app.autodiscover_tasks(["tasks.events", "tasks.embeddings", "tasks.generate_event"])
