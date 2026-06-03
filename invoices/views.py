import csv
from decimal import Decimal
from io import StringIO

from django.contrib import messages
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from accounts.decorators import finance_required
from core.audit import write_audit_log
from core.models import AuditLog
from core.navigation import get_safe_return_url
from core.pagination import paginate_queryset
from core.sorting import apply_sorting
from service_logs.models import ServiceLog

from .forms import InvoiceCreateForm
from .models import Invoice, InvoiceLine


def format_filter_date(value):
    parsed_date = parse_date(value)
    if not parsed_date:
        return value
    return f"{parsed_date.strftime('%B')} {parsed_date.day}, {parsed_date.year}"


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
        invoice_line__isnull=True,
    ).select_related("participant", "worker", "support_item")


def get_selected_billable_logs(service_log_ids):
    try:
        unique_ids = [
            int(service_log_id) for service_log_id in dict.fromkeys(service_log_ids)
        ]
    except (TypeError, ValueError):
        return [], "Selected service logs are no longer available for invoicing."
    service_logs = ServiceLog.objects.filter(
        id__in=unique_ids,
        status=ServiceLog.Status.APPROVED,
        invoice_line__isnull=True,
    ).select_related("participant", "worker", "support_item")
    service_logs = list(service_logs.order_by("service_date", "id"))
    if len(service_logs) != len(unique_ids):
        return [], "Selected service logs are no longer available for invoicing."
    participant_ids = {service_log.participant_id for service_log in service_logs}
    if len(participant_ids) > 1:
        return [], "Selected service logs must belong to one participant."
    return service_logs, ""


def build_selected_invoice_form_data(service_logs):
    return {
        "participant": service_logs[0].participant_id,
        "period_start": min(log.service_date for log in service_logs).isoformat(),
        "period_end": max(log.service_date for log in service_logs).isoformat(),
    }


@finance_required
def invoice_create(request):
    selected_ids = request.GET.getlist("service_log_ids")
    if request.method == "POST":
        selected_ids = request.POST.getlist("service_log_ids")
    selected_service_logs = []
    selected_error = ""

    if selected_ids:
        selected_service_logs, selected_error = get_selected_billable_logs(selected_ids)

    if request.method == "GET" and selected_service_logs:
        form = InvoiceCreateForm(build_selected_invoice_form_data(selected_service_logs))
        form.is_valid()
    else:
        form = InvoiceCreateForm(request.GET or None)

    service_logs = ServiceLog.objects.none()
    if selected_error:
        service_logs = ServiceLog.objects.none()
    elif selected_service_logs:
        service_logs = selected_service_logs
    elif form.is_valid():
        service_logs = get_billable_logs(
            form.cleaned_data["participant"],
            form.cleaned_data["period_start"],
            form.cleaned_data["period_end"],
        )

    if request.method == "POST":
        form = InvoiceCreateForm(request.POST)
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

    return render(
        request,
        "invoices/invoice_form.html",
        {
            "form": form,
            "service_logs": service_logs,
            "selected_error": selected_error,
            "selected_service_log_ids": selected_ids,
        },
    )


@finance_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related("participant", "created_by").prefetch_related(
            "lines",
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


def get_invoice(invoice_id):
    return get_object_or_404(
        Invoice.objects.select_related("participant", "created_by").prefetch_related(
            "lines",
        ),
        id=invoice_id,
    )


def release_invoice_service_logs(invoice):
    lines = list(invoice.lines.select_related("service_log"))
    for line in lines:
        service_log = line.service_log
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
        ]
    )
    for line in invoice.lines.all():
        writer.writerow(
            [
                invoice.invoice_number,
                invoice.participant.display_name,
                invoice.period_start.isoformat(),
                invoice.period_end.isoformat(),
                invoice.status,
                line.support_item_number,
                line.description,
                line.unit,
                f"{line.quantity:.2f}",
                f"{line.unit_price:.2f}",
                line.gst_code,
                f"{line.line_total:.2f}",
            ]
        )
    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="{invoice.invoice_number}.csv"'
    )
    return response


def build_simple_pdf(lines):
    text_lines = ["BT", "/F1 12 Tf", "50 760 Td"]
    for index, line in enumerate(lines):
        safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index:
            text_lines.append("0 -18 Td")
        text_lines.append(f"({safe_line}) Tj")
    text_lines.append("ET")
    stream = "\n".join(text_lines).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
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


@finance_required
def invoice_pdf(request, invoice_id):
    invoice = get_invoice(invoice_id)
    pdf_lines = [
        "Brisbane Star Care NDIS Invoice",
        f"Invoice: {invoice.invoice_number}",
        f"Participant: {invoice.participant.display_name}",
        f"Period: {invoice.period_start} to {invoice.period_end}",
        f"Status: {invoice.get_status_display()}",
        "",
    ]
    for line in invoice.lines.all():
        pdf_lines.append(
            f"{line.support_item_number} {line.description} "
            f"{line.quantity:.2f} x ${format_money(line.unit_price)} = "
            f"${format_money(line.line_total)}"
        )
    pdf_lines.append(f"Total: ${format_money(invoice.total_amount)}")
    response = HttpResponse(build_simple_pdf(pdf_lines), content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{invoice.invoice_number}.pdf"'
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
