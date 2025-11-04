import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_task_queue.settings")

app = Celery("django_task_queue")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


app.conf.beat_schedule = {
    "cleanup_old_jobs": {
        "task": "tasks.tasks.cleanup_old_jobs",
        "schedule": 10.0,
        "args": (),
    },
}
