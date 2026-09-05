import csv
import re
import zlib
from collections import OrderedDict
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, DecimalField, Prefetch, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from PIL import Image

from accounts.decorators import admin_required
from accounts.decorators import finance_required
from coordinators.models import CoordinationLog
from core.audit import write_audit_log
from core.models import AuditLog
from core.navigation import get_safe_return_url
from core.pagination import paginate_queryset
from core.sorting import apply_sorting
from service_logs.models import ServiceLog
from scheduling.models import SupportItem

from .forms import (
    InvoiceCreateForm,
    InvoiceSettingsForm,
    SupportCoordinationInvoiceCreateForm,
    TravelClaimForm,
)
from .models import Invoice, InvoiceLine, InvoiceSettings


INVOICE_STATIC_LOGO_PATH = Path("static/img/bsc-logo.png")
TRAVEL_SUPPORT_ITEM_NUMBER = "04_799_0125_6_1"


def format_filter_date(value):
    parsed_date = parse_date(value)
    if not parsed_date:
        return value
    return parsed_date.strftime("%d/%m/%Y")


def format_au_date(value):
    return value.strftime("%d/%m/%Y")


def safe_filename_part(value, fallback="Invoice"):
    value = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "")).strip("_")
    return value or fallback


def invoice_download_filename(invoice, extension):
    invoice_date = timezone.localtime(invoice.created_at).strftime("%y%m%d")
    invoice_sequence = safe_filename_part(
        invoice.invoice_number.rsplit("-", 1)[-1],
        "0000",
    )
    participant_name = safe_filename_part(invoice.participant.display_name, "Participant")
    prefix = (
        "SC_Invoice"
        if invoice.invoice_type == Invoice.InvoiceType.SUPPORT_COORDINATION
        else "Invoice"
    )
    return f"{prefix}_{invoice_date}_{invoice_sequence}_{participant_name}.{extension}"


def build_invoice_filter_summary(status, q, participant_query, period_from, period_to):
    status_label = dict(Invoice.Status.choices).get(status)
    if not any([status_label, q, participant_query, period_from, period_to]):
        return ""

    summary = f"Showing {status_label.lower()} invoices" if status_label else "Showing invoices"
    if q:
        summary += f' matching "{q}"'
    if participant_query:
        summary += f" for {participant_query}"
    if period_from and period_to:
        summary += f" from {format_filter_date(period_from)} to {format_filter_date(period_to)}"
    elif period_from:
        summary += f" from {format_filter_date(period_from)}"
    elif period_to:
        summary += f" to {format_filter_date(period_to)}"
    return f"{summary}."


@finance_required
def invoice_list(request):
    status_counts = {
        row["status"]: row["count"]
        for row in Invoice.objects.values("status").annotate(count=Count("id"))
    }
    total_count = sum(status_counts.values())
    invoices = Invoice.objects.select_related("participant", "created_by").annotate(
        total_amount_sort=Coalesce(
            Sum("lines__line_total"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    ).order_by("-created_at")
    q = request.GET.get("q", "").strip()
    participant_query = request.GET.get("participant", "").strip()
    status = request.GET.get("status", "").strip()
    period_from = request.GET.get("period_from", "").strip()
    period_to = request.GET.get("period_to", "").strip()
    has_filters = bool(q or participant_query or status or period_from or period_to)

    if q:
        invoices = invoices.filter(invoice_number__icontains=q)
    if participant_query:
        invoices = invoices.filter(
            Q(participant__first_name__icontains=participant_query)
            | Q(participant__last_name__icontains=participant_query)
        )
    if status:
        invoices = invoices.filter(status=status)
    if period_from:
        invoices = invoices.filter(period_end__gte=period_from)
    if period_to:
        invoices = invoices.filter(period_start__lte=period_to)
    filter_summary = build_invoice_filter_summary(
        status,
        q,
        participant_query,
        period_from,
        period_to,
    )
    draft_count = status_counts.get(Invoice.Status.DRAFT, 0)
    issued_count = status_counts.get(Invoice.Status.ISSUED, 0)
    paid_count = status_counts.get(Invoice.Status.PAID, 0)
    cancelled_count = status_counts.get(Invoice.Status.CANCELLED, 0)
    status_overview = [
        {
            "label": "All invoices",
            "count_label": f"{total_count} record{'s' if total_count != 1 else ''}",
            "description": "Full billing history",
            "url": reverse("invoice_placeholder"),
            "active": not status,
        },
        {
            "label": "Draft",
            "count_label": f"{draft_count} draft{'s' if draft_count != 1 else ''}",
            "description": "Ready to review before issuing",
            "url": f"{reverse('invoice_placeholder')}?status={Invoice.Status.DRAFT}",
            "active": status == Invoice.Status.DRAFT,
        },
        {
            "label": "Issued",
            "count_label": f"{issued_count} awaiting payment",
            "description": "Sent invoices not marked paid",
            "url": f"{reverse('invoice_placeholder')}?status={Invoice.Status.ISSUED}",
            "active": status == Invoice.Status.ISSUED,
        },
        {
            "label": "Paid",
            "count_label": f"{paid_count} paid",
            "description": "Completed billing records",
            "url": f"{reverse('invoice_placeholder')}?status={Invoice.Status.PAID}",
            "active": status == Invoice.Status.PAID,
        },
        {
            "label": "Cancelled",
            "count_label": f"{cancelled_count} cancelled",
            "description": "Removed from active billing",
            "url": f"{reverse('invoice_placeholder')}?status={Invoice.Status.CANCELLED}",
            "active": status == Invoice.Status.CANCELLED,
        },
    ]
    invoices, sorting = apply_sorting(
        request,
        invoices,
        {
            "invoice": ("invoice_number",),
            "participant": ("participant__last_name", "participant__first_name", "invoice_number"),
            "period": ("period_start", "period_end", "invoice_number"),
            "status": ("status", "invoice_number"),
            "total": ("total_amount_sort", "invoice_number"),
        },
    )
    invoices, pagination = paginate_queryset(request, invoices)

    return render(
        request,
        "invoices/invoice_list.html",
        {
            "invoices": invoices,
            "pagination": pagination,
            "sorting": sorting,
            "q": q,
            "participant_query": participant_query,
            "status": status,
            "period_from": period_from,
            "period_to": period_to,
            "has_filters": has_filters,
            "status_choices": Invoice.Status.choices,
            "status_overview": status_overview,
            "filter_summary": filter_summary,
            "current_list_url": request.get_full_path(),
        },
    )


def get_billable_logs(participant, period_start, period_end):
    return ServiceLog.objects.filter(
        participant=participant,
        service_date__gte=period_start,
        service_date__lte=period_end,
        status=ServiceLog.Status.APPROVED,
        invoice_lines__isnull=True,
    ).select_related("participant", "worker", "support_item")


def get_billable_coordination_logs(participant, period_start, period_end):
    return CoordinationLog.objects.filter(
        participant=participant,
        service_date__gte=period_start,
        service_date__lte=period_end,
        status=CoordinationLog.Status.APPROVED,
        invoice_lines__isnull=True,
    ).select_related("participant", "coordinator").order_by("service_date", "id")


def get_selected_billable_logs(service_log_ids, require_single_participant=True):
    try:
        unique_ids = [
            int(service_log_id) for service_log_id in dict.fromkeys(service_log_ids)
        ]
    except (TypeError, ValueError):
        return [], "Selected service logs are no longer available for invoicing."
    service_logs = ServiceLog.objects.filter(
        id__in=unique_ids,
        status=ServiceLog.Status.APPROVED,
        invoice_lines__isnull=True,
    ).select_related("participant", "worker", "support_item")
    service_logs = list(service_logs.order_by("service_date", "id"))
    if len(service_logs) != len(unique_ids):
        return [], "Selected service logs are no longer available for invoicing."
    participant_ids = {service_log.participant_id for service_log in service_logs}
    if require_single_participant and len(participant_ids) > 1:
        return [], "Selected service logs must belong to one participant."
    return service_logs, ""


def get_selected_billable_coordination_logs(
    coordination_log_ids,
    require_single_participant=True,
):
    try:
        unique_ids = [
            int(coordination_log_id)
            for coordination_log_id in dict.fromkeys(coordination_log_ids)
        ]
    except (TypeError, ValueError):
        return [], "Selected coordination logs are no longer available for invoicing."

    coordination_logs = CoordinationLog.objects.filter(
        id__in=unique_ids,
        status=CoordinationLog.Status.APPROVED,
        invoice_lines__isnull=True,
    ).select_related("participant", "coordinator")
    coordination_logs = list(coordination_logs.order_by("service_date", "id"))
    if len(coordination_logs) != len(unique_ids):
        return [], "Selected coordination logs are no longer available for invoicing."

    participant_ids = {log.participant_id for log in coordination_logs}
    if require_single_participant and len(participant_ids) > 1:
        return [], "Selected coordination logs must belong to one participant."
    return coordination_logs, ""


def build_selected_invoice_form_data(service_logs):
    return {
        "participant": service_logs[0].participant_id,
        "period_start": min(log.service_date for log in service_logs).isoformat(),
        "period_end": max(log.service_date for log in service_logs).isoformat(),
    }


def build_invoice_rows(service_logs, data=None):
    return [
        {
            "service_log": service_log,
            "travel_form": TravelClaimForm(
                data=data,
                prefix=f"travel-{service_log.id}",
                service_log=service_log,
            ),
        }
        for service_log in service_logs
    ]


def build_selected_invoice_groups(service_logs):
    groups = OrderedDict()
    ordered_logs = sorted(
        service_logs,
        key=lambda log: (
            log.participant.display_name,
            log.service_date,
            log.id,
        ),
    )
    for service_log in ordered_logs:
        group = groups.setdefault(
            service_log.participant_id,
            {
                "participant": service_log.participant,
                "service_logs": [],
            },
        )
        group["service_logs"].append(service_log)

    invoice_groups = []
    for group in groups.values():
        logs = group["service_logs"]
        period_start = min(log.service_date for log in logs)
        period_end = max(log.service_date for log in logs)
        period_label = format_au_date(period_start)
        if period_start != period_end:
            period_label = f"{period_label} - {format_au_date(period_end)}"
        invoice_groups.append(
            {
                "participant": group["participant"],
                "period_start": period_start,
                "period_end": period_end,
                "period_label": period_label,
                "total_hours": sum((log.actual_hours for log in logs), Decimal("0.00")),
                "count": len(logs),
                "selected_service_log_ids": [log.id for log in logs],
                "invoice_rows": build_invoice_rows(logs),
            }
        )
    return invoice_groups


def build_support_coordination_invoice_form_data(coordination_logs):
    return {
        "participant": coordination_logs[0].participant_id,
        "period_start": min(log.service_date for log in coordination_logs).isoformat(),
        "period_end": max(log.service_date for log in coordination_logs).isoformat(),
    }


def build_coordination_invoice_rows(coordination_logs):
    return [
        {"coordination_log": coordination_log}
        for coordination_log in coordination_logs
    ]


def build_selected_coordination_invoice_groups(coordination_logs):
    groups = OrderedDict()
    ordered_logs = sorted(
        coordination_logs,
        key=lambda log: (
            log.participant.display_name,
            log.service_date,
            log.id,
        ),
    )
    for coordination_log in ordered_logs:
        group = groups.setdefault(
            coordination_log.participant_id,
            {
                "participant": coordination_log.participant,
                "coordination_logs": [],
            },
        )
        group["coordination_logs"].append(coordination_log)

    invoice_groups = []
    for group in groups.values():
        logs = group["coordination_logs"]
        period_start = min(log.service_date for log in logs)
        period_end = max(log.service_date for log in logs)
        period_label = format_au_date(period_start)
        if period_start != period_end:
            period_label = f"{period_label} - {format_au_date(period_end)}"
        invoice_groups.append(
            {
                "participant": group["participant"],
                "period_start": period_start,
                "period_end": period_end,
                "period_label": period_label,
                "total_hours": sum((log.actual_hours for log in logs), Decimal("0.00")),
                "count": len(logs),
                "selected_coordination_log_ids": [log.id for log in logs],
                "invoice_rows": build_coordination_invoice_rows(logs),
            }
        )
    return invoice_groups


@finance_required
def invoice_create(request):
    selected_ids = request.GET.getlist("service_log_ids")
    if request.method == "POST":
        selected_ids = request.POST.getlist("service_log_ids")
    selected_service_logs = []
    selected_error = ""
    active_selected_ids = selected_ids
    selected_invoice_groups = []

    if selected_ids:
        selected_service_logs, selected_error = get_selected_billable_logs(
            selected_ids,
            require_single_participant=request.method == "POST",
        )

    if (
        request.method == "GET"
        and selected_service_logs
        and len({log.participant_id for log in selected_service_logs}) == 1
    ):
        form = InvoiceCreateForm(build_selected_invoice_form_data(selected_service_logs))
        form.is_valid()
    elif request.method == "POST":
        form = InvoiceCreateForm(request.POST)
    elif request.method == "GET" and selected_service_logs:
        form = InvoiceCreateForm()
    else:
        form = InvoiceCreateForm(request.GET or None)

    service_logs = ServiceLog.objects.none()
    if selected_error:
        active_selected_ids = []
        if request.method == "GET" and form.is_valid():
            selected_error = ""
            service_logs = get_billable_logs(
                form.cleaned_data["participant"],
                form.cleaned_data["period_start"],
                form.cleaned_data["period_end"],
            )
    elif selected_service_logs:
        service_logs = selected_service_logs
        if request.method == "GET":
            selected_invoice_groups = build_selected_invoice_groups(selected_service_logs)
    elif form.is_valid():
        service_logs = get_billable_logs(
            form.cleaned_data["participant"],
            form.cleaned_data["period_start"],
            form.cleaned_data["period_end"],
        )

    if request.method == "POST":
        if selected_error:
            service_logs = ServiceLog.objects.none()
        elif form.is_valid():
            if selected_service_logs:
                service_logs = selected_service_logs
            else:
                service_logs = get_billable_logs(
                    form.cleaned_data["participant"],
                    form.cleaned_data["period_start"],
                    form.cleaned_data["period_end"],
                )
            service_logs = [
                service_log
                for service_log in service_logs
                if service_log.participant_id == form.cleaned_data["participant"].id
                and form.cleaned_data["period_start"]
                <= service_log.service_date
                <= form.cleaned_data["period_end"]
            ]
            if selected_service_logs and len(service_logs) != len(selected_service_logs):
                selected_error = "Selected service logs do not match the invoice participant and period."
                service_logs = ServiceLog.objects.none()
            elif not service_logs:
                messages.error(request, "No approved logs found for this invoice.")
            else:
                invoice_rows = build_invoice_rows(service_logs, request.POST)
                if all(row["travel_form"].is_valid() for row in invoice_rows):
                    travel_claims = {
                        row["service_log"].id: row["travel_form"].cleaned_data["amount"]
                        for row in invoice_rows
                        if row["travel_form"].cleaned_data["amount"] > Decimal("0.00")
                    }
                    travel_support_item = None
                    if travel_claims:
                        travel_support_item = SupportItem.objects.filter(
                            item_number=TRAVEL_SUPPORT_ITEM_NUMBER,
                            is_active=True,
                        ).first()
                        if not travel_support_item:
                            selected_error = (
                                "The active Provider travel - non-labour support item is "
                                "required before travel claims can be invoiced."
                            )

                    if not travel_claims or travel_support_item:
                        with transaction.atomic():
                            invoice = Invoice.objects.create(
                                participant=form.cleaned_data["participant"],
                                period_start=form.cleaned_data["period_start"],
                                period_end=form.cleaned_data["period_end"],
                                created_by=request.user,
                            )
                            for service_log in service_logs:
                                InvoiceLine.objects.create_from_service_log(
                                    invoice=invoice,
                                    service_log=service_log,
                                )
                                travel_amount = travel_claims.get(service_log.id)
                                if travel_amount:
                                    InvoiceLine.objects.create_travel_claim_from_service_log(
                                        invoice=invoice,
                                        service_log=service_log,
                                        support_item=travel_support_item,
                                        amount=travel_amount,
                                    )
                                service_log.status = ServiceLog.Status.INVOICED
                                service_log.save(update_fields=["status", "updated_at"])
                        write_audit_log(
                            request.user,
                            AuditLog.Action.INVOICE_CREATED,
                            invoice,
                            f"Created invoice {invoice.invoice_number}.",
                        )
                        messages.success(request, "Invoice created.")
                        return redirect(invoice)

    invoice_rows = build_invoice_rows(
        service_logs,
        request.POST if request.method == "POST" else None,
    )

    return render(
        request,
        "invoices/invoice_form.html",
        {
            "form": form,
            "service_logs": service_logs,
            "invoice_rows": invoice_rows,
            "selected_invoice_groups": selected_invoice_groups,
            "selected_error": selected_error,
            "selected_service_log_ids": active_selected_ids,
        },
    )


@admin_required
def support_coordination_invoice_create(request):
    selected_ids = request.GET.getlist("coordination_log_ids")
    if request.method == "POST":
        selected_ids = request.POST.getlist("coordination_log_ids")
    selected_coordination_logs = []
    selected_error = ""
    active_selected_ids = selected_ids
    selected_invoice_groups = []

    if selected_ids:
        selected_coordination_logs, selected_error = (
            get_selected_billable_coordination_logs(
                selected_ids,
                require_single_participant=request.method == "POST",
            )
        )

    if (
        request.method == "GET"
        and selected_coordination_logs
        and len({log.participant_id for log in selected_coordination_logs}) == 1
    ):
        form = SupportCoordinationInvoiceCreateForm(
            initial=build_support_coordination_invoice_form_data(
                selected_coordination_logs
            )
        )
    elif request.method == "POST":
        form = SupportCoordinationInvoiceCreateForm(request.POST)
    elif request.method == "GET" and selected_coordination_logs:
        form = SupportCoordinationInvoiceCreateForm()
    else:
        form = SupportCoordinationInvoiceCreateForm(request.GET or None)

    coordination_logs = CoordinationLog.objects.none()
    if selected_error:
        active_selected_ids = []
        if request.method == "GET" and form.is_valid():
            selected_error = ""
            coordination_logs = get_billable_coordination_logs(
                form.cleaned_data["participant"],
                form.cleaned_data["period_start"],
                form.cleaned_data["period_end"],
            )
    elif selected_coordination_logs:
        coordination_logs = selected_coordination_logs
        if request.method == "GET":
            selected_invoice_groups = build_selected_coordination_invoice_groups(
                selected_coordination_logs
            )
    elif form.is_valid():
        coordination_logs = get_billable_coordination_logs(
            form.cleaned_data["participant"],
            form.cleaned_data["period_start"],
            form.cleaned_data["period_end"],
        )

    if request.method == "POST":
        if selected_error:
            coordination_logs = CoordinationLog.objects.none()
        elif form.is_valid():
            if selected_coordination_logs:
                coordination_logs = selected_coordination_logs
            else:
                coordination_logs = get_billable_coordination_logs(
                    form.cleaned_data["participant"],
                    form.cleaned_data["period_start"],
                    form.cleaned_data["period_end"],
                )
            coordination_logs = [
                coordination_log
                for coordination_log in coordination_logs
                if coordination_log.participant_id == form.cleaned_data["participant"].id
                and form.cleaned_data["period_start"]
                <= coordination_log.service_date
                <= form.cleaned_data["period_end"]
            ]
            if selected_coordination_logs and len(coordination_logs) != len(
                selected_coordination_logs
            ):
                selected_error = (
                    "Selected coordination logs do not match the invoice participant "
                    "and period."
                )
                coordination_logs = CoordinationLog.objects.none()
            elif not coordination_logs:
                messages.error(
                    request,
                    "No approved coordination logs found for this invoice.",
                )
            else:
                with transaction.atomic():
                    invoice = Invoice.objects.create(
                        participant=form.cleaned_data["participant"],
                        period_start=form.cleaned_data["period_start"],
                        period_end=form.cleaned_data["period_end"],
                        invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION,
                        created_by=request.user,
                    )
                    for coordination_log in coordination_logs:
                        InvoiceLine.objects.create_from_coordination_log(
                            invoice=invoice,
                            coordination_log=coordination_log,
                            support_item=form.cleaned_data["support_item"],
                        )
                        coordination_log.status = CoordinationLog.Status.INVOICED
                        coordination_log.save(update_fields=["status", "updated_at"])
                audit_action = (
                    AuditLog.Action.SUPPORT_COORDINATION_INVOICE_CREATED
                    if hasattr(
                        AuditLog.Action,
                        "SUPPORT_COORDINATION_INVOICE_CREATED",
                    )
                    else AuditLog.Action.INVOICE_CREATED
                )
                write_audit_log(
                    request.user,
                    audit_action,
                    invoice,
                    f"Created invoice {invoice.invoice_number}.",
                )
                messages.success(request, "Support coordination invoice created.")
                return redirect(invoice)

    invoice_rows = build_coordination_invoice_rows(coordination_logs)
    if coordination_logs and not selected_error:
        active_selected_ids = active_selected_ids or [
            coordination_log.id for coordination_log in coordination_logs
        ]

    return render(
        request,
        "invoices/support_coordination_invoice_form.html",
        {
            "form": form,
            "coordination_logs": coordination_logs,
            "invoice_rows": invoice_rows,
            "selected_invoice_groups": selected_invoice_groups,
            "selected_error": selected_error,
            "selected_coordination_log_ids": active_selected_ids,
        },
    )


@finance_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related("participant", "created_by").prefetch_related(
            Prefetch(
                "lines",
                queryset=InvoiceLine.objects.select_related(
                    "service_log",
                    "coordination_log",
                ),
            ),
        ),
        id=invoice_id,
    )
    return render(
        request,
        "invoices/invoice_detail.html",
        {
            "invoice": invoice,
            "return_url": get_safe_return_url(request, reverse("invoice_placeholder")),
        },
    )


@admin_required
def invoice_settings(request):
    settings_obj = InvoiceSettings.load()
    if request.method == "POST":
        form = InvoiceSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Invoice settings updated.")
            return redirect("invoice_settings")
    else:
        form = InvoiceSettingsForm(instance=settings_obj)

    return render(
        request,
        "invoices/invoice_settings.html",
        {
            "form": form,
            "settings": settings_obj,
        },
    )


def get_invoice(invoice_id):
    return get_object_or_404(
        Invoice.objects.select_related("participant", "created_by").prefetch_related(
            Prefetch(
                "lines",
                queryset=InvoiceLine.objects.select_related(
                    "service_log",
                    "coordination_log",
                ),
            ),
        ),
        id=invoice_id,
    )


def release_invoice_service_logs(invoice):
    service_logs = {
        line.service_log_id: line.service_log
        for line in invoice.lines.select_related("service_log")
    }
    for service_log in service_logs.values():
        service_log.status = ServiceLog.Status.APPROVED
        service_log.save(update_fields=["status", "updated_at"])
    invoice.lines.all().delete()


@finance_required
def invoice_csv(request, invoice_id):
    invoice = get_invoice(invoice_id)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "invoice_number",
            "participant",
            "period_start",
            "period_end",
            "status",
            "support_item_number",
            "description",
            "unit",
            "quantity",
            "unit_price",
            "gst_code",
            "line_total",
            "invoice_type",
            "source_date",
        ]
    )
    for line in invoice.lines.select_related("service_log", "coordination_log"):
        writer.writerow(
            [
                invoice.invoice_number,
                invoice.participant.display_name,
                format_au_date(invoice.period_start),
                format_au_date(invoice.period_end),
                invoice.status,
                line.support_item_number,
                line.description,
                line.unit,
                f"{line.quantity:.2f}",
                f"{line.unit_price:.2f}",
                line.gst_code,
                f"{line.line_total:.2f}",
                invoice.invoice_type,
                invoice_line_source_date(line),
            ]
        )
    response = HttpResponse(output.getvalue(), content_type="text/csv")
    filename = (
        invoice_download_filename(invoice, "csv")
        if invoice.invoice_type == Invoice.InvoiceType.SUPPORT_COORDINATION
        else f"{invoice.invoice_number}.csv"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )
    return response


def escape_pdf_text(value):
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf_page_stream(lines):
    operations = []
    images = []
    y = 760
    for index, line in enumerate(lines):
        if isinstance(line, dict):
            if line.get("image"):
                image_name = f"Im{len(images) + 1}"
                images.append((image_name, line))
                operations.extend(
                    [
                        "q",
                        f"{line['width']} 0 0 {line['height']} {line['x']} {line['y']} cm",
                        f"/{image_name} Do",
                        "Q",
                    ]
                )
                continue
            if line.get("line"):
                color = line.get("color", (0, 0, 0))
                width = line.get("width", 1)
                operations.extend(
                    [
                        f"{color[0]} {color[1]} {color[2]} RG",
                        f"{width} w",
                        f"{line['x1']} {line['y1']} m",
                        f"{line['x2']} {line['y2']} l",
                        "S",
                    ]
                )
                continue
            text = line.get("text", "")
            x = line.get("x", 50)
            font_size = line.get("font_size", 12)
            font = line.get("font", "F1")
            y = line.get("y", y if not index else y - 18)
        else:
            text = line
            x = 50
            font_size = 12
            font = "F1"
            if index:
                y -= 18
        operations.extend(
            [
                "BT",
                f"/{font} {font_size} Tf",
                f"{x} {y} Td",
                f"({escape_pdf_text(text)}) Tj",
                "ET",
            ]
        )
    return "\n".join(operations).encode("latin-1", errors="replace"), images


def build_simple_pdf(lines_or_pages):
    if lines_or_pages and isinstance(lines_or_pages[0], list):
        pages = lines_or_pages
    else:
        pages = [lines_or_pages]

    page_payloads = [build_pdf_page_stream(lines) for lines in pages]
    next_object_number = 5
    page_records = []
    for stream, images in page_payloads:
        page_object_number = next_object_number
        content_object_number = page_object_number + 1
        image_object_numbers = list(
            range(content_object_number + 1, content_object_number + 1 + len(images))
        )
        page_records.append(
            {
                "page_object_number": page_object_number,
                "content_object_number": content_object_number,
                "image_object_numbers": image_object_numbers,
                "stream": stream,
                "images": images,
            }
        )
        next_object_number = content_object_number + 1 + len(images)

    page_kids = " ".join(
        f"{record['page_object_number']} 0 R" for record in page_records
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{page_kids}] /Count {len(page_records)} >>".encode(
            "ascii"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]

    for record in page_records:
        image_resources = ""
        if record["images"]:
            image_resources = " /XObject << " + " ".join(
                f"/{name} {object_number} 0 R"
                for (name, _), object_number in zip(
                    record["images"],
                    record["image_object_numbers"],
                )
            ) + " >>"
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            + (
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >>{image_resources} >> "
                f"/Contents {record['content_object_number']} 0 R >>"
            ).encode("ascii")
        )
        stream = record["stream"]
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
        for _, image in record["images"]:
            image_data = image["data"]
            objects.append(
                (
                    f"<< /Type /XObject /Subtype /Image /Width {image['pixel_width']} "
                    f"/Height {image['pixel_height']} /ColorSpace /DeviceRGB "
                    f"/BitsPerComponent 8 /Filter /FlateDecode /Length {len(image_data)} >>\n"
                ).encode("ascii")
                + b"stream\n"
                + image_data
                + b"\nendstream"
            )
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def format_money(value):
    return f"{value:.2f}"


def append_if_present(lines, label, value):
    value = (value or "").strip()
    if value:
        lines.append(f"{label}: {value}")


def append_multiline_if_present(lines, value):
    value = (value or "").strip()
    if value:
        lines.extend(line for line in value.splitlines() if line.strip())


def pdf_text(text, x, y, font_size=10, font="F1"):
    return {"text": text, "x": x, "y": y, "font_size": font_size, "font": font}


def estimate_text_width(text, font_size):
    return len(str(text)) * font_size * 0.48


def pdf_right_text(text, right_x, y, font_size=10, font="F1"):
    return pdf_text(text, right_x - estimate_text_width(text, font_size), y, font_size, font)


def wrap_pdf_text(text, max_width, font_size):
    words = str(text).split()
    if not words:
        return [""]

    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if estimate_text_width(candidate, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def invoice_line_source_date(line):
    if line.service_log_id:
        return format_au_date(line.service_log.service_date)
    if line.coordination_log_id:
        return format_au_date(line.coordination_log.service_date)
    return "-"


def pdf_line(x1, y1, x2, y2, width=1.5, color=(0.435, 0.173, 0.502)):
    return {
        "line": True,
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "width": width,
        "color": color,
    }


def pdf_image(image, x, y, width, height):
    return {
        "image": True,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        **image,
    }


def load_pdf_image(path):
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            return {
                "data": zlib.compress(image.tobytes()),
                "pixel_width": image.width,
                "pixel_height": image.height,
            }
    except (OSError, ValueError):
        return None


def format_invoice_date(value):
    local_date = timezone.localtime(value).date()
    return f"{local_date.day} / {local_date.month} / {local_date.year}"


def participant_address(participant):
    parts = [
        participant.address_line_1,
        participant.address_line_2,
        " ".join(
            part
            for part in [participant.suburb, participant.state, participant.postcode]
            if part
        ),
    ]
    return ", ".join(part for part in parts if part)


def next_invoice_section_y(line_groups, section_top, row_start_gap=52, row_gap=13, after_gap=58):
    longest_group = max((len(group) for group in line_groups), default=0)
    if not longest_group:
        return section_top - row_start_gap - after_gap
    last_line_y = section_top - row_start_gap - ((longest_group - 1) * row_gap)
    return last_line_y - after_gap


def invoice_line_row_height(description_lines):
    return max(30, 20 + (len(description_lines) * 10))


def append_invoice_table_header(
    page_lines,
    heading_y,
    page_left,
    page_right,
    item_col_x,
    description_col_x,
    qty_col_right,
    rate_col_right,
    amount_col_right,
    heading="Line Items",
):
    page_lines.extend(
        [
            pdf_text(heading, page_left, heading_y, 10, "F2"),
            pdf_line(
                page_left,
                heading_y - 14,
                page_right,
                heading_y - 14,
                width=0.75,
                color=(0.82, 0.84, 0.88),
            ),
            pdf_text("Date", item_col_x, heading_y - 28, 8.5, "F2"),
            pdf_text("Description", description_col_x, heading_y - 28, 8.5, "F2"),
            pdf_right_text("Qty", qty_col_right, heading_y - 28, 8.5, "F2"),
            pdf_right_text("Rate", rate_col_right, heading_y - 28, 8.5, "F2"),
            pdf_right_text("Amount", amount_col_right, heading_y - 28, 8.5, "F2"),
            pdf_line(
                page_left,
                heading_y - 38,
                page_right,
                heading_y - 38,
                width=0.75,
                color=(0.82, 0.84, 0.88),
            ),
        ]
    )
    return heading_y - 56


def invoice_footer_minimum_top(payment_detail_rows, page_bottom=40):
    if not payment_detail_rows:
        return page_bottom
    payment_rows_height = 28 + ((len(payment_detail_rows) - 1) * 14)
    return page_bottom + 50 + payment_rows_height


@finance_required
def invoice_pdf(request, invoice_id):
    invoice = get_invoice(invoice_id)
    settings_obj = InvoiceSettings.load()
    business_lines = []
    append_if_present(business_lines, "ABN", settings_obj.abn)
    append_if_present(business_lines, "Phone", settings_obj.phone)
    append_if_present(business_lines, "Email", settings_obj.email)
    append_multiline_if_present(business_lines, settings_obj.address)

    participant = invoice.participant
    invoice_date = format_invoice_date(invoice.created_at)
    participant_lines = [f"Name: {participant.display_name}"]
    append_if_present(participant_lines, "NDIS NUMBER", participant.ndis_number)
    append_if_present(participant_lines, "Phone", participant.phone)
    append_if_present(participant_lines, "Email", participant.email)
    append_if_present(participant_lines, "Address", participant_address(participant))

    sent_to_lines = []
    append_if_present(sent_to_lines, "Name", participant.plan_manager_name)
    append_if_present(sent_to_lines, "Phone", participant.plan_manager_phone)
    append_if_present(sent_to_lines, "Email", participant.plan_manager_email)

    page_left = 32
    page_right = 580
    logo_area_width = 58
    logo_text_x = page_left + logo_area_width + 12
    header_y = 742
    invoice_detail_y = 738
    divider_y = 684
    detail_line_gap = 13
    business_info_y = 646
    participant_section_top = 568
    invoice_detail_x = 448
    sent_to_x = 332
    logo_width = 208
    logo_height = 43
    logo_y = header_y - 25
    item_col_x = page_left
    description_col_x = 138
    qty_col_right = 382
    rate_col_right = 454
    amount_col_right = page_right
    description_col_width = min(qty_col_right - description_col_x - 18, 200)
    logo_path = settings.BASE_DIR / INVOICE_STATIC_LOGO_PATH
    logo_image = load_pdf_image(logo_path)
    pdf_lines = [
        pdf_text("TAX INVOICE", invoice_detail_x, invoice_detail_y, 10.5, "F2"),
        pdf_text(f"Invoice No.: # {invoice.invoice_number}", invoice_detail_x, invoice_detail_y - detail_line_gap, 8.5),
        pdf_text(f"Invoice Date: {invoice_date}", invoice_detail_x, invoice_detail_y - (detail_line_gap * 2), 8.5),
        pdf_text(
            f"Invoice Type: {invoice.get_invoice_type_display()}",
            invoice_detail_x,
            invoice_detail_y - (detail_line_gap * 3),
            8.5,
        ),
        pdf_line(page_left, divider_y, page_right, divider_y, width=3),
    ]
    if logo_image:
        pdf_lines.insert(0, pdf_image(logo_image, page_left, logo_y, logo_width, logo_height))
    else:
        pdf_lines = [
            pdf_line(page_left, header_y - 3, page_left + logo_area_width, header_y - 3, width=0.75),
            pdf_text(settings_obj.business_name, logo_text_x, header_y - 1, 14, "F2"),
            pdf_text("Honouring Your Choices, Brightening Your World.", logo_text_x, header_y - 19, 6.3),
            *pdf_lines,
        ]
    y = business_info_y
    if settings_obj.business_name:
        pdf_lines.append(pdf_text(settings_obj.business_name, page_left, y, 10, "F2"))
        y -= 16
    for business_line in business_lines:
        font = "F2" if business_line.startswith("ABN:") else "F1"
        pdf_lines.append(pdf_text(business_line, page_left, y, 9.5, font))
        y -= 14

    pdf_lines.extend(
        [
            pdf_line(page_left, participant_section_top, 278, participant_section_top, width=2),
            pdf_line(sent_to_x, participant_section_top, page_right, participant_section_top, width=2),
            pdf_text("PARTICIPANT INFORMATION", page_left, participant_section_top - 30, 10, "F2"),
            pdf_text("SENT TO", sent_to_x, participant_section_top - 30, 10, "F2"),
        ]
    )
    y = participant_section_top - 52
    for participant_line in participant_lines:
        pdf_lines.append(pdf_text(participant_line, page_left, y, 9))
        y -= 13
    y = participant_section_top - 52
    for sent_to_line in sent_to_lines:
        pdf_lines.append(pdf_text(sent_to_line, sent_to_x, y, 9))
        y -= 13

    line_items_top = next_invoice_section_y(
        [participant_lines, sent_to_lines],
        participant_section_top,
    )
    pdf_lines.append(
        pdf_text(
            f"Period: {format_au_date(invoice.period_start)} to {format_au_date(invoice.period_end)}",
            page_left,
            line_items_top,
            8,
        )
    )
    y = append_invoice_table_header(
        pdf_lines,
        line_items_top - 20,
        page_left,
        page_right,
        item_col_x,
        description_col_x,
        qty_col_right,
        rate_col_right,
        amount_col_right,
    )
    pdf_pages = [pdf_lines]
    payment_detail_rows = [
        ("Bank", settings_obj.bank_name),
        ("Account name", settings_obj.account_name),
        ("BSB", settings_obj.bsb),
        ("Account number", settings_obj.account_number),
    ]
    payment_detail_rows = [
        (label, (value or "").strip())
        for label, value in payment_detail_rows
        if (value or "").strip()
    ]
    footer_minimum_top = invoice_footer_minimum_top(payment_detail_rows)
    invoice_lines = list(invoice.lines.select_related("service_log", "coordination_log"))
    for line_index, line in enumerate(invoice_lines):
        description_lines = wrap_pdf_text(
            line.description,
            description_col_width,
            7.5,
        )
        row_height = invoice_line_row_height(description_lines)
        is_final_line = line_index == len(invoice_lines) - 1
        required_bottom = footer_minimum_top + 10 if is_final_line else 40
        if y - row_height < required_bottom:
            pdf_lines = [
                pdf_text("TAX INVOICE", page_left, 748, 10.5, "F2"),
                pdf_text(
                    f"Invoice No.: # {invoice.invoice_number}",
                    page_left,
                    732,
                    8.5,
                ),
                pdf_right_text("Continued", page_right, 748, 8.5, "F2"),
                pdf_right_text(participant.display_name, page_right, 732, 8.5),
                pdf_line(page_left, 714, page_right, 714, width=3),
            ]
            pdf_pages.append(pdf_lines)
            y = append_invoice_table_header(
                pdf_lines,
                684,
                page_left,
                page_right,
                item_col_x,
                description_col_x,
                qty_col_right,
                rate_col_right,
                amount_col_right,
                heading="Line Items (continued)",
            )
        code_y = y - (len(description_lines) * 10)
        pdf_lines.extend(
            [
                pdf_text(invoice_line_source_date(line), item_col_x, y, 7.5),
                pdf_right_text(f"{line.quantity:.2f}", qty_col_right, y, 7.5),
                pdf_right_text(f"${format_money(line.unit_price)}", rate_col_right, y, 7.5),
                pdf_right_text(f"${format_money(line.line_total)}", amount_col_right, y, 8, "F2"),
            ]
        )
        for index, description_line in enumerate(description_lines):
            pdf_lines.append(
                pdf_text(
                    description_line,
                    description_col_x,
                    y - (index * 10),
                    7.5,
                )
            )
        pdf_lines.append(
            pdf_text(line.support_item_number, description_col_x, code_y, 6.8)
        )
        y -= row_height

    footer_top = y - 10
    total_label_x = 380
    total_amount_right = page_right
    pdf_lines.extend(
        [
            pdf_line(
                total_label_x,
                footer_top + 14,
                page_right,
                footer_top + 14,
                width=0.75,
                color=(0.82, 0.84, 0.88),
            ),
            pdf_text("Invoice Total", total_label_x, footer_top, 9, "F2"),
            pdf_right_text(
                f"${format_money(invoice.total_amount)}",
                total_amount_right,
                footer_top,
                11.5,
                "F2",
            ),
        ]
    )
    if payment_detail_rows:
        payment_details_top = footer_top - 50
        payment_label_x = page_left
        payment_value_x = page_left + 88
        pdf_lines.extend(
            [
                pdf_text("Payment Details", page_left, payment_details_top, 10, "F2"),
                pdf_line(
                    page_left,
                    payment_details_top - 10,
                    292,
                    payment_details_top - 10,
                    width=0.75,
                    color=(0.82, 0.84, 0.88),
                ),
            ]
        )
        y = payment_details_top - 28
        for label, value in payment_detail_rows:
            pdf_lines.append(pdf_text(label, payment_label_x, y, 8.5, "F2"))
            pdf_lines.append(pdf_text(value, payment_value_x, y, 8.5))
            y -= 14
    response = HttpResponse(build_simple_pdf(pdf_pages), content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{invoice_download_filename(invoice, "pdf")}"'
    )
    return response


@finance_required
@require_POST
def invoice_mark_issued(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, status=Invoice.Status.DRAFT)
    invoice.status = Invoice.Status.ISSUED
    invoice.save(update_fields=["status", "updated_at"])
    write_audit_log(
        request.user,
        AuditLog.Action.INVOICE_MARKED_ISSUED,
        invoice,
        f"Marked invoice {invoice.invoice_number} as issued.",
    )
    messages.success(request, "Invoice marked as issued.")
    return redirect(invoice)


@finance_required
@require_POST
def invoice_mark_paid(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, status=Invoice.Status.ISSUED)
    invoice.status = Invoice.Status.PAID
    invoice.save(update_fields=["status", "updated_at"])
    write_audit_log(
        request.user,
        AuditLog.Action.INVOICE_MARKED_PAID,
        invoice,
        f"Marked invoice {invoice.invoice_number} as paid.",
    )
    messages.success(request, "Invoice marked as paid.")
    return redirect(invoice)


@finance_required
@require_POST
def invoice_cancel(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.prefetch_related("lines__service_log"),
        id=invoice_id,
        status__in=[Invoice.Status.DRAFT, Invoice.Status.ISSUED],
    )
    release_invoice_service_logs(invoice)
    invoice.status = Invoice.Status.CANCELLED
    invoice.save(update_fields=["status", "updated_at"])
    write_audit_log(
        request.user,
        AuditLog.Action.INVOICE_CANCELLED,
        invoice,
        f"Cancelled invoice {invoice.invoice_number}.",
    )
    messages.success(request, "Invoice cancelled.")
    return redirect(invoice)


@finance_required
@require_POST
def invoice_delete(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.prefetch_related("lines__service_log"),
        id=invoice_id,
        status=Invoice.Status.DRAFT,
    )
    invoice_number = invoice.invoice_number
    release_invoice_service_logs(invoice)
    write_audit_log(
        request.user,
        AuditLog.Action.INVOICE_DELETED,
        invoice,
        f"Deleted draft invoice {invoice_number}.",
    )
    invoice.delete()
    messages.success(request, "Draft invoice deleted.")
    return redirect("invoice_placeholder")


@finance_required
def exports_placeholder(request):
    return render(
        request,
        "invoices/finance_placeholder.html",
        {"title": "Reports and Exports"},
    )

# Create your views here.
