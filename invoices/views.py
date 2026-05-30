import csv
from io import StringIO

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import finance_required
from core.audit import write_audit_log
from core.models import AuditLog
from service_logs.models import ServiceLog

from .forms import InvoiceCreateForm
from .models import Invoice, InvoiceLine


@finance_required
def invoice_list(request):
    invoices = Invoice.objects.select_related("participant", "created_by")
    return render(request, "invoices/invoice_list.html", {"invoices": invoices})


def get_billable_logs(participant, period_start, period_end):
    return ServiceLog.objects.filter(
        participant=participant,
        service_date__gte=period_start,
        service_date__lte=period_end,
        status=ServiceLog.Status.APPROVED,
        invoice_line__isnull=True,
    ).select_related("participant", "worker", "support_item")


@finance_required
def invoice_create(request):
    form = InvoiceCreateForm(request.GET or None)
    service_logs = ServiceLog.objects.none()
    if form.is_valid():
        service_logs = get_billable_logs(
            form.cleaned_data["participant"],
            form.cleaned_data["period_start"],
            form.cleaned_data["period_end"],
        )

    if request.method == "POST":
        form = InvoiceCreateForm(request.POST)
        if form.is_valid():
            service_logs = get_billable_logs(
                form.cleaned_data["participant"],
                form.cleaned_data["period_start"],
                form.cleaned_data["period_end"],
            )
            if not service_logs.exists():
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
        {"form": form, "service_logs": service_logs},
    )


@finance_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related("participant", "created_by").prefetch_related(
            "lines",
        ),
        id=invoice_id,
    )
    return render(request, "invoices/invoice_detail.html", {"invoice": invoice})


def get_invoice(invoice_id):
    return get_object_or_404(
        Invoice.objects.select_related("participant", "created_by").prefetch_related(
            "lines",
        ),
        id=invoice_id,
    )


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
            f"{line.quantity} x ${line.unit_price} = ${line.line_total}"
        )
    pdf_lines.append(f"Total: ${invoice.total_amount}")
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
        Invoice,
        id=invoice_id,
        status__in=[Invoice.Status.DRAFT, Invoice.Status.ISSUED],
    )
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
def exports_placeholder(request):
    return render(
        request,
        "invoices/finance_placeholder.html",
        {"title": "Reports and Exports"},
    )

# Create your views here.
