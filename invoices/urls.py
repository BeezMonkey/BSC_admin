from django.urls import path

from .views import exports_placeholder, invoice_create, invoice_detail, invoice_list

urlpatterns = [
    path("invoices/", invoice_list, name="invoice_placeholder"),
    path("invoices/new/", invoice_create, name="invoice_create"),
    path("invoices/<int:invoice_id>/", invoice_detail, name="invoice_detail"),
    path("exports/", exports_placeholder, name="exports_placeholder"),
]
