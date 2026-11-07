from datetime import date, time
from decimal import Decimal

from django.test import TestCase

from accounts.models import UserProfile
from invoices import tests_invoices as fixtures
from invoices.models import Invoice, InvoiceBillingAdjustment, InvoiceLine
from scheduling.models import SupportItem
from service_logs.models import ServiceLog
from invoices import tests_weekly_billing as weekly_fixtures
from scheduling.models import ParticipantCancellation


class WeeklyBillingActionTests(TestCase):
    setUp = fixtures.InvoiceGenerationTests.setUp
    create_user_with_role = fixtures.InvoiceGenerationTests.create_user_with_role
    create_service_log = fixtures.InvoiceGenerationTests.create_service_log
    create_travel_support_item = fixtures.InvoiceGenerationTests.create_travel_support_item
    create_shift = weekly_fixtures.WeeklyBillingTests.create_shift
    cancellation = weekly_fixtures.WeeklyBillingTests.cancellation

    def post(self, action, **data):
        self.client.force_login(self.admin_user)
        return self.client.post('/billing/weekly/', {
            'period': 'custom', 'start': '2026-06-01', 'end': '2026-06-07',
            'action': action, 'participant_id': self.participant.pk, **data,
        })

    def preview(self, **data):
        response = self.post('preview', **data)
        self.assertEqual(response.status_code, 200)
        return response.context['billing_preview']

    def create(self, preview, mode='workbench', **data):
        return self.post('create', preview_token=preview['tokens'][mode], period_mode=mode, **data)

    def test_preview_post_is_read_only_and_contains_explicit_signed_sources(self):
        log = self.create_service_log(kilometres=Decimal('8'))
        preview = self.preview()
        self.assertEqual([r['service_log'].pk for r in preview['rows']], [log.pk])
        self.assertEqual(preview['actual_start'], date(2026, 6, 1))
        self.assertEqual(set(preview['tokens']), {'workbench', 'actual'})
        self.assertFalse(Invoice.objects.exists())
        self.assertContains(self.post('preview'), f'name="travel-{log.pk}-amount"', count=1)

    def test_create_defaults_to_workbench_and_retry_recovers_same_result(self):
        self.create_service_log()
        preview = self.preview()
        first = self.create(preview)
        self.assertEqual(first.status_code, 200)
        invoice = Invoice.objects.get()
        self.assertEqual((invoice.period_start, invoice.period_end), (date(2026, 6, 1), date(2026, 6, 7)))
        self.assertEqual(self.create(preview).status_code, 200)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(invoice.status, Invoice.Status.DRAFT)

    def test_actual_mode_changes_saved_period_only(self):
        self.create_service_log(service_date=date(2026, 6, 3))
        self.assertEqual(self.create(self.preview(), 'actual').status_code, 200)
        invoice = Invoice.objects.get()
        self.assertEqual((invoice.period_start, invoice.period_end), (date(2026, 6, 3), date(2026, 6, 3)))
        self.assertEqual(invoice.total_amount, Decimal('130.94'))

    def test_correct_time_item_and_km_use_existing_history_and_manual_claim(self):
        log = self.create_service_log(kilometres=Decimal('8'))
        travel = self.create_travel_support_item()
        travel.price_limit = Decimal('1.25')
        travel.save()
        item = SupportItem.objects.create(item_number='WB-TEST-HOURLY', name='WB test hourly',
            unit=SupportItem.Unit.HOUR, price_limit=Decimal('73.21'), is_active=True)
        preview = self.preview()
        fields = {f'adjustment-{log.pk}-{key}': value for key, value in {
            'correct_time': 'on', 'actual_start_time': '09:01', 'actual_end_time': '11:31',
            'break_minutes': '0', 'source_version': log.updated_at.isoformat(),
            'support_item': item.pk, 'kilometres': '12', 'reason': 'multiple',
        }.items()}
        response = self.create(preview, **fields, **{f'travel-{log.pk}-amount': '15.50'})
        self.assertEqual(response.status_code, 200)
        log.refresh_from_db()
        self.assertEqual(log.actual_start_time, time(9, 1))
        self.assertEqual(log.actual_hours, Decimal('2.50'))
        self.assertEqual(log.kilometres, Decimal('8'))
        self.assertEqual(log.support_item_id, self.support_item.pk)
        self.assertEqual(InvoiceBillingAdjustment.objects.get().billing_values['kilometres'], '12')
        self.assertEqual(InvoiceLine.objects.get(line_type='travel_non_labour').line_total, Decimal('19.38'))

    def test_invalid_claim_keeps_inputs_and_does_not_create(self):
        log = self.create_service_log()
        response = self.create(self.preview(), **{f'travel-{log.pk}-amount': '12.34'})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, '12.34', status_code=400)
        self.assertFalse(Invoice.objects.exists())

    def test_newly_approved_source_requires_explicit_refresh(self):
        self.create_service_log()
        preview = self.preview()
        self.create_service_log(service_date=date(2026, 6, 2))
        self.assertEqual(self.create(preview).status_code, 409)
        self.assertFalse(Invoice.objects.exists())

    def test_changed_log_or_catalog_rate_requires_refresh(self):
        log = self.create_service_log()
        preview = self.preview()
        log.worker_notes = 'Updated evidence'
        log.save()
        self.assertEqual(self.create(preview).status_code, 409)
        preview = self.preview()
        self.support_item.price_limit += Decimal('1')
        self.support_item.save()
        self.assertEqual(self.create(preview).status_code, 409)
        self.assertFalse(Invoice.objects.exists())

    def test_inactive_original_item_price_is_still_part_of_signed_preview(self):
        self.create_service_log()
        self.support_item.is_active = False
        self.support_item.save()
        preview = self.preview()
        self.support_item.price_limit += Decimal('1')
        self.support_item.save()
        self.assertEqual(self.create(preview).status_code, 409)
        self.assertFalse(Invoice.objects.exists())

    def test_source_removed_between_scope_lookup_and_lock_returns_conflict(self):
        from unittest.mock import patch
        from django.db.models.query import QuerySet
        log = self.create_service_log(status=ServiceLog.Status.SUBMITTED)
        original_get = QuerySet.get
        def disappearing_source(queryset, *args, **kwargs):
            if queryset.model is ServiceLog and queryset.query.select_for_update:
                raise ServiceLog.DoesNotExist()
            return original_get(queryset, *args, **kwargs)
        with patch.object(QuerySet, 'get', autospec=True, side_effect=disappearing_source):
            self.assertEqual(self.post('approve', source_id=log.pk).status_code, 409)

    def test_signed_scope_rejects_tampered_participant_period_mode_or_token(self):
        self.create_service_log()
        preview = self.preview()
        for data in ({'participant_id': self.other_participant.pk}, {'end': '2026-06-08'},
                     {'period_mode': 'actual'}, {'preview_token': preview['tokens']['workbench'] + 'x'}):
            payload = dict(preview_token=preview['tokens']['workbench'], period_mode='workbench')
            payload.update(data)
            self.assertEqual(self.post('create', **payload).status_code, 409)
        self.assertFalse(Invoice.objects.exists())

    def test_review_is_same_period_and_duplicate_is_conflict(self):
        log = self.create_service_log(status=ServiceLog.Status.SUBMITTED)
        self.assertEqual(self.post('approve', source_id=log.pk).status_code, 200)
        log.refresh_from_db()
        self.assertEqual(log.status, ServiceLog.Status.APPROVED)
        self.assertEqual(self.post('approve', source_id=log.pk).status_code, 409)
        outside = self.create_service_log(status=ServiceLog.Status.SUBMITTED, service_date=date(2026, 5, 31))
        self.assertEqual(self.post('approve', source_id=outside.pk).status_code, 400)
        outside.refresh_from_db()
        self.assertEqual(outside.status, ServiceLog.Status.SUBMITTED)

    def test_non_admin_post_and_csrf_are_rejected(self):
        from django.test import Client
        self.client.force_login(self.accountant_user)
        self.assertEqual(self.client.post('/billing/weekly/', {'action': 'preview'}).status_code, 403)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin_user)
        self.assertEqual(client.post('/billing/weekly/', {'action': 'preview'}).status_code, 403)

    def test_return_reason_required_then_preserved_in_review(self):
        log = self.create_service_log(status=ServiceLog.Status.SUBMITTED)
        self.assertEqual(self.post('return', source_id=log.pk).status_code, 400)
        self.assertEqual(self.post('return', source_id=log.pk, reason='Check appointment time').status_code, 200)
        log.refresh_from_db()
        self.assertEqual(log.rejection_reason, 'Check appointment time')

    def test_cancellation_decisions_and_rejection_restore_missing_log(self):
        for decision, state in [('approve', 'approved'), ('waive', 'waived'), ('reject', 'rejected')]:
            cancellation = self.cancellation(ParticipantCancellation.Status.PENDING)
            if decision == 'reject':
                self.assertEqual(self.post('cancel_reject', source_id=cancellation.pk).status_code, 400)
            response = self.post('cancel_' + decision, source_id=cancellation.pk,
                                 admin_note='Incorrect cancellation' if decision == 'reject' else '')
            self.assertEqual(response.status_code, 200)
            cancellation.refresh_from_db()
            self.assertEqual(cancellation.status, state)
            if decision == 'reject':
                self.assertEqual(response.context['workbench']['missing_log_count'], 1)
            self.assertEqual(self.post('cancel_' + decision, source_id=cancellation.pk).status_code,
                             400 if decision == 'reject' else 409)

    def test_approved_cancellation_can_create_draft_without_service_logs(self):
        cancellation = self.cancellation(ParticipantCancellation.Status.APPROVED)
        self.assertEqual(self.create(self.preview()).status_code, 200)
        self.assertEqual(InvoiceLine.objects.get().participant_cancellation_id, cancellation.pk)

    def test_empty_km_keeps_original_and_explicit_zero_does_not_create_travel(self):
        log = self.create_service_log(kilometres=Decimal('8'))
        preview = self.preview()
        response = self.create(preview, **{f'adjustment-{log.pk}-kilometres': ''})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(InvoiceBillingAdjustment.objects.exists())
        other = self.create_service_log(service_date=date(2026, 6, 2), kilometres=Decimal('8'))
        response = self.create(self.preview(), **{f'adjustment-{other.pk}-kilometres': '0',
                                                f'adjustment-{other.pk}-reason': 'corrected_km'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(InvoiceBillingAdjustment.objects.get().billing_values['kilometres'], '0')
        self.assertEqual(Invoice.objects.count(), 2)
        self.assertFalse(InvoiceLine.objects.filter(line_type='travel_non_labour').exists())

    def test_retry_after_lost_session_result_recovers_audit_intent(self):
        self.create_service_log()
        preview = self.preview()
        self.assertEqual(self.create(preview).status_code, 200)
        session = self.client.session
        session['weekly_billing_results'] = {}
        session.save()
        self.assertEqual(self.create(preview).status_code, 200)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_token_bound_to_user_session_and_expiration(self):
        from unittest.mock import patch
        import time as system_time
        log = self.create_service_log()
        preview = self.preview()
        other_admin = self.create_user_with_role('other-admin', UserProfile.Role.ADMIN)
        self.client.force_login(other_admin)
        response = self.client.post('/billing/weekly/', {
            'period': 'custom', 'start': '2026-06-01', 'end': '2026-06-07',
            'action': 'create', 'participant_id': log.participant_id,
            'period_mode': 'workbench', 'preview_token': preview['tokens']['workbench'],
        })
        self.assertEqual(response.status_code, 409)
        with patch('django.core.signing.time.time', return_value=system_time.time() + 9 * 60 * 60):
            self.assertEqual(self.create(preview).status_code, 409)
        self.assertFalse(Invoice.objects.exists())

    def test_json_partial_includes_consistent_counts_and_new_draft(self):
        log = self.create_service_log(status=ServiceLog.Status.SUBMITTED)
        self.client.force_login(self.admin_user)
        response = self.client.post('/billing/weekly/', {
            'period': 'custom', 'start': '2026-06-01', 'end': '2026-06-07',
            'action': 'approve', 'participant_id': self.participant.pk, 'source_id': log.pk,
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertIn('1 approved unbilled logs', response.json()['html'])
        self.assertEqual(response.json()['participant_id'], self.participant.pk)

    def test_invalid_action_ids_do_not_raise_or_mutate(self):
        self.create_service_log()
        for values in ({'participant_id': 'not-a-number'}, {'participant_id': '9' * 100},
                       {'source_id': '9' * 100}, {'source_id': '-1'}):
            self.assertEqual(self.post('approve', **values).status_code, 400)
        self.assertFalse(Invoice.objects.exists())

    def test_audit_failure_rolls_back_draft_sources_and_can_retry_same_intent(self):
        from unittest.mock import patch
        log = self.create_service_log()
        preview = self.preview()
        with patch('invoices.billing.write_audit_log', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
                self.create(preview)
        self.assertFalse(Invoice.objects.exists())
        log.refresh_from_db()
        self.assertEqual(log.status, ServiceLog.Status.APPROVED)
        self.assertEqual(self.create(preview).status_code, 200)

    def test_other_page_invoicing_requires_new_preview(self):
        from invoices.billing import create_service_invoice
        from django.http import QueryDict
        log = self.create_service_log()
        preview = self.preview()
        create_service_invoice(actor=self.admin_user, form_data={'participant': self.participant,
            'period_start': date(2026, 6, 1), 'period_end': date(2026, 6, 7)},
            logs=[log], cancellations=[], data=QueryDict(), can_adjust=True,
            travel_item_number='04_799_0125_6_1')
        self.assertEqual(self.create(preview).status_code, 409)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_deleted_draft_releases_sources_but_old_intent_cannot_recreate_it(self):
        from django.urls import reverse
        log = self.create_service_log(kilometres=Decimal('8'))
        self.create_travel_support_item()
        preview = self.preview()
        fields = {f'adjustment-{log.pk}-{key}': value for key, value in {
            'correct_time': 'on', 'actual_start_time': '09:01', 'actual_end_time': '11:31',
            'break_minutes': '0', 'source_version': log.updated_at.isoformat(), 'reason': 'incorrect_time',
        }.items()}
        self.assertEqual(self.create(preview, **fields, **{f'travel-{log.pk}-amount': '15'}).status_code, 200)
        invoice = Invoice.objects.get()
        self.assertEqual(self.client.post(reverse('invoice_delete', args=[invoice.pk])).status_code, 302)
        log.refresh_from_db()
        self.assertEqual(log.status, ServiceLog.Status.APPROVED)
        self.assertEqual(log.actual_start_time, time(9, 1))
        self.assertEqual(self.create(preview).status_code, 409)
        self.assertFalse(Invoice.objects.exists())
        self.assertEqual(self.create(self.preview()).status_code, 200)
        self.assertFalse(InvoiceLine.objects.filter(line_type='travel_non_labour').exists())
