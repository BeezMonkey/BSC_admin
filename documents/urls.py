from django.urls import path

from .views import (
    document_create,
    document_detail,
    document_download,
    document_list,
    worker_document_detail,
    worker_document_download,
    worker_document_list,
)

urlpatterns = [
    path("documents/", document_list, name="document_list"),
    path("documents/new/", document_create, name="document_create"),
    path("documents/<int:document_id>/", document_detail, name="document_detail"),
    path(
        "documents/<int:document_id>/download/",
        document_download,
        name="document_download",
    ),
    path("sw/documents/", worker_document_list, name="worker_document_list"),
    path(
        "sw/documents/<int:document_id>/",
        worker_document_detail,
        name="worker_document_detail",
    ),
    path(
        "sw/documents/<int:document_id>/download/",
        worker_document_download,
        name="worker_document_download",
    ),
]
