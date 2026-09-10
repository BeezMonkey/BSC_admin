from django.urls import path

from .views import (
    document_create,
    document_delete,
    document_detail,
    document_edit,
    document_download,
    document_list,
    participant_document_files,
    document_preview,
    document_review,
    worker_document_files,
    worker_document_detail,
    worker_document_download,
    worker_document_list,
    worker_document_upload,
)

urlpatterns = [
    path("documents/", document_list, name="document_list"),
    path("documents/new/", document_create, name="document_create"),
    path(
        "documents/participants/<int:participant_id>/",
        participant_document_files,
        name="participant_document_files",
    ),
    path(
        "documents/workers/<int:worker_id>/",
        worker_document_files,
        name="worker_document_files",
    ),
    path("documents/<int:document_id>/", document_detail, name="document_detail"),
    path("documents/<int:document_id>/edit/", document_edit, name="document_edit"),
    path("documents/<int:document_id>/delete/", document_delete, name="document_delete"),
    path("documents/<int:document_id>/preview/", document_preview, name="document_preview"),
    path("documents/<int:document_id>/review/", document_review, name="document_review"),
    path(
        "documents/<int:document_id>/download/",
        document_download,
        name="document_download",
    ),
    path("sw/documents/", worker_document_list, name="worker_document_list"),
    path("sw/documents/upload/", worker_document_upload, name="worker_document_upload"),
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
