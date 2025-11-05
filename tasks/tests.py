import io
import os
from unittest.mock import patch
from datetime import timedelta

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from PIL import Image

from tasks.models import Job
from tasks.tasks import resize_image, cleanup_old_jobs


class ResizeImageTaskTest(TestCase):
    def setUp(self):
        image = Image.new("RGB", (700, 700), color="red")
        image_file = io.BytesIO()
        image.save(image_file, "JPEG")
        image_file.seek(0)

        self.uploaded_image = SimpleUploadedFile(
            name="test_image.jpg", content=image_file.read(), content_type="image/jpeg"
        )

    def tearDown(self):
        for job in Job.objects.all():
            if job.original_image and os.path.exists(job.original_image.path):
                os.remove(job.original_image.path)
            if job.resized_image and os.path.exists(job.resized_image.path):
                os.remove(job.resized_image.path)
        super().tearDown()

    def test_resize_creates_thumbnail(self):
        job = Job.objects.create(original_image=self.uploaded_image)

        resize_image(job.id, job.original_image.path)

        job.refresh_from_db()

        self.assertEqual(job.status, Job.STATUS_COMPLETED)
        self.assertIsNotNone(job.resized_image)
        self.assertTrue(os.path.exists(job.resized_image.path))

    @patch("tasks.tasks.Image.open")
    def test_task_handles_failure(self, mock_open):
        mock_open.side_effect = Exception("Corrupted image")

        job = Job.objects.create(original_image=self.uploaded_image)

        task = resize_image
        task.request.retries = 3
        task.max_retries = 3

        with self.assertRaises(Exception):
            task(job.id, job.original_image.path)

        job.refresh_from_db()

        self.assertEqual(job.status, Job.STATUS_FAILED)
        self.assertIsNotNone(job.error_message)

    def test_cleanup_old_jobs(self):
        old_job = Job.objects.create(original_image=self.uploaded_image)
        Job.objects.filter(id=old_job.id).update(
            created_at=timezone.now() - timezone.timedelta(hours=25)
        )
        old_job.refresh_from_db()

        recent_job = Job.objects.create(original_image=self.uploaded_image)

        summary = cleanup_old_jobs()

        self.assertIn("Deleted 1 jobs", summary)
        self.assertFalse(Job.objects.filter(id=old_job.id).exists())
        self.assertTrue(Job.objects.filter(id=recent_job.id).exists())
        self.assertFalse(os.path.exists(old_job.original_image.path))
        self.assertTrue(os.path.exists(recent_job.original_image.path))
