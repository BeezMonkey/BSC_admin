from django.urls import path

from .views import invoice_placeholder

urlpatterns = [
    path("invoices/", invoice_placeholder, name="invoice_placeholder"),
]
