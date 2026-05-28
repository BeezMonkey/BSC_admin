from django.shortcuts import render

from accounts.decorators import role_required


@role_required("super_admin", "admin", "accountant")
def invoice_placeholder(request):
    return render(request, "invoices/invoice_placeholder.html")

# Create your views here.
