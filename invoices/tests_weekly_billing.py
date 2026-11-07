from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from core.models import AuditLog
from invoices.models import Invoice, InvoiceLine, InvoiceSettings
from invoices import tests_invoices as invoice_fixtures
from participants.models import Participant
from scheduling.models import ParticipantCancellation, Shift
from service_logs.models import ServiceLog


class WeeklyBillingTests(TestCase):
    # Reuse the established billing fixture without inheriting its test methods.
    setUp = invoice_fixtures.InvoiceGenerationTests.setUp
    create_user_with_role = invoice_fixtures.InvoiceGenerationTests.create_user_with_role
    create_service_log = invoice_fixtures.InvoiceGenerationTests.create_service_log

    def get_workbench(self, **params):
        self.client.force_login(self.admin_user)
        return self.client.get('/billing/weekly/', {
            'period': 'custom', 'start': '2026-06-01', 'end': '2026-06-07', **params,
        })

    def create_shift(self, **overrides):
        values = dict(participant=self.participant, worker=self.worker,
                      service_date=date(2026, 6, 2), start_time=time(9),
                      end_time=time(11), planned_hours=Decimal('2.00'),
                      support_item=self.support_item,
                      service_type=Shift.ServiceType.PERSONAL_CARE,
                      status=Shift.Status.PUBLISHED, created_by=self.admin_user)
        values.update(overrides)
        return Shift.objects.create(**values)

    def cancellation(self, status, **shift_overrides):
        shift = self.create_shift(**shift_overrides)
        return ParticipantCancellation.objects.create(
            shift=shift, cancellation_type=ParticipantCancellation.CancellationType.SHORT_NOTICE,
            reason=ParticipantCancellation.Reason.OTHER, details='Cancellation evidence',
            received_at=timezone.now(), previous_shift_status=Shift.Status.PUBLISHED,
            status=status, submitted_by=self.admin_user,
        )

    def make_invoice(self, log, **overrides):
        values = dict(participant=log.participant, period_start=date(2026, 1, 1),
                      period_end=date(2026, 1, 31), created_by=self.admin_user)
        values.update(overrides)
        invoice = Invoice.objects.create(**values)
        InvoiceLine.objects.create_from_service_log(invoice=invoice, service_log=log)
        return invoice

    def test_admin_get_is_available_and_named(self):
        response = self.get_workbench()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse('weekly_billing'), '/billing/weekly/')
        self.assertContains(response, 'Weekly Billing')

    def test_all_non_admin_roles_are_forbidden(self):
        for role in (UserProfile.Role.ACCOUNTANT, UserProfile.Role.SUPPORT_WORKER,
                     UserProfile.Role.SUPPORT_COORDINATOR):
            user = self.create_user_with_role('role-' + role, role)
            self.client.force_login(user)
            self.assertEqual(self.client.get('/billing/weekly/').status_code, 403)

    def test_superadmin_can_get(self):
        user = self.create_user_with_role('weekly-super', UserProfile.Role.SUPER_ADMIN)
        self.client.force_login(user)
        self.assertEqual(self.client.get('/billing/weekly/').status_code, 200)

    def test_anonymous_redirects_to_login(self):
        self.assertEqual(self.client.get('/billing/weekly/').status_code, 302)

    def test_post_is_not_allowed_and_get_creates_no_billing_or_audit_records(self):
        self.create_service_log()
        self.client.force_login(self.admin_user)
        before = (Invoice.objects.count(), InvoiceLine.objects.count(),
                  InvoiceSettings.objects.count(), AuditLog.objects.count())
        self.assertEqual(self.client.post('/billing/weekly/', {'action': 'approve'}).status_code, 405)
        self.assertEqual(self.get_workbench().status_code, 200)
        self.assertEqual(before, (Invoice.objects.count(), InvoiceLine.objects.count(),
                                 InvoiceSettings.objects.count(), AuditLog.objects.count()))
        self.assertEqual(ServiceLog.objects.get().status, ServiceLog.Status.APPROVED)

    def test_default_is_brisbane_current_monday_to_sunday(self):
        instant = datetime(2026, 6, 7, 15, 30, tzinfo=ZoneInfo('UTC'))
        self.client.force_login(self.admin_user)
        with patch('django.utils.timezone.now', return_value=instant):
            response = self.client.get('/billing/weekly/')
        self.assertEqual(response.context['period']['start'], date(2026, 6, 8))
        self.assertEqual(response.context['period']['end'], date(2026, 6, 14))

    def test_preset_boundaries_follow_existing_resolver(self):
        from invoices.workbench_forms import WeeklyBillingPeriodForm
        expected = {
            'this_week': (date(2026, 6, 1), date(2026, 6, 7)),
            'last_week': (date(2026, 5, 25), date(2026, 5, 31)),
            'this_fortnight': (date(2026, 6, 1), date(2026, 6, 14)),
            'last_fortnight': (date(2026, 5, 18), date(2026, 5, 31)),
        }
        for key, bounds in expected.items():
            form = WeeklyBillingPeriodForm({'period': key}, today=date(2026, 6, 7))
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual((form.period['start'], form.period['end']), bounds)

    def test_invalid_custom_and_unknown_period_never_fall_back_to_all_sources(self):
        self.create_service_log()
        for params in ({'start': ''}, {'end': ''}, {'start': '2026-02-30'},
                       {'start': '2026-06-08'}, {'period': 'all'}, {'period': 'discarded'}):
            response = self.get_workbench(**params)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['period_form'].errors)
            self.assertIsNone(response.context['workbench'])
            self.assertNotContains(response, 'Log for Ava Nguyen')

    def test_inclusive_single_day_and_range_boundaries(self):
        for day in (date(2026, 5, 31), date(2026, 6, 1), date(2026, 6, 7), date(2026, 6, 8)):
            self.create_service_log(service_date=day)
        response = self.get_workbench()
        self.assertEqual(len(response.context['workbench']['log_rows']), 2)
        response = self.get_workbench(end='2026-06-01')
        self.assertEqual(len(response.context['workbench']['log_rows']), 1)

    def test_missing_uses_existing_cancellation_exclusions_and_statuses(self):
        self.create_shift()
        self.create_shift(status=Shift.Status.CONFIRMED)
        self.create_shift(status=Shift.Status.DRAFT)
        self.create_shift(status=Shift.Status.COMPLETED)
        self.create_shift(source=Shift.Source.UNSCHEDULED)
        for status in ParticipantCancellation.Status.values:
            self.cancellation(status)
        response = self.get_workbench()
        # Published + confirmed + cancellation rejected; pending/approved/waived excluded.
        self.assertEqual(response.context['workbench']['missing_log_count'], 3)

    def test_only_ended_roster_is_missing_and_future_is_upcoming(self):
        today = timezone.localdate()
        self.create_shift(service_date=today - timedelta(days=1))
        self.create_shift(service_date=today + timedelta(days=1))
        response = self.get_workbench(start=(today - timedelta(days=1)).isoformat(),
                                      end=(today + timedelta(days=1)).isoformat())
        workbench = response.context['workbench']
        self.assertEqual(workbench['missing_log_count'], 1)
        self.assertEqual(sum(row['status'] == 'Upcoming' for row in workbench['roster_rows']), 1)

    def test_unscheduled_log_is_shown_by_log_service_date_and_never_invents_missing(self):
        log = self.create_service_log(status=ServiceLog.Status.SUBMITTED)
        log.source = ServiceLog.Source.UNSCHEDULED
        log.service_date = date(2026, 6, 4)
        log.save()
        log.shift.service_date = date(2026, 5, 1)
        log.shift.source = Shift.Source.UNSCHEDULED
        log.shift.save()
        workbench = self.get_workbench().context['workbench']
        self.assertEqual([row['log'].pk for row in workbench['log_rows']], [log.pk])
        self.assertEqual(workbench['missing_log_count'], 0)
        self.assertTrue(workbench['log_rows'][0]['unscheduled'])

    def test_same_hours_changed_time_window_is_independent_difference(self):
        log = self.create_service_log(status=ServiceLog.Status.SUBMITTED)
        log.actual_start_time, log.actual_end_time = time(10), time(12)
        log.save()
        row = self.get_workbench().context['workbench']['log_rows'][0]
        self.assertFalse(row['hours_differ'])
        self.assertTrue(row['time_window_differ'])

    def test_submitted_card_labels_original_worker_notes_and_case_notes_separately(self):
        log = self.create_service_log(status=ServiceLog.Status.SUBMITTED,
                                      case_notes='Original case note evidence')
        log.worker_notes = 'Original worker note evidence'
        log.save()
        response = self.get_workbench()
        for text in ('Worker notes', 'Case notes', 'Original case note evidence',
                     'Original worker note evidence', log.get_absolute_url(),
                     'Travel claim not included'):
            self.assertContains(response, text)
        self.assertNotContains(response, 'name="action"')
        self.assertNotContains(response, 'disabled')

    def test_approved_unbilled_sources_estimate_and_blockers(self):
        self.create_service_log()
        self.create_service_log(status=ServiceLog.Status.SUBMITTED)
        self.create_service_log(status=ServiceLog.Status.REJECTED)
        self.create_shift()
        self.cancellation(ParticipantCancellation.Status.APPROVED)
        self.cancellation(ParticipantCancellation.Status.PENDING)
        row = self.get_workbench().context['workbench']['participant_rows'][0]
        self.assertEqual(row['approved_log_count'], 1)
        self.assertEqual(row['approved_cancellation_count'], 1)
        self.assertEqual(row['missing_count'], 1)
        self.assertEqual(row['pending_count'], 2)
        self.assertEqual(row['rejected_count'], 1)
        self.assertEqual(row['service_estimate'], Decimal('261.88'))
        self.assertEqual(row['readiness'], 'Partial')

    def test_existing_invoice_does_not_suppress_fresh_sources_and_uses_saved_source_dates(self):
        old = self.create_service_log(status=ServiceLog.Status.INVOICED)
        invoice = self.make_invoice(old, status=Invoice.Status.PAID)
        fresh = self.create_service_log()
        response = self.get_workbench()
        workbench = response.context['workbench']
        self.assertEqual(workbench['participant_rows'][0]['approved_log_count'], 1)
        self.assertEqual(workbench['participant_rows'][0]['readiness'], 'Additional')
        self.assertEqual([row['invoice'].pk for row in workbench['invoice_rows']], [invoice.pk])
        self.assertContains(response, 'Paid')
        self.assertEqual(fresh.status, ServiceLog.Status.APPROVED)

    def test_invoice_period_overlap_alone_does_not_make_invoice_related(self):
        outside = self.create_service_log(service_date=date(2026, 5, 1))
        self.make_invoice(outside, period_start=date(2026, 6, 1), period_end=date(2026, 6, 7))
        self.assertEqual(self.get_workbench().context['workbench']['invoice_rows'], [])

    def test_cancellation_invoice_source_dates_are_related(self):
        cancellation = self.cancellation(ParticipantCancellation.Status.APPROVED)
        invoice = Invoice.objects.create(participant=self.participant,
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 1), created_by=self.admin_user)
        InvoiceLine.objects.create_from_participant_cancellation(invoice=invoice, cancellation=cancellation)
        row = self.get_workbench().context['workbench']['invoice_rows'][0]
        self.assertEqual(row['invoice'], invoice)
        self.assertEqual(self.get_workbench().context['workbench']['participant_rows'][0]['approved_cancellation_count'], 0)

    def test_archived_participant_sources_remain_visible(self):
        self.participant.status = Participant.Status.ARCHIVED
        self.participant.save()
        self.create_service_log()
        response = self.get_workbench()
        self.assertContains(response, 'Archived')
        self.assertEqual(response.context['workbench']['participant_rows'][0]['participant'], self.participant)

    def test_plan_manager_readiness_uses_current_participant_email_and_other_types_manual(self):
        self.participant.management_type = Participant.ManagementType.PLAN_MANAGED
        self.participant.plan_manager_email = ''
        self.participant.save()
        invoice = self.make_invoice(self.create_service_log())
        self.assertEqual(self.get_workbench().context['workbench']['invoice_rows'][0]['delivery'], 'PM email missing')
        self.participant.plan_manager_email = 'current@example.com'
        self.participant.save()
        self.assertEqual(self.get_workbench().context['workbench']['invoice_rows'][0]['delivery'], 'current@example.com')
        self.participant.management_type = Participant.ManagementType.SELF_MANAGED
        self.participant.save()
        self.assertEqual(self.get_workbench().context['workbench']['invoice_rows'][0]['delivery'], 'Manual handling')

    def test_prior_period_unbilled_has_original_period_link(self):
        self.create_service_log(service_date=date(2026, 5, 20))
        response = self.get_workbench()
        self.assertEqual(response.context['workbench']['earlier_unbilled_count'], 1)
        self.assertContains(response, 'Earlier unbilled')
        self.assertContains(response, 'start=2026-05-20')

    def test_queries_do_not_grow_per_participant(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from invoices.workbench_queries import build_weekly_workbench
        self.create_service_log()
        with CaptureQueriesContext(connection) as first:
            build_weekly_workbench(date(2026, 6, 1), date(2026, 6, 7))
        for index in range(6):
            participant = Participant.objects.create(first_name='Scale', last_name=str(index))
            self.create_service_log(participant=participant)
        with CaptureQueriesContext(connection) as expanded:
            build_weekly_workbench(date(2026, 6, 1), date(2026, 6, 7))
        self.assertLessEqual(len(expanded), len(first) + 1)

    def test_dashboard_and_business_navigation_link_to_workbench(self):
        response = self.get_workbench()
        self.assertContains(response, 'class="sidebar-link active" href="/billing/weekly/"')
        dashboard = self.client.get(reverse('admin_dashboard'))
        self.assertContains(dashboard, '/billing/weekly/')

    def test_accountant_invoice_navigation_does_not_expose_workbench(self):
        self.client.force_login(self.accountant_user)
        response = self.client.get(reverse('invoice_placeholder'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '/billing/weekly/')

    def test_log_statuses_and_pending_cancellation_are_visible_without_actions(self):
        for status in ServiceLog.Status.values:
            self.create_service_log(status=status)
        cancellation = self.cancellation(ParticipantCancellation.Status.PENDING)
        response = self.get_workbench()
        for text in ('Submitted', 'Approved', 'Rejected', 'Invoiced',
                     'Pending review', 'Cancellation evidence'):
            self.assertContains(response, text)
        self.assertContains(response, reverse('participant_cancellation_detail', args=[cancellation.pk]))

    def test_legacy_selectors_none_stays_empty_and_bulk_selectors_are_explicit(self):
        from invoices.selectors import billable_logs_in_period, billable_cancellations_in_period
        from invoices.views import get_billable_logs, get_billable_cancellations
        self.create_service_log()
        self.cancellation(ParticipantCancellation.Status.APPROVED)
        start, end = date(2026, 6, 1), date(2026, 6, 7)
        self.assertFalse(get_billable_logs(None, start, end).exists())
        self.assertFalse(get_billable_cancellations(None, start, end).exists())
        self.assertEqual(billable_logs_in_period(start, end).count(), 1)
        self.assertEqual(billable_cancellations_in_period(start, end).count(), 1)

    def test_rejected_cancellation_without_log_is_missing_once(self):
        cancellation = self.cancellation(ParticipantCancellation.Status.REJECTED)
        workbench = self.get_workbench().context['workbench']
        row = workbench['participant_rows'][0]
        self.assertEqual(row['missing_count'], 1)
        self.assertEqual(row['rejected_count'], 0)
        self.assertEqual(workbench['roster_rows'][0]['status'], 'Missing')

    def test_rejected_cancellation_with_approved_log_has_no_blocker(self):
        cancellation = self.cancellation(ParticipantCancellation.Status.REJECTED)
        ServiceLog.objects.create_from_shift(shift=cancellation.shift,
            actual_start_time=time(9), actual_end_time=time(11), break_minutes=0,
            actual_hours=Decimal('2.00'), case_notes='Restored service', status=ServiceLog.Status.APPROVED)
        row = self.get_workbench().context['workbench']['participant_rows'][0]
        self.assertEqual(row['blocker_count'], 0)
        self.assertEqual(row['readiness'], 'Ready')

    def test_invoice_only_participant_does_not_claim_waiting_for_review(self):
        self.make_invoice(self.create_service_log(status=ServiceLog.Status.INVOICED))
        row = self.get_workbench().context['workbench']['participant_rows'][0]
        self.assertEqual(row['readiness'], 'No unbilled sources')

    def test_future_only_participant_is_upcoming(self):
        day = timezone.localdate() + timedelta(days=1)
        self.create_shift(service_date=day)
        response = self.get_workbench(start=day.isoformat(), end=day.isoformat())
        self.assertEqual(response.context['workbench']['participant_rows'][0]['readiness'], 'Upcoming')

    def test_original_log_link_uses_participant_id_and_same_period(self):
        self.create_service_log()
        response = self.get_workbench()
        self.assertContains(response, '?participant=' + str(self.participant.pk) + '&amp;date_range=custom')

    def test_pending_cancellation_counts_in_review_step_with_no_submitted_logs(self):
        self.cancellation(ParticipantCancellation.Status.PENDING)
        workbench = self.get_workbench().context['workbench']
        self.assertEqual(workbench['pending_cancellation_count'], 1)
        self.assertEqual(workbench['submitted_rows'], [])

    def test_rendered_unscheduled_logs_do_not_add_queries_per_record(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        def add_unscheduled():
            log = self.create_service_log()
            log.source = ServiceLog.Source.UNSCHEDULED
            log.save()
            log.shift.service_date = date(2026, 5, 1)
            log.shift.source = Shift.Source.UNSCHEDULED
            log.shift.save()
        add_unscheduled()
        self.client.force_login(self.admin_user)
        params = {'period': 'custom', 'start': '2026-06-01', 'end': '2026-06-07'}
        with CaptureQueriesContext(connection) as first:
            response = self.client.get('/billing/weekly/', params)
        self.assertEqual(response.status_code, 200)
        for index in range(4):
            add_unscheduled()
        with CaptureQueriesContext(connection) as expanded:
            response = self.client.get('/billing/weekly/', params)
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(expanded), len(first) + 1, (len(first), len(expanded)))

    def test_future_terminal_and_draft_roster_statuses_remain_stored_not_upcoming(self):
        day = timezone.localdate() + timedelta(days=1)
        states = (Shift.Status.CANCELLED, Shift.Status.DRAFT, Shift.Status.COMPLETED)
        for status in states:
            self.create_shift(service_date=day, status=status)
        workbench = self.get_workbench(start=day.isoformat(), end=day.isoformat()).context['workbench']
        self.assertCountEqual([row['status'] for row in workbench['roster_rows']],
                              [dict(Shift.Status.choices)[state] for state in states])
        self.assertEqual(workbench['participant_rows'][0]['upcoming_count'], 0)
        self.assertEqual(workbench['participant_rows'][0]['readiness'], 'No unbilled sources')

    def test_future_unscheduled_shift_without_log_does_not_invent_upcoming_service(self):
        day = timezone.localdate() + timedelta(days=1)
        self.create_shift(service_date=day, source=Shift.Source.UNSCHEDULED)
        workbench = self.get_workbench(start=day.isoformat(), end=day.isoformat()).context['workbench']
        self.assertEqual(workbench['roster_rows'][0]['status'], 'Published')
        self.assertEqual(workbench['participant_rows'][0]['upcoming_count'], 0)
        self.assertNotEqual(workbench['participant_rows'][0]['readiness'], 'Upcoming')

    def test_future_confirmed_scheduled_shift_is_upcoming(self):
        day = timezone.localdate() + timedelta(days=1)
        self.create_shift(service_date=day, status=Shift.Status.CONFIRMED)
        workbench = self.get_workbench(start=day.isoformat(), end=day.isoformat()).context['workbench']
        self.assertEqual(workbench['roster_rows'][0]['status'], 'Upcoming')
        self.assertEqual(workbench['participant_rows'][0]['upcoming_count'], 1)

    def test_period_filters_reuse_accepted_calendar_with_one_named_field_each(self):
        from html.parser import HTMLParser
        from django.templatetags.static import static
        class Controls(HTMLParser):
            def __init__(self, html):
                super().__init__()
                self.ids, self.named, self.proxies = [], [], []
                self.feed(html)
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if attrs.get('id'):
                    self.ids.append(attrs['id'])
                if tag in ('input', 'select') and attrs.get('name') in ('period', 'start', 'end'):
                    self.named.append(attrs['name'])
                if 'data-invoice-date-proxy' in attrs:
                    self.proxies.append(attrs)
        response = self.get_workbench()
        html = response.content.decode()
        controls = Controls(html)
        self.assertCountEqual(controls.named, ['period', 'start', 'end'])
        self.assertEqual(len(controls.ids), len(set(controls.ids)))
        self.assertEqual(len(controls.proxies), 2)
        self.assertTrue(all('name' not in proxy for proxy in controls.proxies))
        self.assertContains(response, 'data-invoice-filters')
        self.assertContains(response, 'data-weekly-billing-filters')
        scripts = [static('js/' + name) for name in (
            'date_time_picker.js', 'r1_admin_invoice_filters.js', 'weekly_billing.js')]
        for script in scripts:
            self.assertContains(response, script, count=1)
        self.assertEqual([html.index(script) for script in scripts],
                         sorted(html.index(script) for script in scripts))
        self.assertNotContains(response, 'css/r1_admin_invoice_list.')

    def test_invalid_period_dates_retain_values_with_connected_server_errors(self):
        response = self.get_workbench(start='2026-06-07', end='2026-06-01')
        self.assertTrue(response.context['period_form'].errors)
        self.assertContains(response, 'name="start" value="2026-06-07"')
        self.assertContains(response, 'name="end" value="2026-06-01"')
        self.assertContains(response, 'id="invoice-end-server-error"')
        self.assertContains(response, 'aria-describedby="invoice-end-client-error invoice-end-server-error"', count=2)
        self.assertContains(response, 'aria-invalid="true"', count=2)
        self.assertContains(response, 'The end date must be on or after the start date.')
