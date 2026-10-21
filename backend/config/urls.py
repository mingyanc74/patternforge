from core import views
from django.urls import path

urlpatterns = [
    path("api/bootstrap", views.Bootstrap.as_view()),
    path("api/health", views.Health.as_view()),
    path("api/s3/connections", views.Connections.as_view()),
    path("api/s3/sample-connection", views.SampleConnection.as_view()),
    path("api/s3/connections/<uuid:connection_id>", views.Disconnect.as_view()),
    path("api/s3/connections/<uuid:connection_id>/files", views.Files.as_view()),
    path("api/files/inspect", views.Inspect.as_view()),
    path("api/jobs", views.Jobs.as_view()),
    path("api/jobs/<uuid:job_id>", views.JobDetail.as_view()),
    path("api/jobs/<uuid:job_id>/cancel", views.Cancel.as_view()),
    path("api/jobs/<uuid:job_id>/results", views.Results.as_view()),
    path("internal/metrics", views.Metrics.as_view()),
]
