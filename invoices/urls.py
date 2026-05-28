from django.urls import path

from .views import exports_placeholder, invoice_placeholder

urlpatterns = [
    path("invoices/", invoice_placeholder, name="invoice_placeholder"),
    path("exports/", exports_placeholder, name="exports_placeholder"),
]
