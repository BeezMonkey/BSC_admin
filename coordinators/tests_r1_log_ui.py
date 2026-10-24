from datetime import date, time
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.templatetags.static import static
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import AuditLog
from documents.tests_r1_ui import Element, Page
from invoices.models import Invoice, InvoiceLine
from scheduling.models import SupportItem

from .models import CoordinationLog, CoordinationLogChange, ParticipantCoordinatorAssignment
from .tests import create_coordinator, create_participant


class CoordinatorLogR1UITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sc = create_coordinator('r1-log-ui-sc')
        cls.person = create_participant()
        cls.person.internal_notes = 'PRIVATE B073 DO NOT DISPLAY'
        cls.person.save()
        ParticipantCoordinatorAssignment.objects.create(participant=cls.person, coordinator=cls.sc, start_date=date(2026, 1, 1))
        cls.log = CoordinationLog.objects.create(participant=cls.person, coordinator=cls.sc, service_date=date(2026, 10, 12),
            actual_hours=Decimal('1.25'), case_notes='Fictional complete case note.\nSecond line.', status='submitted')

    def setUp(self):
        self.client.force_login(self.sc.user)
        self.detail_url = reverse('coordinator_log_detail', args=[self.log.pk])
        self.edit_url = reverse('coordinator_log_edit', args=[self.log.pk])
        self.create_url = reverse('coordinator_log_create')

    def payload(self, **overrides):
        data = dict(participant=self.person.pk, service_date='2026-10-12', coordination_type='general',
                    duration_hours='1', duration_minutes='15', case_notes='Fictional revised case note.',
                    revision_reason='update_notes', revision_details='')
        data.update(overrides)
        return data

    def post_edit(self, **overrides):
        data = self.payload(revision_token=self.client.get(self.edit_url).context['revision_token'])
        data.update(overrides)
        return self.client.post(self.edit_url, data)

    def test_only_three_routes_load_new_opt_in_assets(self):
        for url in [self.detail_url, self.create_url, self.edit_url]:
            response = self.client.get(url)
            self.assertContains(response, 'r1-coordinator-log-pages')
            self.assertContains(response, static('css/r1_coordinator_log.css'), count=1)
            self.assertNotContains(response, static('css/r1_coordinator_details.css'))
            self.assertNotContains(response, static('css/r1_coordinator_workspace.css'))

    def test_detail_grouping_and_all_original_fields_are_preserved(self):
        response = self.client.get(self.detail_url)
        self.assertContains(response, 'r1-sc-log-detail')
        for value in ['Service Details', 'Review', 'Case Notes', 'Status', 'Participant', 'Date', 'Service duration',
                      'Coordination type', 'Submitted', self.person.display_name, '12/10/2026', '1h 15m', 'Second line.']:
            self.assertContains(response, value)
        for value in ['Previously recorded time', 'Recorded break', 'Coordinator Notes', 'Change history', self.person.internal_notes]:
            self.assertNotContains(response, value)

    def test_legacy_times_break_and_optional_notes_are_not_removed(self):
        self.log.start_time = time(9)
        self.log.end_time = time(10, 30)
        self.log.break_minutes = 15
        self.log.coordinator_notes = 'Previously recorded coordinator notes.'
        self.log.save()
        response = self.client.get(self.detail_url)
        for text in ['Previously recorded time', '9:00 AM', '10:30 AM', 'Recorded break', '15 minutes', self.log.coordinator_notes]:
            self.assertContains(response, text)

    def test_rejected_reason_and_review_timestamp_are_complete_and_escaped(self):
        self.log.status = 'rejected'
        self.log.reviewed_at = timezone.now()
        self.log.rejection_reason = 'Retain line one.\n<script>unsafe</script>'
        self.log.save()
        response = self.client.get(self.detail_url)
        self.assertContains(response, 'Rejection reason')
        self.assertContains(response, 'Reviewed')
        self.assertContains(response, '&lt;script&gt;unsafe&lt;/script&gt;')
        self.assertNotContains(response, '<script>unsafe</script>')
        self.assertContains(response, self.edit_url)

    def test_invoiced_detail_and_direct_edit_preserve_read_only_contract(self):
        self.log.status = 'invoiced'
        self.log.save()
        response = self.client.get(self.detail_url)
        self.assertContains(response, 'This log is read-only because it has been invoiced. Contact Admin for a correction.')
        self.assertNotContains(response, self.edit_url)
        blocked = self.client.get(self.edit_url)
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.content.decode(), 'This log is read-only. Contact Admin for a correction.')

    def test_approved_with_invoice_line_is_also_read_only(self):
        item = SupportItem.objects.create(item_number='QA-B073', name='Fictional coordination', unit=SupportItem.Unit.HOUR, price_limit=Decimal('100.00'))
        invoice = Invoice.objects.create(participant=self.person, period_start=self.log.service_date, period_end=self.log.service_date,
                                        created_by=self.sc.user, invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION)
        InvoiceLine.objects.create_from_coordination_log(invoice, self.log, item)
        self.log.status = 'approved'
        self.log.save()
        response = self.client.get(self.detail_url)
        self.assertContains(response, 'Approved')
        self.assertNotContains(response, self.edit_url)
        self.assertEqual(self.client.get(self.edit_url).status_code, 403)

    def test_create_fields_limits_and_original_scripts_remain(self):
        response = self.client.get(self.create_url)
        self.assertContains(response, 'r1-sc-log-form-page')
        tree = Page(response).root
        self.assertEqual(len(tree.find('select', name='participant')), 1)
        self.assertEqual(len(tree.find('select', name='coordination_type')[0].find('option')), 6)
        for name, maximum in [('duration_hours', '24'), ('duration_minutes', '59')]:
            node = tree.find('input', name=name)[0]
            self.assertEqual((node.attrs['min'], node.attrs['max'], node.attrs['step']), ('0', maximum, '1'))
        for script in ['date_time_picker.js', 'sc_log_form.js']:
            self.assertContains(response, static('js/' + script))
        self.assertNotContains(response, 'revision_reason')
        self.assertNotContains(response, 'sc_log_revision.js')

    def test_duration_inputs_precede_small_accessible_labels(self):
        for url in [self.create_url, self.edit_url]:
            tree = Page(self.client.get(url)).root
            for name, caption in [('duration_hours', 'Hours'), ('duration_minutes', 'Minutes')]:
                node = tree.find('input', name=name)[0]
                label = node.parent
                self.assertTrue(label.has_class('r1-sc-duration-field'))
                self.assertEqual(label.attrs['for'], node.attrs['id'])
                parts = [c for c in label.children if isinstance(c, Element)]
                self.assertIs(parts[0], node)
                self.assertEqual(parts[1].text, caption)
                self.assertTrue(parts[1].has_class('r1-sc-duration-caption'))

    def test_original_post_csrf_revision_token_and_cancel_destinations(self):
        for url in [self.create_url, self.edit_url]:
            response = self.client.get(url)
            tree = Page(response).root
            form = next(f for f in tree.find('form') if f.has_class('sc-log-form'))
            self.assertEqual(form.attrs['method'], 'post')
            self.assertIn('novalidate', form.attrs)
            self.assertTrue(form.find('input', name='csrfmiddlewaretoken'))
            self.assertEqual(bool(form.find('input', name='revision_token')), url == self.edit_url)
        self.assertContains(self.client.get(self.edit_url), self.detail_url)

    def test_other_error_keeps_original_visibility_and_entered_notes(self):
        response = self.post_edit(revision_reason='other', revision_details='')
        self.assertEqual(response.status_code, 200)
        tree = Page(response).root
        self.assertNotIn('hidden', tree.find('div', id='sc-revision-details')[0].attrs)
        self.assertContains(response, 'Additional details (required)')
        self.assertContains(response, 'This field is required.')
        self.assertContains(response, 'Fictional revised case note.')
        self.assertTrue(response.context['form'].fields['participant'].disabled)

    def test_duration_errors_remain_at_original_named_fields(self):
        cases = [('0', '0', 'Enter a service duration of at least 1 minute.'),
                 ('24', '1', 'Service duration cannot exceed 24 hours.'),
                 ('1', '60', 'Ensure this value is less than or equal to 59.')]
        for hours, minutes, message in cases:
            response = self.client.post(self.create_url, self.payload(duration_hours=hours, duration_minutes=minutes))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, message)
            self.assertContains(response, 'r1-sc-duration-caption')

    def test_no_change_error_does_not_write_or_create_history(self):
        response = self.post_edit(case_notes=self.log.case_notes)
        self.assertContains(response, 'No changes to submit.')
        self.assertFalse(self.log.changes.exists())

    def test_stale_409_preserves_message_reload_and_typed_values(self):
        token = self.client.get(self.edit_url).context['revision_token']
        self.log.case_notes = 'Changed by another session.'
        self.log.save()
        response = self.client.post(self.edit_url, self.payload(revision_token=token, case_notes='Retained unsaved notes.'))
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, 'This log has changed. Reload the latest version before editing.', status_code=409)
        self.assertContains(response, 'Reload latest version', status_code=409)
        self.assertContains(response, 'Retained unsaved notes.', status_code=409)
        self.assertEqual(response.context['revision_token'], token)

    def test_approved_edit_warning_and_original_resubmit_transition(self):
        self.log.status = 'approved'
        self.log.reviewed_at = timezone.now()
        self.log.save()
        self.assertContains(self.client.get(self.edit_url), 'Saving removes the current approval. Admin must approve the revised record before invoicing.')
        response = self.post_edit()
        self.assertRedirects(response, self.detail_url, fetch_redirect_response=False)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, 'submitted')
        self.assertIsNone(self.log.reviewed_at)
        self.assertContains(self.client.get(self.detail_url), 'Changes submitted for admin review.')

    def test_original_create_success_copy_and_redirect(self):
        response = self.client.post(self.create_url, self.payload())
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(response.url), 'Coordination log submitted for admin review.')

    def test_all_history_content_review_details_and_full_text_hooks_preserved(self):
        value = 'Complete historical note. ' * 80 + '<script>unsafe</script>'
        CoordinationLogChange.objects.create(log=self.log, actor=self.sc.user, kind='revision', reason='Update notes', details='Full original explanation.',
            before={'case_notes': value, 'status': 'approved', 'reviewed_by': 'Admin'},
            after={'case_notes': self.log.case_notes, 'status': 'submitted', 'reviewed_by': ''})
        response = self.client.get(self.detail_url)
        for text in ['Change history', 'Review details', 'Before', 'After', 'Full original explanation.', 'Show full text', 'data-history-text-value', value[:1000]]:
            self.assertContains(response, text)
        self.assertContains(response, '&lt;script&gt;unsafe&lt;/script&gt;')
        self.assertContains(response, static('js/sc_log_history.js'))

    def test_accepted_sc_and_admin_pages_do_not_load_new_styles(self):
        routes = [reverse('coordinator_account'), reverse('coordinator_participant_detail', args=[self.person.pk]),
                  reverse('coordinator_dashboard'), reverse('coordinator_participant_list'), reverse('coordinator_log_list')]
        for url in routes:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, static('css/r1_coordinator_log.css'))

    def test_read_only_gets_do_not_mutate_records_or_audit(self):
        before = (list(CoordinationLog.objects.values()), CoordinationLogChange.objects.count(), AuditLog.objects.count())
        for url in [self.detail_url, self.create_url, self.edit_url]:
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(before, (list(CoordinationLog.objects.values()), CoordinationLogChange.objects.count(), AuditLog.objects.count()))

    def test_other_coordinator_and_anonymous_keep_original_access_boundaries(self):
        other = create_coordinator('b073-other')
        self.client.force_login(other.user)
        for url in [self.detail_url, self.edit_url]:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.client.logout()
        for url in [self.detail_url, self.edit_url, self.create_url]:
            self.assertEqual(self.client.get(url).status_code, 302)


class CoordinatorLogR1StyleTests(SimpleTestCase):
    def test_styles_are_scoped_and_include_approved_picker_and_duration_treatment(self):
        path = Path(settings.BASE_DIR) / 'static/css/r1_coordinator_log.css'
        self.assertTrue(path.is_file())
        css = path.read_text(encoding='utf-8')
        for text in ['.r1-coordinator-log-pages', 'border-radius:8px', 'border-radius:6px',
                     'font-size:24px', 'font-size:16px', 'font-size:12px', 'min-height:36px', 'min-height:44px',
                     'selector(select::picker(select))', 'appearance:base-select', 'var(--r1-blue-soft)',
                     '.r1-sc-duration-caption', '@media (max-width:980px)', 'overflow-wrap:anywhere']:
            self.assertIn(text, css)
        self.assertNotIn(':root', css)

    def test_log_overrides_defeat_legacy_widths_and_control_styles(self):
        css = (Path(settings.BASE_DIR) / 'static/css/r1_coordinator_log.css').read_text(encoding='utf-8')
        for rule in [
            '.r1-coordinator-log-pages .sc-log-form .sc-service-duration { width:100%; max-width:none;',
            '.r1-coordinator-log-pages .sc-log-form .field > span:first-child { font-size:14px; line-height:20px;',
            '.r1-coordinator-log-pages .sc-log-form .form-section h2 { padding:0; border:0;',
            '.r1-coordinator-log-pages .sc-log-revision .sc-log-revision-reason { max-width:none;',
            '.app-shell.r1-ui.r1-coordinator-log-pages .sc-log-form select { appearance:base-select;',
            '.r1-coordinator-log-pages .worker-sidebar { display:none;',
            '.r1-coordinator-log-pages .detail-list :is(dt,dd) { padding:0; border:0; background:transparent;',
        ]:
            self.assertIn(rule, css)

    def test_dedicated_base_does_not_reuse_accepted_workspace_or_detail_assets(self):
        path = Path(settings.BASE_DIR) / 'templates/r1/coordinator_log_base.html'
        self.assertTrue(path.is_file())
        text = path.read_text(encoding='utf-8')
        self.assertIn('extends "coordinator_base.html"', text)
        self.assertNotIn('r1_coordinator_details.css', text)
        self.assertNotIn('r1_coordinator_workspace.css', text)
