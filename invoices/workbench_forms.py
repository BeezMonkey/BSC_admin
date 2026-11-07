"""Strict, bounded periods for the weekly billing workbench."""
from zoneinfo import ZoneInfo

from django import forms
from django.utils import timezone

from service_logs.filters import resolve_service_date_filter


class WeeklyBillingPeriodForm(forms.Form):
    PERIOD_CHOICES = (
        ('this_week', 'This week'), ('last_week', 'Last week'),
        ('this_fortnight', 'This fortnight'), ('last_fortnight', 'Last fortnight'),
        ('custom', 'Custom'),
    )
    period = forms.ChoiceField(choices=PERIOD_CHOICES, label='Billing period')
    start = forms.DateField(required=False, input_formats=['%Y-%m-%d'],
                           widget=forms.DateInput(attrs={'type': 'date'}), label='From')
    end = forms.DateField(required=False, input_formats=['%Y-%m-%d'],
                         widget=forms.DateInput(attrs={'type': 'date'}), label='To')

    def __init__(self, data=None, *, today=None, **kwargs):
        self.today = today or timezone.localtime(timezone.now(), ZoneInfo('Australia/Brisbane')).date()
        if data is None or not data:
            data = {'period': 'this_week'}
        super().__init__(data=data, **kwargs)
        self.period = None

    def clean(self):
        cleaned = super().clean()
        key = cleaned.get('period')
        if not key:
            return cleaned
        if key == 'custom':
            for field in ('start', 'end'):
                if not cleaned.get(field) and field not in self.errors:
                    self.add_error(field, 'Enter both dates for a custom period.')
            if self.errors:
                return cleaned
            if cleaned['start'] > cleaned['end']:
                self.add_error('end', 'The end date must be on or after the start date.')
                return cleaned
        if not self.errors:
            self.period = resolve_service_date_filter(
                key, cleaned.get('start').isoformat() if cleaned.get('start') else '',
                cleaned.get('end').isoformat() if cleaned.get('end') else '', today=self.today,
            )
        return cleaned


class WeeklyBillingActionForm(forms.Form):
    action = forms.ChoiceField(choices=[(value, value) for value in (
        'approve', 'return', 'cancel_approve', 'cancel_waive', 'cancel_reject', 'preview', 'create')])
    participant_id = forms.IntegerField(min_value=1, max_value=9223372036854775807)
    source_id = forms.IntegerField(required=False, min_value=1, max_value=9223372036854775807)

    def clean(self):
        data = super().clean()
        if data.get('action') not in ('preview', 'create', None) and not data.get('source_id'):
            self.add_error('source_id', 'Choose a source to review.')
        return data
