from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "farmconnect",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.task_routes = {"app.tasks.message_tasks.*": {"queue": "messages"}}
