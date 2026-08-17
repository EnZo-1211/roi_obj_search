from celery import Celery
import os

# Configure Celery
celery_app = Celery(
    "roi_object_search",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    include=["src.celery_tasks"]
)

# Configure Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour timeout
    task_soft_time_limit=3300,  # 55 minutes soft timeout
    worker_prefetch_multiplier=1,  # Process tasks one by one
)

# Configure task routes and queues
celery_app.conf.task_routes = {
    "src.celery_tasks.process_object_matching": {"queue": "roi_processing"},
}

celery_app.conf.task_default_queue = "roi_processing"
celery_app.conf.task_create_missing_queues = True