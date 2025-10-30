from django.urls import path

from tasks.views import JobView

urlpatterns = [
    path("", JobView.as_view(), name="create-job"),
    path("<uuid:job_id>/", JobView.as_view(), name="get-job"),
]
