from accounts.decorators import admin_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .workbench_forms import WeeklyBillingPeriodForm
from .workbench_queries import build_weekly_workbench


@admin_required
@require_GET
def weekly_billing(request):
    form = WeeklyBillingPeriodForm(request.GET)
    period = None
    workbench = None
    if form.is_valid():
        period = form.period
        workbench = build_weekly_workbench(period['start'], period['end'])
    return render(request, 'invoices/weekly_billing.html', {
        'period_form': form, 'period': period, 'workbench': workbench,
    })
