from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods, require_POST

from accounts.decorators import admin_required, worker_required
from core.audit import write_audit_log
from core.models import AuditLog
from participants.models import Participant
from workers.models import SupportWorker

from .forms import DocumentForm, WorkerDocumentUploadForm
from .models import Document
from .storage import StorageOperationError


def _document_list_url(owner, person_id=None, category="all"):
    query = {"owner": owner}
    if person_id:
        query["person"] = person_id
    if category != "all":
        query["category"] = category
    return f"{reverse('document_list')}?{urlencode(query)}"


def _document_upload_url(owner, person_id=None, category="all"):
    if not person_id:
        return reverse("document_create")
    return_url = _document_list_url(owner, person_id, category)
    key = "worker" if owner == "workers" else "participant"
    query = {
        key: person_id,
        "next": return_url,
    }
    if category == "others":
        query["category"] = Document.Category.GENERAL
    elif category not in {"all", *{value for value, _label in Document.Category.choices}}:
        category = "all"
    elif category != "all":
        query["category"] = category
    return f"{reverse('document_create')}?{urlencode(query)}"


def _document_owner_url(document):
    if document.worker_id:
        return _document_list_url("workers", document.worker_id)
    if document.participant_id:
        return _document_list_url("participants", document.participant_id)
    return reverse("document_list")


def _safe_next_url(request, next_url):
    if not next_url:
        return ""
    if url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ""


def _document_upload_context(initial):
    context_items = []
    participant_id = initial.get("participant")
    worker_id = initial.get("worker")

    if participant_id:
        participant = Participant.objects.filter(id=participant_id).first()
        if participant:
            context_items.append(
                {
                    "label": "Participant",
                    "name": participant.display_name,
                    "detail": participant.ndis_number or participant.get_status_display(),
                }
            )
    if worker_id:
        worker = SupportWorker.objects.filter(id=worker_id).first()
        if worker:
            context_items.append(
                {
                    "label": "Support Worker",
                    "name": worker.display_name,
                    "detail": worker.email or worker.get_status_display(),
                }
            )
    return context_items


def _document_category_tabs(owner, person_id, documents, active_category):
    tabs = [
        {"key": "all", "label": "All", "count": documents.count()},
        {
            "key": Document.Category.PLAN,
            "label": "Plan",
            "count": documents.filter(category=Document.Category.PLAN).count(),
        },
        {
            "key": Document.Category.COMPLIANCE,
            "label": "Compliance",
            "count": documents.filter(category=Document.Category.COMPLIANCE).count(),
        },
        {
            "key": Document.Category.INVOICE,
            "label": "Invoices",
            "count": documents.filter(category=Document.Category.INVOICE).count(),
        },
        {
            "key": Document.Category.SERVICE_LOG,
            "label": "Service logs",
            "count": documents.filter(category=Document.Category.SERVICE_LOG).count(),
        },
        {
            "key": "others",
            "label": "Others",
            "count": documents.filter(category=Document.Category.GENERAL).count(),
        },
    ]
    if owner == "workers":
        tabs = [
            tabs[0],
            tabs[2],
            {
                "key": "others",
                "label": "Others",
                "count": documents.filter(
                    Q(category=Document.Category.GENERAL)
                    | Q(category=Document.Category.COMPLIANCE, required_document_type="")
                ).count(),
            },
        ]

    for tab in tabs:
        tab["url"] = _document_list_url(owner, person_id, tab["key"])
        tab["is_active"] = tab["key"] == active_category
    return tabs


def _filter_documents_for_category(documents, owner, category):
    if category == "all":
        return documents
    if category == "others":
        if owner == "workers":
            return documents.filter(
                Q(category=Document.Category.GENERAL)
                | Q(category=Document.Category.COMPLIANCE, required_document_type="")
            )
        return documents.filter(category=Document.Category.GENERAL)
    valid_categories = {value for value, _label in Document.Category.choices}
    if category in valid_categories:
        return documents.filter(category=category)
    return documents


@admin_required
def document_list(request):
    owner = request.GET.get("owner", "participants")
    if owner not in {"participants", "workers"}:
        owner = "participants"

    category = request.GET.get("category", "all")
    person_id = request.GET.get("person")
    selected_person = None

    if owner == "workers":
        people = SupportWorker.objects.select_related("user").annotate(
            document_count=Count("documents")
        )
        if person_id:
            selected_person = people.filter(id=person_id).first()
        selected_person = selected_person or people.first()
        person_list_title = "Support Worker list"
        person_list_description = "Open a worker to manage their compliance and personal files."
        selected_person_description = (
            "Support worker compliance files, credentials, and flexible personal uploads."
        )
        documents = (
            Document.objects.select_related(
                "participant",
                "worker",
                "invoice",
                "service_log",
                "uploaded_by",
            ).filter(worker=selected_person)
            if selected_person
            else Document.objects.none()
        )
    else:
        people = Participant.objects.annotate(document_count=Count("documents"))
        if person_id:
            selected_person = people.filter(id=person_id).first()
        selected_person = selected_person or people.first()
        person_list_title = "Participant list"
        person_list_description = "Open a person to manage their files."
        selected_person_description = (
            "Participant documents, plan files, reports, and flexible personal uploads."
        )
        documents = (
            Document.objects.select_related(
                "participant",
                "worker",
                "invoice",
                "service_log",
                "uploaded_by",
            ).filter(participant=selected_person)
            if selected_person
            else Document.objects.none()
        )

    valid_categories = {"all", "others"} | {
        value for value, _label in Document.Category.choices
    }
    if category not in valid_categories:
        category = "all"

    documents = documents.order_by("-created_at")
    filtered_documents = _filter_documents_for_category(documents, owner, category)
    expiring_soon_date = timezone.localdate() + timedelta(days=30)

    owner_tabs = [
        {
            "key": "participants",
            "label": "Participants",
            "count": Participant.objects.count(),
            "url": _document_list_url("participants"),
            "is_active": owner == "participants",
        },
        {
            "key": "workers",
            "label": "Support Workers",
            "count": SupportWorker.objects.count(),
            "url": _document_list_url("workers"),
            "is_active": owner == "workers",
        },
    ]
    person_items = [
        {
            "person": person,
            "url": _document_list_url(owner, person.id, category),
            "is_active": selected_person and person.id == selected_person.id,
        }
        for person in people
    ]
    category_tabs = _document_category_tabs(
        owner,
        selected_person.id if selected_person else None,
        documents,
        category,
    )
    active_category_label = next(
        (tab["label"] for tab in category_tabs if tab["key"] == category),
        "All",
    )
    summary = {
        "total": documents.count(),
        "pending_review": documents.filter(
            review_status=Document.ReviewStatus.PENDING_REVIEW
        ).count(),
        "expiring_soon": documents.filter(
            expiry_date__isnull=False,
            expiry_date__lte=expiring_soon_date,
        ).count(),
        "others": next(
            (tab["count"] for tab in category_tabs if tab["key"] == "others"),
            0,
        ),
    }

    return render(
        request,
        "documents/document_list.html",
        {
            "owner": owner,
            "owner_tabs": owner_tabs,
            "person_items": person_items,
            "selected_person": selected_person,
            "selected_person_description": selected_person_description,
            "person_list_title": person_list_title,
            "person_list_description": person_list_description,
            "documents": filtered_documents,
            "category_tabs": category_tabs,
            "active_category": category,
            "active_category_label": active_category_label,
            "summary": summary,
            "upload_url": _document_upload_url(
                owner,
                selected_person.id if selected_person else None,
                category,
            ),
            "current_list_url": _document_list_url(
                owner,
                selected_person.id if selected_person else None,
                category,
            ),
        },
    )


@admin_required
def document_create(request):
    next_url = _safe_next_url(request, request.POST.get("next") or request.GET.get("next", ""))
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
            if next_url:
                return redirect(next_url)
            return redirect(document)
    else:
        initial = {
            key: request.GET[key]
            for key in ("participant", "worker", "invoice", "service_log", "category")
            if request.GET.get(key)
        }
        form = DocumentForm(initial=initial)

    return render(
        request,
        "documents/document_form.html",
        {
            "form": form,
            "next_url": next_url,
            "upload_context_items": _document_upload_context(
                request.POST if request.method == "POST" else form.initial
            ),
        },
    )


@admin_required
def document_detail(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    return render(
        request,
        "documents/document_detail.html",
        {
            "document": document,
            "document_owner_url": _document_owner_url(document),
        },
    )


@admin_required
@require_http_methods(["GET", "POST"])
def document_delete(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    return_url = _safe_next_url(
        request,
        request.POST.get("next") or request.GET.get("next", ""),
    ) or _document_owner_url(document)

    if request.method == "POST":
        document_title = document.title
        document_filename = document.filename
        try:
            document.file.delete(save=False)
        except Exception:
            messages.error(
                request,
                "Could not delete document from private storage. Please try again later or contact admin.",
            )
            return render(
                request,
                "documents/document_confirm_delete.html",
                {"document": document, "return_url": return_url},
            )

        write_audit_log(
            request.user,
            AuditLog.Action.DOCUMENT_DELETED,
            document,
            f"Deleted document {document.id}: {document_title} ({document_filename}).",
        )
        document.delete()
        messages.success(request, f"Deleted document {document_title}.")
        return redirect(return_url)

    return render(
        request,
        "documents/document_confirm_delete.html",
        {"document": document, "return_url": return_url},
    )


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
