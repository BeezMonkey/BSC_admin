from datetime import date, time
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.templatetags.static import static
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from core.models import AuditLog
from core.formatting import format_display_time
from documents.tests_r1_ui import Page
from invoices.models import Invoice, InvoiceLine
from scheduling.models import SupportItem
from .models import CoordinationLog, CoordinationLogChange
from .tests import create_coordinator, create_participant


class AdminCoordinationLogR1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username='b081-admin')
        UserProfile.objects.create(user=cls.admin, role='admin')
        cls.sc = create_coordinator('b081-sc')
        cls.person = create_participant()
        cls.log = CoordinationLog.objects.create(participant=cls.person, coordinator=cls.sc,
            service_date=date(2026, 10, 12), actual_hours=Decimal('1.25'),
            case_notes='Complete fictional note.\nSecond line <script>unsafe</script>', status='submitted')

    def setUp(self):
        self.client.force_login(self.admin)
        self.list_url = reverse('coordination_log_list')
        self.detail = reverse('coordination_log_detail', args=[self.log.pk])
        self.correction = reverse('coordination_log_correction', args=[self.log.pk])

    def invoice(self, status='invoiced'):
        item = SupportItem.objects.create(item_number='QA-B081', name='Fictional item', unit='H', price_limit=Decimal('100.00'))
        invoice = Invoice.objects.create(participant=self.person, period_start=self.log.service_date,
            period_end=self.log.service_date, created_by=self.admin, invoice_type='support_coordination')
        InvoiceLine.objects.create_from_coordination_log(invoice, self.log, item)
        self.log.status = status
        self.log.save()
        return invoice

    def test_three_routes_opt_in_to_only_dedicated_style(self):
        self.invoice()
        for url in [self.list_url, self.detail, self.correction]:
            response = self.client.get(url)
            self.assertContains(response, 'r1-admin-coordination-logs')
            for css in ['r1_tokens.css', 'r1_shell.css', 'r1_admin_coordination_logs.css']:
                self.assertContains(response, static('css/' + css), count=1)
            self.assertNotContains(response, 'r1_coordinator_log.css')
            self.assertContains(response, 'Coordination / Coordination Logs')

    def test_list_retains_nine_columns_and_mobile_labels(self):
        response = self.client.get(self.list_url)
        tree = Page(response).root
        tables = [t for t in tree.find('table') if t.has_class('r1-coordination-table')]
        self.assertEqual(len(tables), 1)
        table = tables[0]
        self.assertEqual([t.text for t in table.find('th')], ['Select', 'Date', 'Participant', 'Coordinator', 'Type', 'Status', 'Hours', 'Notes', 'Actions'])
        self.assertTrue(table.parent.has_class('r1-coordination-table-wrap'))
        self.assertEqual([t.attrs.get('data-label') for t in table.find('td')], ['Select', 'Date', 'Participant', 'Coordinator', 'Type', 'Status', 'Hours', 'Notes', 'Actions'])
        self.assertContains(response, 'Submitted ')
        self.assertContains(response, 'Support coordinator')
        self.assertContains(response, self.person.display_name)

    def test_filter_and_safe_detail_return_preserve_original_destinations(self):
        response = self.client.get(self.list_url + '?status=submitted')
        tree = Page(response).root
        self.assertEqual(len(tree.find('select', name='status')), 1)
        self.assertEqual(len(tree.find('select', name='status')[0].find('option')), len(CoordinationLog.Status.choices) + 1)
        self.assertContains(response, '?next=/coordination-logs/%3Fstatus%3Dsubmitted')
        response = self.client.get(self.detail + '?next=%2Fcoordination-logs%2F%3Fstatus%3Dsubmitted')
        self.assertContains(response, 'href="/coordination-logs/?status=submitted"')
        self.assertNotContains(self.client.get(self.detail + '?next=https://example.invalid'), 'href="https://example.invalid"')

    def test_selection_remains_approved_and_without_invoice_line_only(self):
        for status in ['submitted', 'rejected', 'invoiced', 'approved']:
            self.log.status = status
            self.log.save()
            tree = Page(self.client.get(self.list_url)).root
            self.assertEqual(len(tree.find('input', name='coordination_log_ids')), int(status == 'approved'))
        self.invoice(status='approved')
        self.assertNotContains(self.client.get(self.list_url), 'name="coordination_log_ids"')

    def test_billing_get_form_and_view_button_keep_original_targets(self):
        tree = Page(self.client.get(self.list_url)).root
        form = tree.find('form', action=reverse('support_coordination_invoice_create'))[0]
        self.assertEqual(form.attrs['method'], 'get')
        link = next(a for a in tree.find('a') if a.text == 'View')
        self.assertTrue(link.has_class('button'))
        self.assertTrue(link.has_class('secondary'))
        self.assertTrue(link.attrs['href'].startswith(self.detail + '?next='))

    def test_both_empty_states_preserve_original_explanations(self):
        self.assertContains(self.client.get(self.list_url + '?status=rejected'), 'No coordination logs match the current filters.')
        self.log.delete()
        self.assertContains(self.client.get(self.list_url), 'Coordination logs appear here after support coordinators submit their work.')

    def test_detail_all_original_information_and_full_escaped_notes(self):
        self.log.start_time, self.log.end_time, self.log.break_minutes = time(9), time(10, 30), 15
        self.log.coordinator_notes = 'Legacy complete coordinator note.'
        self.log.reviewed_by, self.log.reviewed_at = self.admin, timezone.now()
        self.log.rejection_reason = 'Complete rejection explanation.'
        self.log.save()
        response = self.client.get(self.detail)
        for value in ['r1-admin-coordination-detail', 'Coordination Log', 'Notes', 'Service date', 'Status', 'Coordinator', 'Coordination type', 'Service duration',
                      'Previously recorded time', format_display_time(time(9)), format_display_time(time(10, 30)), 'Recorded break', '15 minutes', 'Reviewed by', 'Reviewed at',
                      self.log.coordinator_notes, self.log.rejection_reason, 'Second line &lt;script&gt;unsafe&lt;/script&gt;']:
            self.assertContains(response, value)
        self.assertNotContains(response, '<script>unsafe</script>')

    def test_review_csrf_revision_and_required_reason_are_unchanged(self):
        response = self.client.get(self.detail)
        tree = Page(response).root
        for name in ['coordination_log_approve', 'coordination_log_reject']:
            form = tree.find('form', action=reverse(name, args=[self.log.pk]))[0]
            self.assertEqual(form.attrs['method'], 'post')
            self.assertTrue(form.find('input', name='csrfmiddlewaretoken'))
            self.assertEqual(form.find('input', name='revision_token')[0].attrs['value'], response.context['revision_token'])
        self.assertIn('required', tree.find('input', name='rejection_reason')[0].attrs)

    def test_approved_or_invoice_linked_log_never_gets_review_controls(self):
        self.log.status = 'approved'
        self.log.save()
        self.assertNotContains(self.client.get(self.detail), 'class="service-log-review-card"')
        self.invoice(status='submitted')
        response = self.client.get(self.detail)
        self.assertNotContains(response, 'name="rejection_reason"')
        self.assertContains(response, self.correction)

    def test_review_success_and_failure_messages_remain_original(self):
        token = self.client.get(self.detail).context['revision_token']
        reject = reverse('coordination_log_reject', args=[self.log.pk])
        response = self.client.post(reject, {'revision_token': token}, follow=True)
        self.assertContains(response, 'Rejection reason is required.')
        self.assertContains(response, 'message error')
        response = self.client.post(reject, {'revision_token': token, 'rejection_reason': 'Retained reason'}, follow=True)
        self.assertContains(response, 'Coordination log rejected.')
        self.log.refresh_from_db()
        self.assertEqual(self.log.rejection_reason, 'Retained reason')

    def test_stale_and_already_reviewed_messages_remain_original(self):
        token = self.client.get(self.detail).context['revision_token']
        self.log.case_notes = 'Changed in another session.'
        self.log.save()
        approve = reverse('coordination_log_approve', args=[self.log.pk])
        self.assertContains(self.client.post(approve, {'revision_token': token}, follow=True), 'Coordination log has changed. Review the latest record before making a decision.')
        self.log.status = 'approved'
        self.log.save()
        self.assertContains(self.client.post(approve, {'revision_token': token}, follow=True), 'Coordination log has already been reviewed.')

    def test_history_and_original_expansion_script_are_preserved(self):
        value = 'Fictional complete history. ' * 100
        CoordinationLogChange.objects.create(log=self.log, actor=self.admin, kind='revision', reason='Complete reason', details='Additional explanation',
            before={'case_notes': value, 'status': 'approved', 'reviewed_by': 'Admin'}, after={'case_notes': self.log.case_notes, 'status': 'submitted', 'reviewed_by': ''})
        response = self.client.get(self.detail)
        for text in ['Change history', 'Before', 'After', 'Review details', 'Show full text', 'data-history-text-value', value, 'Additional explanation']:
            self.assertContains(response, text)
        self.assertContains(response, static('js/sc_log_history.js'), count=1)

    def test_correction_uninvoiced_guard_remains_403(self):
        response = self.client.get(self.correction)
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Corrections are for invoiced logs.', status_code=403)

    def test_correction_fields_limits_notices_and_invoice_links_preserved(self):
        invoice = self.invoice()
        response = self.client.get(self.correction)
        tree = Page(response).root
        self.assertContains(response, 'r1-admin-coordination-correction')
        for text in ['The original log and invoice remain unchanged. Date, time or charge corrections require a separate invoice review.', invoice.invoice_number,
                     reverse('invoice_detail', args=[invoice.pk]), 'Add correction note', 'Billing correction - invoice review required']:
            self.assertContains(response, text)
        self.assertEqual(len(tree.find('select', name='kind')[0].find('option')), 2)
        for name, maximum in [('reason', '2000'), ('details', '10000')]:
            field = tree.find('textarea', name=name)[0]
            self.assertEqual(field.attrs['maxlength'], maximum)
            self.assertIn('required', field.attrs)

    def test_correction_validation_keeps_values_and_errors(self):
        self.invoice()
        token = self.client.get(self.correction).context['revision_token']
        response = self.client.post(self.correction, {'revision_token': token, 'kind': 'correction', 'reason': '', 'details': 'Retained typed details'})
        self.assertContains(response, 'This field is required.')
        self.assertContains(response, 'Retained typed details')
        self.assertFalse(self.log.changes.exists())

    def test_correction_stale_409_keeps_reload_token_and_entered_values(self):
        self.invoice()
        token = self.client.get(self.correction).context['revision_token']
        self.log.save()
        response = self.client.post(self.correction, {'revision_token': token, 'kind': 'correction', 'reason': 'Unsaved reason', 'details': 'Unsaved details'})
        self.assertEqual(response.status_code, 409)
        for text in ['This log has changed. Reload before recording a correction.', 'Reload latest version', 'Unsaved reason', 'Unsaved details', 'r1-coordination-form-error']:
            self.assertContains(response, text, status_code=409)
        self.assertEqual(response.context['revision_token'], token)

    def test_correction_success_does_not_change_original_business_values(self):
        invoice = self.invoice()
        before = (self.log.case_notes, self.log.actual_hours, invoice.total_amount)
        token = self.client.get(self.correction).context['revision_token']
        response = self.client.post(self.correction, {'revision_token': token, 'kind': 'billing_review', 'reason': 'Fictional billing review', 'details': 'Full explanation'}, follow=True)
        self.assertContains(response, 'Correction recorded. Original log and invoice values are unchanged.')
        self.assertContains(response, 'Invoice review required. This entry does not change the original log or invoice.')
        self.log.refresh_from_db()
        invoice.refresh_from_db()
        self.assertEqual((self.log.case_notes, self.log.actual_hours, invoice.total_amount), before)

    def test_permissions_and_post_csrf_are_unchanged(self):
        self.invoice()
        self.client.force_login(self.sc.user)
        for url in [self.list_url, self.detail, self.correction]:
            self.assertEqual(self.client.get(url).status_code, 403)
        from django.test import Client
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)
        self.assertEqual(csrf_client.post(reverse('coordination_log_approve', args=[self.log.pk])).status_code, 403)

    def test_read_only_gets_do_not_write_audit_history_or_logs(self):
        self.invoice()
        before = (AuditLog.objects.count(), CoordinationLogChange.objects.count(), list(CoordinationLog.objects.values()))
        for url in [self.list_url, self.detail, self.correction]:
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual((AuditLog.objects.count(), CoordinationLogChange.objects.count(), list(CoordinationLog.objects.values())), before)

    def test_accepted_sc_and_unrelated_admin_pages_do_not_load_new_style(self):
        for name in ['coordinator_dashboard', 'coordinator_account', 'coordinator_log_list', 'coordinator_participant_list']:
            self.client.force_login(self.sc.user)
            self.assertNotContains(self.client.get(reverse(name)), 'r1_admin_coordination_logs.css')
        self.client.force_login(self.admin)
        for url in ['/documents/', '/service-logs/', '/invoices/', '/coordinators/']:
            self.assertNotContains(self.client.get(url), 'r1_admin_coordination_logs.css')


class AdminCoordinationLogR1StyleTests(SimpleTestCase):
    def test_button_styles_do_not_override_native_hidden_history_controls(self):
        css = (Path(settings.BASE_DIR) / 'static/css/r1_admin_coordination_logs.css').read_text()
        self.assertIn('.r1-admin-coordination-logs [hidden] { display:none !important; }', css)

    def test_detail_groups_clear_legacy_nested_frame_and_padded_cells(self):
        css = (Path(settings.BASE_DIR) / 'static/css/r1_admin_coordination_logs.css').read_text()
        self.assertIn('.r1-admin-coordination-detail .detail-list { border:0;', css)
        self.assertIn('.r1-admin-coordination-detail .detail-list :is(dt,dd) { padding:0;', css)
        self.assertIn('.app-shell.r1-ui.r1-admin-coordination-logs .record-form .field', css)

    def test_mobile_cells_explicitly_clear_legacy_one_percent_widths(self):
        css = (Path(settings.BASE_DIR) / 'static/css/r1_admin_coordination_logs.css').read_text()
        mobile = css.split('@media (max-width:760px)', 1)[1]
        self.assertIn('.r1-coordination-table td { width:auto;', mobile)
        self.assertIn('.status-pill { justify-self:start;', mobile)

    def test_status_backgrounds_override_shared_shell_specificity(self):
        css = (Path(settings.BASE_DIR) / 'static/css/r1_admin_coordination_logs.css').read_text()
        for status in ['approved', 'submitted', 'rejected', 'invoiced']:
            self.assertIn('.app-shell.r1-ui.r1-admin-coordination-logs .status-pill.status-' + status, css)

    def test_style_is_opt_in_responsive_and_has_no_fixed_page_width(self):
        path = Path(settings.BASE_DIR) / 'static/css/r1_admin_coordination_logs.css'
        self.assertTrue(path.is_file(), 'Dedicated opt-in CSS is not implemented yet')
        css = path.read_text()
        for token in ['.r1-admin-coordination-logs', 'min-width:1080px', 'width:100%', 'max-width:760px', 'min-height:44px', 'appearance:base-select',
                      'var(--r1-accent)', 'var(--r1-text)', 'var(--r1-border)', 'data-label', 'white-space:pre-wrap']:
            self.assertIn(token, css)
        self.assertNotIn(':root', css)
        self.assertNotIn('width:1440px', css)
