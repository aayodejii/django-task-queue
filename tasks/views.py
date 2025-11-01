from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, status
from rest_framework.response import Response

from tasks.models import Job
from tasks.serializers import JobSerializer
from tasks.tasks import resize_image


class JobView(APIView):
    serializer_class = JobSerializer

    def get(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)
        serializer = self.serializer_class(job)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    def post(self, request):
        # API endpoint receives image upload
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            # Creates a Job record in database (status: PENDING)
            instance = serializer.save()
            print("orginal", instance.original_image.path)

            # Triggers Celery task with job ID
            resize_image.delay(instance.id, instance.original_image.path)

            return Response(status=status.HTTP_201_CREATED, data=serializer.data)
        return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors)

        # API endpoint to check job status returns the result
