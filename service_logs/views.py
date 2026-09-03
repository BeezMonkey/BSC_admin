from contextlib import suppress

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required, worker_required
from core.audit import write_audit_log
from core.models import AuditLog
from core.formatting import format_display_time
from core.navigation import get_safe_return_url
from core.pagination import paginate_queryset
from core.sorting import apply_sorting
from documents.forms import validate_service_log_attachments
from documents.models import Document
from documents.storage import StorageOperationError
from invoices.views import (
    INVOICE_STATIC_LOGO_PATH,
    build_simple_pdf,
    load_pdf_image,
    pdf_image,
    pdf_line,
    pdf_text,
    safe_filename_part,
    wrap_pdf_text,
)
from scheduling.models import Shift

from .forms import ServiceLogForm
from .models import ServiceLog
from .notifications import notify_admin_service_log_submitted


@admin_required
def service_log_list(request):
    status_counts = {
        row["status"]: row["count"]
        for row in ServiceLog.objects.values("status").annotate(count=Count("id"))
    }
    total_count = sum(status_counts.values())
    service_logs = ServiceLog.objects.select_related(
        "shift",
        "participant",
        "worker",
        "support_item",
    )
    status = request.GET.get("status", "").strip()
    has_filters = bool(status)
    if status:
        service_logs = service_logs.filter(status=status)
    status_label = dict(ServiceLog.Status.choices).get(status)
    filter_summary = f"Showing {status_label.lower()} service logs." if status_label else ""
    status_overview = [
        {
            "label": "All logs",
            "count_label": f"{total_count} record{'s' if total_count != 1 else ''}",
            "description": "Full service log history",
            "url": reverse("service_log_list"),
            "active": not status,
        },
        {
            "label": "Submitted",
            "count_label": f"{status_counts.get(ServiceLog.Status.SUBMITTED, 0)} waiting",
            "description": "Waiting for admin review",
            "url": f"{reverse('service_log_list')}?status={ServiceLog.Status.SUBMITTED}",
            "active": status == ServiceLog.Status.SUBMITTED,
        },
        {
            "label": "Approved",
            "count_label": f"{status_counts.get(ServiceLog.Status.APPROVED, 0)} ready",
            "description": "Ready to invoice",
            "url": f"{reverse('service_log_list')}?status={ServiceLog.Status.APPROVED}",
            "active": status == ServiceLog.Status.APPROVED,
        },
        {
            "label": "Invoiced",
            "count_label": f"{status_counts.get(ServiceLog.Status.INVOICED, 0)} billed",
            "description": "Already converted to invoices",
            "url": f"{reverse('service_log_list')}?status={ServiceLog.Status.INVOICED}",
            "active": status == ServiceLog.Status.INVOICED,
        },
        {
            "label": "Rejected",
            "count_label": f"{status_counts.get(ServiceLog.Status.REJECTED, 0)} returned",
            "description": "Needs worker correction",
            "url": f"{reverse('service_log_list')}?status={ServiceLog.Status.REJECTED}",
            "active": status == ServiceLog.Status.REJECTED,
        },
    ]
    service_logs, sorting = apply_sorting(
        request,
        service_logs,
        {
            "date": ("service_date", "id"),
            "participant": ("participant__last_name", "participant__first_name", "service_date"),
            "worker": ("worker__last_name", "worker__first_name", "service_date"),
            "status": ("status", "service_date"),
        },
    )
    service_logs, pagination = paginate_queryset(request, service_logs)
    return render(
        request,
        "service_logs/service_log_list.html",
        {
            "service_logs": service_logs,
            "pagination": pagination,
            "sorting": sorting,
            "status": status,
            "has_filters": has_filters,
            "status_choices": ServiceLog.Status.choices,
            "status_overview": status_overview,
            "filter_summary": filter_summary,
            "current_list_url": request.get_full_path(),
        },
    )


@admin_required
def service_log_detail(request, service_log_id):
    service_log = get_object_or_404(
        ServiceLog.objects.select_related(
            "shift",
            "participant",
            "worker",
            "support_item",
        ),
        id=service_log_id,
    )
    return render(
        request,
        "service_logs/service_log_detail.html",
        {
            "service_log": service_log,
            "return_url": get_safe_return_url(request, reverse("service_log_list")),
        },
    )


def service_log_download_filename(service_log):
    service_date = service_log.service_date.strftime("%Y%m%d")
    participant_name = safe_filename_part(
        service_log.participant.display_name,
        "Participant",
    )
    return f"ServiceLog_{service_date}_{service_log.id}_{participant_name}.pdf"


def pdf_value(value):
    value = str(value or "").strip()
    return value or "-"


def pdf_datetime(value):
    if not value:
        return "-"
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M")


def append_service_log_pdf_row(lines, label, value, x, y, max_width=150):
    lines.append(pdf_text(label, x, y, 8.5, "F2"))
    wrapped_lines = wrap_pdf_text(pdf_value(value), max_width, 8.5)
    for index, wrapped_line in enumerate(wrapped_lines):
        lines.append(pdf_text(wrapped_line, x + 96, y - (index * 11), 8.5))
    return y - max(16, len(wrapped_lines) * 11)


def append_service_log_pdf_section(lines, heading, x, y, width):
    lines.extend(
        [
            pdf_text(heading, x, y, 10, "F2"),
            pdf_line(x, y - 10, x + width, y - 10, width=0.75, color=(0.82, 0.84, 0.88)),
        ]
    )
    return y - 28


def service_log_pdf_pages(service_log):
    page_left = 32
    page_right = 580
    header_y = 742
    logo_width = 208
    logo_height = 43
    logo_y = header_y - 25
    detail_x = 430
    divider_y = 684
    left_x = page_left
    right_x = 326
    section_width = 254
    details_y = 640

    logo_path = settings.BASE_DIR / INVOICE_STATIC_LOGO_PATH
    logo_image = load_pdf_image(logo_path)
    lines = [
        pdf_text("SERVICE LOG", detail_x, 738, 10.5, "F2"),
        pdf_text(f"Log ID: # {service_log.id}", detail_x, 724, 8.5),
        pdf_text(f"Service Date: {service_log.service_date:%d/%m/%Y}", detail_x, 711, 8.5),
        pdf_text(f"Status: {service_log.get_status_display()}", detail_x, 698, 8.5),
        pdf_line(page_left, divider_y, page_right, divider_y, width=3),
    ]
    if logo_image:
        lines.insert(0, pdf_image(logo_image, page_left, logo_y, logo_width, logo_height))
    else:
        lines.insert(0, pdf_text("Brisbane Star Care", page_left, header_y, 14, "F2"))

    left_y = append_service_log_pdf_section(lines, "Service Details", left_x, details_y, section_width)
    left_y = append_service_log_pdf_row(lines, "Participant", service_log.participant.display_name, left_x, left_y)
    left_y = append_service_log_pdf_row(lines, "Worker", service_log.worker.display_name, left_x, left_y)
    left_y = append_service_log_pdf_row(lines, "Shift ID", service_log.shift_id, left_x, left_y)
    left_y = append_service_log_pdf_row(lines, "Support item", service_log.support_item, left_x, left_y)
    left_y = append_service_log_pdf_row(
        lines,
        "Actual time",
        f"{format_display_time(service_log.actual_start_time)} - {format_display_time(service_log.actual_end_time)}",
        left_x,
        left_y,
    )
    left_y = append_service_log_pdf_row(lines, "Break", f"{service_log.break_minutes} minutes", left_x, left_y)
    left_y = append_service_log_pdf_row(lines, "Actual hours", f"{service_log.actual_hours:.2f}", left_x, left_y)
    append_service_log_pdf_row(lines, "Kilometres", f"{service_log.kilometres:.2f}", left_x, left_y)

    right_y = append_service_log_pdf_section(lines, "Review", right_x, details_y, section_width)
    right_y = append_service_log_pdf_row(lines, "Submitted", pdf_datetime(service_log.submitted_at), right_x, right_y)
    right_y = append_service_log_pdf_row(lines, "Reviewed by", service_log.reviewed_by or "-", right_x, right_y)
    right_y = append_service_log_pdf_row(lines, "Reviewed at", pdf_datetime(service_log.reviewed_at), right_x, right_y)
    append_service_log_pdf_row(lines, "Rejection", service_log.rejection_reason, right_x, right_y)

    notes_y = min(left_y, right_y) - 44
    y = append_service_log_pdf_section(lines, "Notes", page_left, notes_y, page_right - page_left)
    y = append_service_log_pdf_row(lines, "Case notes", service_log.case_notes, page_left, y, max_width=410)
    y = append_service_log_pdf_row(lines, "Worker notes", service_log.worker_notes, page_left, y, max_width=410)

    attachment_names = [document.filename for document in service_log.documents.all()]
    attachment_text = ", ".join(attachment_names) if attachment_names else "No attachments"
    y = append_service_log_pdf_section(lines, "Attachments", page_left, y - 24, page_right - page_left)
    append_service_log_pdf_row(lines, "Files", attachment_text, page_left, y, max_width=410)
    return [lines]


@admin_required
def service_log_pdf(request, service_log_id):
    service_log = get_object_or_404(
        ServiceLog.objects.select_related(
            "shift",
            "participant",
            "worker",
            "support_item",
            "reviewed_by",
        ).prefetch_related("documents"),
        id=service_log_id,
    )
    response = HttpResponse(
        build_simple_pdf(service_log_pdf_pages(service_log)),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{service_log_download_filename(service_log)}"'
    )
    return response


@admin_required
@require_POST
def service_log_approve(request, service_log_id):
    service_log = get_object_or_404(
        ServiceLog,
        id=service_log_id,
        status=ServiceLog.Status.SUBMITTED,
    )
    service_log.status = ServiceLog.Status.APPROVED
    service_log.reviewed_by = request.user
    service_log.reviewed_at = timezone.now()
    service_log.rejection_reason = ""
    service_log.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "updated_at",
        ],
    )
    write_audit_log(
        request.user,
        AuditLog.Action.SERVICE_LOG_APPROVED,
        service_log,
        f"Approved service log {service_log.id}.",
    )
    messages.success(request, "Service log approved.")
    return redirect("service_log_detail", service_log_id=service_log.id)


@admin_required
@require_POST
def service_log_reject(request, service_log_id):
    service_log = get_object_or_404(
        ServiceLog,
        id=service_log_id,
        status=ServiceLog.Status.SUBMITTED,
    )
    rejection_reason = request.POST.get("rejection_reason", "").strip()
    if not rejection_reason:
        messages.error(request, "Rejection reason is required.")
        return redirect("service_log_detail", service_log_id=service_log.id)

    service_log.status = ServiceLog.Status.REJECTED
    service_log.reviewed_by = request.user
    service_log.reviewed_at = timezone.now()
    service_log.rejection_reason = rejection_reason
    service_log.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "rejection_reason",
            "updated_at",
        ],
    )
    write_audit_log(
        request.user,
        AuditLog.Action.SERVICE_LOG_REJECTED,
        service_log,
        f"Rejected service log {service_log.id}.",
    )
    messages.success(request, "Service log rejected.")
    return redirect("service_log_detail", service_log_id=service_log.id)


@worker_required
def worker_log_list(request):
    worker = getattr(request.user, "supportworker", None)
    service_logs = ServiceLog.objects.none()
    if worker:
        service_logs = ServiceLog.objects.filter(worker=worker).select_related(
            "shift",
            "participant",
            "support_item",
        )

    return render(
        request,
        "service_logs/worker_log_list.html",
        {"service_logs": service_logs},
    )


@worker_required
def worker_service_log_detail(request, service_log_id):
    worker = getattr(request.user, "supportworker", None)
    service_log = get_object_or_404(
        ServiceLog.objects.select_related("shift", "participant", "support_item"),
        id=service_log_id,
        worker=worker,
    )
    return render(
        request,
        "service_logs/worker_service_log_detail.html",
        {"service_log": service_log},
    )


@worker_required
def worker_service_log_create(request, shift_id):
    worker = getattr(request.user, "supportworker", None)
    shift = get_object_or_404(
        Shift.objects.select_related("participant", "worker", "support_item"),
        id=shift_id,
        worker=worker,
        status__in=[Shift.Status.PUBLISHED, Shift.Status.CONFIRMED],
    )
    if hasattr(shift, "service_log"):
        raise Http404("Service log already exists for this shift.")

    initial = {
        "actual_start_time": shift.start_time.strftime("%H:%M"),
        "actual_end_time": shift.end_time.strftime("%H:%M"),
        "break_minutes": shift.break_minutes,
    }
    if request.method == "POST":
        form = ServiceLogForm(request.POST)
        attachments = request.FILES.getlist("attachments")
        if form.is_valid():
            try:
                validate_service_log_attachments(attachments)
            except ValidationError as error:
                form.add_error(None, error)
                return render(
                    request,
                    "service_logs/worker_service_log_form.html",
                    {"form": form, "shift": shift},
                )

            stored_attachment_documents = []
            try:
                with transaction.atomic():
                    service_log = ServiceLog.objects.create_from_shift(
                        shift=shift,
                        actual_start_time=form.cleaned_data["actual_start_time"],
                        actual_end_time=form.cleaned_data["actual_end_time"],
                        break_minutes=form.cleaned_data["break_minutes"],
                        actual_hours=form.cleaned_data["actual_hours"],
                        kilometres=form.cleaned_data["kilometres"],
                        case_notes=form.cleaned_data["case_notes"],
                        worker_notes=form.cleaned_data["worker_notes"],
                    )
                    for uploaded_file in attachments:
                        document = Document.objects.create(
                            title=f"Service log attachment - {uploaded_file.name}",
                            category=Document.Category.SERVICE_LOG,
                            participant=shift.participant,
                            worker=worker,
                            service_log=service_log,
                            review_status=Document.ReviewStatus.PENDING_REVIEW,
                            file=uploaded_file,
                            original_filename=uploaded_file.name,
                            uploaded_by=request.user,
                        )
                        stored_attachment_documents.append(document)
                        write_audit_log(
                            request.user,
                            AuditLog.Action.DOCUMENT_UPLOADED,
                            document,
                            f"Uploaded service log attachment {document.id} for service log {service_log.id}.",
                        )
                    shift.status = Shift.Status.COMPLETED
                    shift.completed_at = timezone.now()
                    shift.save(update_fields=["status", "completed_at", "updated_at"])
            except StorageOperationError as exc:
                for document in stored_attachment_documents:
                    if document.file:
                        with suppress(Exception):
                            document.file.delete(save=False)
                form.add_error(None, exc)
                return render(
                    request,
                    "service_logs/worker_service_log_form.html",
                    {"form": form, "shift": shift},
                )

            notify_admin_service_log_submitted(service_log, request=request)
            messages.success(request, "Service log submitted for admin review.")
            return redirect("worker_service_log_detail", service_log_id=service_log.id)
    else:
        form = ServiceLogForm(initial=initial)

    return render(
        request,
        "service_logs/worker_service_log_form.html",
        {"form": form, "shift": shift},
    )
