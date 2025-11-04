import os
import logging
from datetime import timedelta
import uuid
from PIL import Image

from celery.schedules import crontab
from django.conf import settings
from django.utils import timezone

from django_task_queue.celery import app
from tasks.models import Job

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3)
def resize_image(self, job_id, img_path):
    """Resize image to thumbnail. Updates Job status throughout process."""

    new_size = (128, 128)
    thumbnail_dir = os.path.join(settings.MEDIA_ROOT, "thumbnails")
    os.makedirs(thumbnail_dir, exist_ok=True)
    unique_id = uuid.uuid4().hex[:8]
    outfile = os.path.join(thumbnail_dir, f"thumbnail-{unique_id}.jpg")
    outfile_relative = os.path.join("thumbnails", f"thumbnail-{unique_id}.jpg")

    job = None

    try:
        job = Job.objects.get(id=job_id)

        if job.status == job.STATUS_COMPLETED:
            return f"Already completed: {job.resized_image}"

        if job.status == job.STATUS_PROCESSING:
            raise Exception("Job is already being processed.")

        job.status = job.STATUS_PROCESSING
        job.save()

        im = Image.open(img_path)
        im.thumbnail(new_size)
        im.save(outfile, "JPEG")

        job.resized_image = outfile_relative
        job.status = job.STATUS_COMPLETED
        job.save()

        return outfile_relative

    except Exception as e:
        if job:
            if self.request.retries >= self.max_retries:
                job.status = job.STATUS_FAILED
                job.error_message = str(e)
                job.save()

        raise self.retry(exc=e, countdown=2**self.request.retries)


@app.task
def cleanup_old_jobs():
    """Delete jobs older than 24 hours along with their thumbnaial files. Return summary of deletions."""
    jobs = Job.objects.filter(created_at__lt=timezone.now() - timedelta(hours=24))
    files_deleted = 0

    job_count = jobs.count()

    for job in jobs:
        if job.resized_image and os.path.exists(job.resized_image.path):
            path = job.resized_image.path
            try:
                os.remove(path)
                files_deleted += 1

            except Exception as e:
                logger.warning(f"Could not delete thumbnail {path}: {e}")

        if job.original_image and os.path.exists(job.original_image.path):
            path = job.original_image.path
            try:
                os.remove(path)
                files_deleted += 1

            except Exception as e:
                logger.warning(f"Could not delete original {path}: {e}")

        job.delete()

    return f"Deleted {job_count} jobs and {files_deleted} files older than 24 hours."


# Things to consider:

# What if the thumbnail file doesn't exist? (job failed, or file manually deleted)
# What if you can't delete the file? (permissions issue)
# Should you delete the original image too, or just the thumbnail?


# Query old jobs
# Delete files
# Delete records
# Return count
