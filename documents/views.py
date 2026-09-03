from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required, worker_required
from core.audit import write_audit_log
from core.models import AuditLog

from .forms import DocumentForm, WorkerDocumentUploadForm
from .models import Document
from .storage import StorageOperationError


@admin_required
def document_list(request):
    documents = Document.objects.select_related(
        "participant",
        "worker",
        "invoice",
        "service_log",
        "uploaded_by",
    ).filter(
        category=Document.Category.COMPLIANCE,
        worker__isnull=False,
    )
    return render(
        request,
        "documents/document_list.html",
        {"documents": documents},
    )


@admin_required
def document_create(request):
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploaded_by = request.user
            document.original_filename = document.file.name
            try:
                document.save()
            except StorageOperationError as exc:
                messages.error(request, str(exc))
                return render(
                    request,
                    "documents/document_form.html",
                    {"form": form},
                )
            write_audit_log(
                request.user,
                AuditLog.Action.DOCUMENT_UPLOADED,
                document,
                f"Uploaded document {document.id}: {document.title}.",
            )
            return redirect(document)
    else:
        initial = {
            key: request.GET[key]
            for key in ("participant", "worker", "invoice", "service_log")
            if request.GET.get(key)
        }
        form = DocumentForm(initial=initial)

    return render(
        request,
        "documents/document_form.html",
        {"form": form},
    )


@admin_required
def document_detail(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    return render(request, "documents/document_detail.html", {"document": document})


@admin_required
@require_POST
def document_review(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    review_status = request.POST.get("review_status", "")
    if review_status not in {
        Document.ReviewStatus.APPROVED,
        Document.ReviewStatus.REJECTED,
    }:
        messages.error(request, "Select a valid review action.")
        return redirect("document_detail", document_id=document.id)

    review_note = request.POST.get("review_note", "").strip()
    document.review_status = review_status
    if review_note:
        note = f"Review note: {review_note}"
        document.notes = f"{document.notes}\n\n{note}".strip()
    document.save(update_fields=["review_status", "notes", "updated_at"])

    action = (
        AuditLog.Action.DOCUMENT_APPROVED
        if review_status == Document.ReviewStatus.APPROVED
        else AuditLog.Action.DOCUMENT_REJECTED
    )
    write_audit_log(
        request.user,
        action,
        document,
        f"{document.get_review_status_display()} document {document.id}: {document.title}.",
    )
    messages.success(request, f"Document marked {document.get_review_status_display().lower()}.")
    return redirect("document_detail", document_id=document.id)


@admin_required
def document_download(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    with document.file.open("rb") as file_handle:
        response = HttpResponse(file_handle.read(), content_type="application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{document.filename}"'
    write_audit_log(
        request.user,
        AuditLog.Action.DOCUMENT_DOWNLOADED,
        document,
        f"Downloaded document {document.id}: {document.title}.",
    )
    return response


@admin_required
@xframe_options_sameorigin
def document_preview(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    if not document.is_previewable:
        raise Http404("Document type cannot be previewed.")

    with document.file.open("rb") as file_handle:
        response = HttpResponse(file_handle.read(), content_type=document.preview_content_type)
    response["Content-Disposition"] = f'inline; filename="{document.filename}"'
    return response


def worker_documents_for_user(user):
    worker = getattr(user, "supportworker", None)
    if not worker:
        return Document.objects.none()
    return Document.objects.filter(worker=worker)


def required_compliance_items_for_worker(worker):
    documents = {}
    for document in Document.objects.filter(
        worker=worker,
        category=Document.Category.COMPLIANCE,
        required_document_type__gt="",
    ).order_by("-created_at"):
        documents.setdefault(document.required_document_type, document)
    return [
        {
            "value": value,
            "label": label,
            "document": documents.get(value),
        }
        for value, label in Document.RequiredDocumentType.choices
    ]


def valid_required_document_type(value):
    valid_values = {choice_value for choice_value, _ in Document.RequiredDocumentType.choices}
    return value if value in valid_values else ""


@worker_required
def worker_document_list(request):
    worker = getattr(request.user, "supportworker", None)
    documents = worker_documents_for_user(request.user).filter(required_document_type="").exclude(
        category=Document.Category.SERVICE_LOG,
    )
    required_documents = required_compliance_items_for_worker(worker) if worker else []
    return render(
        request,
        "documents/worker_document_list.html",
        {
            "documents": documents,
            "required_documents": required_documents,
        },
    )


@worker_required
def worker_document_upload(request):
    worker = getattr(request.user, "supportworker", None)
    requested_type = request.POST.get("required_document_type") or request.GET.get("type", "")
    locked_required_document_type = valid_required_document_type(requested_type)
    if request.method == "POST":
        form = WorkerDocumentUploadForm(
            request.POST,
            request.FILES,
            locked_required_document_type=locked_required_document_type,
        )
        if form.is_valid():
            required_document_type = form.cleaned_data.get("required_document_type", "")
            title = (
                Document.RequiredDocumentType(required_document_type).label
                if required_document_type
                else form.cleaned_data["title"]
            )
            uploaded_file = form.cleaned_data["file"]
            try:
                document = Document.objects.create(
                    title=title,
                    category=Document.Category.COMPLIANCE,
                    worker=worker,
                    required_document_type=required_document_type,
                    review_status=Document.ReviewStatus.PENDING_REVIEW,
                    issue_date=form.cleaned_data["issue_date"],
                    expiry_date=form.cleaned_data["expiry_date"],
                    notes=form.cleaned_data["notes"],
                    file=uploaded_file,
                    original_filename=uploaded_file.name,
                    uploaded_by=request.user,
                )
            except StorageOperationError as exc:
                messages.error(request, str(exc))
                return render(
                    request,
                    "documents/worker_document_upload.html",
                    {
                        "form": form,
                        "is_required_upload": form.is_required_document,
                        "selected_required_document_label": form.selected_required_document_label,
                    },
                )
            write_audit_log(
                request.user,
                AuditLog.Action.DOCUMENT_UPLOADED,
                document,
                f"Uploaded worker compliance document {document.id}: {document.title}.",
            )
            messages.success(request, "Document submitted for admin review.")
            return redirect("worker_document_list")
    else:
        form = WorkerDocumentUploadForm(
            locked_required_document_type=locked_required_document_type,
        )

    return render(
        request,
        "documents/worker_document_upload.html",
        {
            "form": form,
            "is_required_upload": form.is_required_document,
            "selected_required_document_label": form.selected_required_document_label,
        },
    )


@worker_required
def worker_document_detail(request, document_id):
    document = get_object_or_404(worker_documents_for_user(request.user), id=document_id)
    return render(request, "documents/worker_document_detail.html", {"document": document})


@worker_required
def worker_document_download(request, document_id):
    document = get_object_or_404(worker_documents_for_user(request.user), id=document_id)
    with document.file.open("rb") as file_handle:
        response = HttpResponse(file_handle.read(), content_type="application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{document.filename}"'
    return response
