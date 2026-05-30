from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import finance_required
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


@finance_required
def exports_placeholder(request):
    return render(
        request,
        "invoices/finance_placeholder.html",
        {"title": "Reports and Exports"},
    )

# Create your views here.
