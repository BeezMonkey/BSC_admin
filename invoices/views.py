from django.shortcuts import render

from accounts.decorators import finance_required


@finance_required
def invoice_placeholder(request):
    return render(request, "invoices/invoice_placeholder.html")


@finance_required
def exports_placeholder(request):
    return render(
        request,
        "invoices/finance_placeholder.html",
        {"title": "Reports and Exports"},
    )

# Create your views here.
