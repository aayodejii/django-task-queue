from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response


class JobView(APIView):

    def get(self, request, job_id):

        return Response({"message": "Job View"})

    def post(self, request):
        # API endpoint receives image upload
        # Creates a Job record in database (status: PENDING)
        # Triggers Celery task with job ID
        # Task resizes image, updates Job status to COMPLETED
        # API endpoint to check job status returns the result

        return Response({"message": "Job Created"})
