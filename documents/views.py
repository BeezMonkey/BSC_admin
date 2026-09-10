from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Count, Max, Q
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
from core.pagination import paginate_queryset
from core.sorting import apply_sorting
from participants.models import Participant
from workers.models import SupportWorker

from .forms import DocumentForm, DocumentMetadataForm, WorkerDocumentUploadForm
from .models import Document
from .storage import StorageOperationError


FILE_MANAGER_CATEGORY_KEYS = {
    "all",
    "others",
    Document.Category.PLAN,
    Document.Category.COMPLIANCE,
    Document.Category.GENERAL,
}
FILE_MANAGER_EXCLUDED_CATEGORIES = [
    Document.Category.INVOICE,
    Document.Category.SERVICE_LOG,
]


def _document_list_url(owner="participants"):
    if owner == "workers":
        return f"{reverse('document_list')}?owner=workers"
    return reverse("document_list")


def _document_owner_detail_url(owner, person_id, category="all"):
    route_name = "worker_document_files" if owner == "workers" else "participant_document_files"
    url = reverse(route_name, args=[person_id])
    if category != "all":
        return f"{url}?{urlencode({'category': category})}"
    return url


def _document_upload_url(owner, person_id=None, category="all"):
    if not person_id:
        return reverse("document_create")
    return_url = _document_owner_detail_url(owner, person_id, category)
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
        return _document_owner_detail_url("workers", document.worker_id)
    if document.participant_id:
        return _document_owner_detail_url("participants", document.participant_id)
    return reverse("document_list")


def _document_owner_key(document):
    if document.worker_id:
        return "workers"
    if document.participant_id:
        return "participants"
    return ""


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


def _document_upload_owner(initial):
    participant_id = initial.get("participant")
    worker_id = initial.get("worker")
    has_invoice = bool(initial.get("invoice"))
    has_service_log = bool(initial.get("service_log"))

    if participant_id and not worker_id and not has_invoice and not has_service_log:
        return "participants"
    if worker_id and not participant_id and not has_invoice and not has_service_log:
        return "workers"
    return ""


def _document_upload_page_copy(upload_context_items, hide_linked_records):
    if hide_linked_records and upload_context_items:
        person_name = upload_context_items[0]["name"]
        return {
            "title": f"Upload file for {person_name}",
            "description": "Choose a folder, attach the file, and add optional notes.",
            "context_note": "This file will be saved under the selected person.",
            "back_label": "Back to uploaded files",
        }
    return {
        "title": "Upload File",
        "description": "Attach a file to a selected person or record.",
        "context_note": (
            "The linked records below are prefilled from Uploaded Files. "
            "You can still change them before uploading."
        ),
        "back_label": "Back to selected files",
    }


def _document_upload_template_context(
    request,
    form,
    next_url,
    hide_linked_records,
):
    upload_context_items = _document_upload_context(
        request.POST if request.method == "POST" else form.initial
    )
    page_copy = _document_upload_page_copy(upload_context_items, hide_linked_records)
    return {
        "form": form,
        "next_url": next_url,
        "upload_context_items": upload_context_items,
        "hide_linked_records": hide_linked_records,
        "upload_page_title": page_copy["title"],
        "upload_page_description": page_copy["description"],
        "upload_context_note": page_copy["context_note"],
        "upload_back_label": page_copy["back_label"],
    }


def _document_category_tabs(owner, person_id, documents, active_category):
    compliance_label = "Compliance" if owner == "workers" else "NDIS Forms"
    tabs = [
        {"key": "all", "label": "All", "count": documents.count()},
        {
            "key": Document.Category.PLAN,
            "label": "Agreement",
            "count": documents.filter(category=Document.Category.PLAN).count(),
        },
        {
            "key": Document.Category.COMPLIANCE,
            "label": compliance_label,
            "count": documents.filter(category=Document.Category.COMPLIANCE).count(),
        },
        {
            "key": "others",
            "label": "Others",
            "count": documents.filter(category=Document.Category.GENERAL).count(),
        },
    ]

    for tab in tabs:
        tab["url"] = _document_owner_detail_url(owner, person_id, tab["key"])
        tab["is_active"] = tab["key"] == active_category
    return tabs


def _filter_documents_for_category(documents, owner, category):
    if category == "all":
        return documents
    if category == "others":
        return documents.filter(category=Document.Category.GENERAL)
    valid_categories = {Document.Category.PLAN, Document.Category.COMPLIANCE}
    if category in valid_categories:
        return documents.filter(category=category)
    return documents


def _document_queryset():
    return Document.objects.exclude(
        category__in=FILE_MANAGER_EXCLUDED_CATEGORIES
    ).select_related(
        "participant",
        "worker",
        "invoice",
        "service_log",
        "uploaded_by",
    )


def _valid_document_category(category):
    if category == Document.Category.GENERAL:
        return "others"
    return category if category in FILE_MANAGER_CATEGORY_KEYS else "all"


def _document_category_filter(owner, category):
    if category == "others":
        return Q(documents__category=Document.Category.GENERAL)
    if category in {Document.Category.PLAN, Document.Category.COMPLIANCE}:
        return Q(documents__category=category)
    return Q()


def _file_manager_document_filter(prefix="documents"):
    return ~Q(**{f"{prefix}__category__in": FILE_MANAGER_EXCLUDED_CATEGORIES})


def _document_category_choices(owner):
    compliance_label = "Compliance" if owner == "workers" else "NDIS Forms"
    return [
        ("all", "All folders"),
        (Document.Category.PLAN, "Agreement"),
        (Document.Category.COMPLIANCE, compliance_label),
        ("others", "Others"),
    ]


def _document_upload_category_choices(owner):
    return DocumentForm.PERSON_UPLOAD_CATEGORY_CHOICES[owner]


def _selected_person_document_context(request, owner, selected_person):
    category = _valid_document_category(request.GET.get("category", "all"))
    query = request.GET.get("q", "").strip()
    review_status = request.GET.get("review_status", "").strip()
    valid_review_statuses = {value for value, _label in Document.ReviewStatus.choices}
    if review_status not in valid_review_statuses:
        review_status = ""

    if owner == "workers":
        selected_person_description = "Support worker files stored in CrazyDomains."
        documents = _document_queryset().filter(worker=selected_person)
    else:
        selected_person_description = "Participant files stored in CrazyDomains."
        documents = _document_queryset().filter(participant=selected_person)

    documents = documents.order_by("-created_at")
    category_tabs = _document_category_tabs(owner, selected_person.id, documents, category)
    filtered_documents = _filter_documents_for_category(documents, owner, category)
    if query:
        filtered_documents = filtered_documents.filter(
            Q(title__icontains=query)
            | Q(original_filename__icontains=query)
            | Q(notes__icontains=query)
            | Q(uploaded_by__username__icontains=query)
        )
    if review_status:
        filtered_documents = filtered_documents.filter(review_status=review_status)

    expiring_soon_date = timezone.localdate() + timedelta(days=30)
    active_category_label = next(
        (tab["label"] for tab in category_tabs if tab["key"] == category),
        "All",
    )
    current_list_url = request.get_full_path()

    return {
        "owner": owner,
        "selected_person": selected_person,
        "selected_person_description": selected_person_description,
        "documents": filtered_documents,
        "category_tabs": category_tabs,
        "active_category": category,
        "active_category_label": active_category_label,
        "query": query,
        "review_status": review_status,
        "review_status_choices": Document.ReviewStatus.choices,
        "reset_url": _document_owner_detail_url(owner, selected_person.id, category),
        "summary": {
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
        },
        "upload_url": _document_upload_url(owner, selected_person.id, category),
        "upload_category_choices": _document_upload_category_choices(owner),
        "upload_category_value": (
            Document.Category.GENERAL if category in {"all", "others"} else category
        ),
        "current_list_url": current_list_url,
        "directory_url": _document_list_url(owner),
    }


@admin_required
def document_list(request):
    owner = request.GET.get("owner", "participants")
    if owner not in {"participants", "workers"}:
        owner = "participants"

    person_id = request.GET.get("person")
    if person_id:
        category = _valid_document_category(request.GET.get("category", "all"))
        return redirect(_document_owner_detail_url(owner, person_id, category))

    query = request.GET.get("q", "").strip()
    category = _valid_document_category(request.GET.get("category", "all"))
    review_status = request.GET.get("review_status", "").strip()
    valid_review_statuses = {value for value, _label in Document.ReviewStatus.choices}
    if review_status not in valid_review_statuses:
        review_status = ""
    coverage = request.GET.get("coverage", "").strip()
    if coverage not in {"has_documents", "no_documents"}:
        coverage = ""

    expiring_soon_date = timezone.localdate() + timedelta(days=30)
    document_filter = _file_manager_document_filter()
    annotations = {
        "document_count": Count(
            "documents",
            filter=document_filter,
            distinct=True,
        ),
        "pending_review_count": Count(
            "documents",
            filter=Q(documents__review_status=Document.ReviewStatus.PENDING_REVIEW)
            & document_filter,
            distinct=True,
        ),
        "expiring_soon_count": Count(
            "documents",
            filter=Q(
                documents__expiry_date__isnull=False,
                documents__expiry_date__lte=expiring_soon_date,
            )
            & document_filter,
            distinct=True,
        ),
        "last_uploaded": Max(
            "documents__created_at",
            filter=document_filter,
        ),
    }

    if owner == "workers":
        people = SupportWorker.objects.select_related("user").annotate(**annotations)
        if query:
            people = people.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone__icontains=query)
            )
        person_type_label = "Support Worker"
        directory_title = "Support Worker directory"
        directory_description = "Find a worker, then open their CrazyDomains file folder."
    else:
        people = Participant.objects.annotate(**annotations)
        if query:
            people = people.filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(preferred_name__icontains=query)
                | Q(ndis_number__icontains=query)
                | Q(phone__icontains=query)
                | Q(email__icontains=query)
            )
        person_type_label = "Participant"
        directory_title = "Participant directory"
        directory_description = "Find a participant, then open their CrazyDomains file folder."

    category_filter = _document_category_filter(owner, category)
    if category_filter:
        people = people.filter(category_filter)
    if review_status:
        people = people.filter(
            Q(documents__review_status=review_status) & document_filter
        )
    if coverage == "has_documents":
        people = people.filter(document_count__gt=0)
    elif coverage == "no_documents":
        people = people.filter(document_count=0)

    people = people.distinct()
    people, sorting = apply_sorting(
        request,
        people,
        {
            "name": ("last_name", "first_name"),
            "documents": ("document_count", "last_name", "first_name"),
            "last_uploaded": ("last_uploaded", "last_name", "first_name"),
        },
        default_sort="name",
    )
    people, pagination = paginate_queryset(request, people)

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
            "detail_url": _document_owner_detail_url(owner, person.id),
            "upload_url": _document_upload_url(owner, person.id),
        }
        for person in people
    ]
    file_manager_documents = Document.objects.exclude(
        category__in=FILE_MANAGER_EXCLUDED_CATEGORIES
    )
    total_documents = file_manager_documents.count()
    directory_summary = {
        "total_documents": total_documents,
        "pending_review": file_manager_documents.filter(
            review_status=Document.ReviewStatus.PENDING_REVIEW
        ).count(),
        "expiring_soon": file_manager_documents.filter(
            expiry_date__isnull=False,
            expiry_date__lte=expiring_soon_date,
        ).count(),
        "people_with_files": (
            Participant.objects.filter(
                documents__isnull=False,
            )
            .filter(_file_manager_document_filter())
            .distinct()
            .count()
            + SupportWorker.objects.filter(
                documents__isnull=False,
            )
            .filter(_file_manager_document_filter())
            .distinct()
            .count()
        ),
    }

    return render(
        request,
        "documents/document_list.html",
        {
            "owner": owner,
            "owner_tabs": owner_tabs,
            "person_items": person_items,
            "person_type_label": person_type_label,
            "directory_title": directory_title,
            "directory_description": directory_description,
            "active_category": category,
            "query": query,
            "review_status": review_status,
            "coverage": coverage,
            "review_status_choices": Document.ReviewStatus.choices,
            "category_choices": _document_category_choices(owner),
            "summary": directory_summary,
            "pagination": pagination,
            "sorting": sorting,
            "has_filters": bool(query or review_status or coverage or category != "all"),
            "current_list_url": request.get_full_path(),
        },
    )


@admin_required
def participant_document_files(request, participant_id):
    participant = get_object_or_404(Participant, id=participant_id)
    return render(
        request,
        "documents/document_person_files.html",
        _selected_person_document_context(request, "participants", participant),
    )


@admin_required
def worker_document_files(request, worker_id):
    worker = get_object_or_404(SupportWorker.objects.select_related("user"), id=worker_id)
    return render(
        request,
        "documents/document_person_files.html",
        _selected_person_document_context(request, "workers", worker),
    )


@admin_required
def document_create(request):
    next_url = _safe_next_url(request, request.POST.get("next") or request.GET.get("next", ""))
    source_data = request.POST if request.method == "POST" else request.GET
    upload_owner = _document_upload_owner(source_data)
    hide_linked_records = bool(upload_owner)
    if request.method == "POST":
        form = DocumentForm(
            request.POST,
            request.FILES,
            upload_owner=upload_owner,
            hide_linked_records=hide_linked_records,
        )
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
                    _document_upload_template_context(
                        request,
                        form,
                        next_url,
                        hide_linked_records,
                    ),
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
            for key in (
                "participant",
                "worker",
                "invoice",
                "service_log",
                "category",
                "required_document_type",
            )
            if request.GET.get(key)
        }
        form = DocumentForm(
            initial=initial,
            upload_owner=upload_owner,
            hide_linked_records=hide_linked_records,
        )

    return render(
        request,
        "documents/document_form.html",
        _document_upload_template_context(
            request,
            form,
            next_url,
            hide_linked_records,
        ),
    )


@admin_required
def document_detail(request, document_id):
    document = get_object_or_404(
        Document.objects.select_related("participant", "worker", "uploaded_by"),
        id=document_id,
    )
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
def document_edit(request, document_id):
    document = get_object_or_404(
        Document.objects.select_related("participant", "worker", "uploaded_by"),
        id=document_id,
    )
    return_url = _safe_next_url(
        request,
        request.POST.get("next") or request.GET.get("next", ""),
    ) or _document_owner_url(document)
    document_owner = _document_owner_key(document)

    if request.method == "POST":
        form = DocumentMetadataForm(
            request.POST,
            instance=document,
            document_owner=document_owner,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Updated file details.")
            return redirect(return_url)
    else:
        form = DocumentMetadataForm(instance=document, document_owner=document_owner)

    return render(
        request,
        "documents/document_edit_form.html",
        {
            "document": document,
            "form": form,
            "return_url": return_url,
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
