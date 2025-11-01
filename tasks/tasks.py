import os
from PIL import Image

from django_task_queue.celery import app
from tasks.models import Job


@app.task(bind=True, max_retries=3)
def resize_image(self, job_id, img_path):
    """Resize image to thumbnail. Updates Job status throughout process."""

    new_size = (128, 128)
    outfile = os.path.splitext(img_path)[0] + "_thumbnail.jpg"
    job = None

    try:
        job = Job.objects.get(id=job_id)
        job.status = job.STATUS_PROCESSING
        job.save()

        im = Image.open(img_path)
        im.thumbnail(new_size)
        im.save(outfile, "JPEG")

        job.resized_image = outfile
        job.status = job.STATUS_COMPLETED
        job.save()

        return outfile

    except Exception as e:
        if job:
            if self.request.retries >= self.max_retries:
                job.status = job.STATUS_FAILED
                job.error_message = str(e)
                job.save()

        raise self.retry(exc=e, countdown=2**self.request.retries)
