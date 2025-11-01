from rest_framework import serializers

from tasks.models import Job


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id",
            "status",
            "original_image",
            "resized_image",
            "error_message",
            "created_at",
        ]
