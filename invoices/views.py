import csv
from decimal import Decimal
from io import StringIO

from django.contrib import messages
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from accounts.decorators import admin_required
from accounts.decorators import finance_required
from core.audit import write_audit_log
from core.models import AuditLog
from core.navigation import get_safe_return_url
from core.pagination import paginate_queryset
from core.sorting import apply_sorting
from service_logs.models import ServiceLog

from .forms import InvoiceCreateForm, InvoiceSettingsForm
from .models import Invoice, InvoiceLine, InvoiceSettings


def format_filter_date(value):
    parsed_date = parse_date(value)
    if not parsed_date:
        return value
    return parsed_date.strftime("%d/%m/%Y")


def format_au_date(value):
    return value.strftime("%d/%m/%Y")


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
            ]
        )
    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="{invoice.invoice_number}.csv"'
    )
    return response


def escape_pdf_text(value):
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_simple_pdf(lines):
    operations = []
    y = 760
    for index, line in enumerate(lines):
        if isinstance(line, dict):
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
    stream = "\n".join(operations).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
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
    divider_y = 684
    detail_line_gap = 13
    business_info_y = 642
    participant_section_top = 568
    invoice_detail_x = 442
    sent_to_x = 332
    item_col_x = page_left
    description_col_x = 138
    qty_col_right = 382
    rate_col_right = 454
    amount_col_right = page_right
    pdf_lines = [
        pdf_line(page_left, header_y - 3, page_left + logo_area_width, header_y - 3, width=0.75),
        pdf_text(settings_obj.business_name, logo_text_x, header_y - 1, 14, "F2"),
        pdf_text("Honouring Your Choices, Brightening Your World.", logo_text_x, header_y - 19, 6.3),
        pdf_text("TAX INVOICE", invoice_detail_x, header_y, 10.5, "F2"),
        pdf_text(f"Invoice No.: # {invoice.invoice_number}", invoice_detail_x, header_y - detail_line_gap, 8.5),
        pdf_text(f"Invoice Date: {invoice_date}", invoice_detail_x, header_y - (detail_line_gap * 2), 8.5),
        pdf_line(page_left, divider_y, page_right, divider_y, width=3),
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
    pdf_lines.extend(
        [
            pdf_text(
                f"Period: {format_au_date(invoice.period_start)} to {format_au_date(invoice.period_end)}",
                page_left,
                line_items_top,
                8,
            ),
            pdf_text("Line Items", page_left, line_items_top - 20, 10, "F2"),
            pdf_line(
                page_left,
                line_items_top - 34,
                page_right,
                line_items_top - 34,
                width=0.75,
                color=(0.82, 0.84, 0.88),
            ),
            pdf_text("Item", item_col_x, line_items_top - 48, 8.5, "F2"),
            pdf_text("Description", description_col_x, line_items_top - 48, 8.5, "F2"),
            pdf_right_text("Qty", qty_col_right, line_items_top - 48, 8.5, "F2"),
            pdf_right_text("Rate", rate_col_right, line_items_top - 48, 8.5, "F2"),
            pdf_right_text("Amount", amount_col_right, line_items_top - 48, 8.5, "F2"),
            pdf_line(
                page_left,
                line_items_top - 58,
                page_right,
                line_items_top - 58,
                width=0.75,
                color=(0.82, 0.84, 0.88),
            ),
        ]
    )
    y = line_items_top - 76
    for line in invoice.lines.all():
        pdf_lines.extend(
            [
                pdf_text(line.support_item_number, item_col_x, y, 7.5),
                pdf_text(line.description[:44], description_col_x, y, 7.5),
                pdf_right_text(f"{line.quantity:.2f}", qty_col_right, y, 7.5),
                pdf_right_text(f"${format_money(line.unit_price)}", rate_col_right, y, 7.5),
                pdf_right_text(f"${format_money(line.line_total)}", amount_col_right, y, 8, "F2"),
            ]
        )
        y -= 22

    total_y = max(y - 10, 126)
    pdf_lines.extend(
        [
            pdf_line(
                380,
                total_y + 14,
                page_right,
                total_y + 14,
                width=0.75,
                color=(0.82, 0.84, 0.88),
            ),
            pdf_text("Invoice Total", 380, total_y, 9, "F2"),
            pdf_right_text(f"${format_money(invoice.total_amount)}", amount_col_right, total_y, 10, "F2"),
        ]
    )
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
    if payment_detail_rows:
        payment_details_top = max(y - 52, 54)
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
