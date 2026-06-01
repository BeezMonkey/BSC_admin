from django.urls import path

from .views import (
    exports_placeholder,
    invoice_cancel,
    invoice_create,
    invoice_csv,
    invoice_delete,
    invoice_detail,
    invoice_list,
    invoice_mark_issued,
    invoice_mark_paid,
    invoice_pdf,
)

urlpatterns = [
    path("invoices/", invoice_list, name="invoice_placeholder"),
    path("invoices/new/", invoice_create, name="invoice_create"),
    path("invoices/<int:invoice_id>/", invoice_detail, name="invoice_detail"),
    path("invoices/<int:invoice_id>/csv/", invoice_csv, name="invoice_csv"),
    path("invoices/<int:invoice_id>/pdf/", invoice_pdf, name="invoice_pdf"),
    path("invoices/<int:invoice_id>/delete/", invoice_delete, name="invoice_delete"),
    path(
        "invoices/<int:invoice_id>/mark-issued/",
        invoice_mark_issued,
        name="invoice_mark_issued",
    ),
    path(
        "invoices/<int:invoice_id>/mark-paid/",
        invoice_mark_paid,
        name="invoice_mark_paid",
    ),
    path("invoices/<int:invoice_id>/cancel/", invoice_cancel, name="invoice_cancel"),
    path("exports/", exports_placeholder, name="exports_placeholder"),
]
