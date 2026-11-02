from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from participants.models import Participant
from scheduling.forms import ParticipantCancellationReviewForm
from scheduling.models import ParticipantCancellation, Shift, SupportItem
from scheduling.tests_r1_roster import ControlParser
from workers.models import SupportWorker


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class R1CancellationUITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username='cancellation-ui-admin')
        UserProfile.objects.create(user=cls.admin, role=UserProfile.Role.ADMIN)
        cls.sw = get_user_model().objects.create_user(username='cancellation-ui-sw')
        UserProfile.objects.create(user=cls.sw, role=UserProfile.Role.SUPPORT_WORKER)
        cls.sc = get_user_model().objects.create_user(username='cancellation-ui-sc')
        UserProfile.objects.create(user=cls.sc, role=UserProfile.Role.SUPPORT_COORDINATOR)
        cls.person = Participant.objects.create(first_name='Fictional', last_name='Participant')
        cls.worker = SupportWorker.objects.create(user=cls.sw, first_name='Fictional', last_name='Worker')
        cls.item = SupportItem.objects.create(item_number='R1-CANCEL-UI', name='Fictional support', price_limit=Decimal('100'))
        cls.records = {}
        for i, status in enumerate(ParticipantCancellation.Status.values):
            shift = Shift.objects.create(participant=cls.person, worker=cls.worker,
                service_date=date(2027, 1, 4 + i), start_time=time(9), end_time=time(12),
                planned_hours=Decimal('3'), support_item=cls.item, service_type='community_access',
                status='cancellation_review', created_by=cls.admin)
            cls.records[status] = ParticipantCancellation.objects.create(shift=shift,
                cancellation_type='short_notice', reason='other', details='Complete fictional report.',
                received_at=timezone.make_aware(datetime(2027, 1, 4, 8)),
                previous_shift_status='confirmed', submitted_by=cls.sw, status=status,
                reviewed_by=None if status == 'pending' else cls.admin,
                reviewed_at=None if status == 'pending' else timezone.now(),
                admin_note='' if status == 'pending' else 'Existing fictional review note.')

    def setUp(self):
        self.client.force_login(self.admin)

    def detail(self, status='pending'):
        return self.client.get(reverse('participant_cancellation_detail', args=[self.records[status].pk]))

    def test_two_pages_opt_in_to_scoped_assets_without_menu_changes(self):
        for response in (self.client.get(reverse('participant_cancellation_list')), self.detail()):
            self.assertContains(response, 'class="r1-ui r1-people-form r1-roster-record r1-cancellations"', count=1)
            text = response.content.decode()
            styles = ['css/admin.css', 'css/r1_tokens.css', 'css/r1_admin_people_forms.css',
                      'css/r1_roster_records.css', 'css/r1_admin_cancellations.css', 'css/form_focus.css']
            for path in styles:
                self.assertContains(response, static(path), count=1)
            positions = [text.index(static(path)) for path in styles]
            self.assertEqual(positions, sorted(positions))
            self.assertContains(response, 'aria-label="Admin navigation"', count=2)
            self.assertContains(response, 'class="admin-mobile-header"')
            self.assertContains(response, static('js/admin_nav.js'), count=1)
            self.assertNotContains(response, 'r1_shell.css')
            self.assertNotContains(response, 'preview-guard.js')

    def test_list_keeps_groups_all_columns_and_original_links(self):
        response = self.client.get(reverse('participant_cancellation_list'))
        for text in ('Waiting for review', 'Recently reviewed', 'Pending review', 'Approved for charging', 'Charge waived', 'Rejected'):
            self.assertContains(response, text)
        for label in ('Date', 'Participant', 'Worker', 'Type', 'Status', 'Decision', 'Action'):
            self.assertContains(response, f'data-label="{label}"')
        for record in self.records.values():
            self.assertContains(response, reverse('participant_cancellation_detail', args=[record.pk]))
        self.assertNotContains(response, 'name="status"')

    def test_empty_list_keeps_both_original_explanations(self):
        ParticipantCancellation.objects.all().delete()
        response = self.client.get(reverse('participant_cancellation_list'))
        self.assertContains(response, 'No cancellations need review.')
        self.assertContains(response, 'New participant cancellation reports will appear here.')
        self.assertNotContains(response, 'Recently reviewed')

    def test_review_form_keeps_original_field_and_three_post_destinations(self):
        response = self.detail()
        nodes = ControlParser(response.content.decode()).nodes
        forms = [a for tag, a in nodes if tag == 'form' and a.get('class') == 'service-log-reject-form']
        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0].get('method'), 'post')
        self.assertFalse(ParticipantCancellationReviewForm().fields['admin_note'].required)
        self.assertContains(response, 'name="admin_note"', count=1)
        for action, label in (('approve', 'Approve Charge'), ('waive', 'Waive Charge'), ('reject', 'Reject Report')):
            target = reverse('participant_cancellation_' + action, args=[self.records['pending'].pk])
            self.assertContains(response, f'formaction="{target}"', count=1)
            self.assertContains(response, label)

    def test_review_outcomes_keep_invoice_condition_and_read_only_fields(self):
        for status in ('approved', 'waived', 'rejected'):
            with self.subTest(status=status):
                response = self.detail(status)
                for text in ('Review outcome', 'Decision', 'Admin note', 'Reviewed by', 'Reviewed at', 'Existing fictional review note.'):
                    self.assertContains(response, text)
                self.assertNotContains(response, 'name="admin_note"')
                if status == 'approved':
                    self.assertContains(response, 'Create Invoice')
                    self.assertContains(response, reverse('invoice_create') + '?participant=')
                else:
                    self.assertNotContains(response, 'Create Invoice')

    def test_missing_review_values_keep_original_fallback(self):
        record = self.records['approved']
        record.admin_note = ''
        record.reviewed_by = None
        record.reviewed_at = None
        record.save(update_fields=['admin_note', 'reviewed_by', 'reviewed_at'])
        self.assertContains(self.detail('approved'), '<dd>-</dd>', count=3, html=True)

    def test_long_report_is_not_truncated_and_get_does_not_change_record(self):
        value = 'LongUnbrokenReport' * 50 + '\nComplete final sentence.'
        record = self.records['pending']
        record.details = value
        record.save(update_fields=['details'])
        response = self.detail()
        self.assertContains(response, value)
        record.refresh_from_db()
        self.assertEqual(record.details, value)
        self.assertEqual(record.status, 'pending')

    def test_original_admin_permissions_remain_on_both_pages(self):
        for user in (self.sw, self.sc):
            self.client.force_login(user)
            self.assertEqual(self.detail().status_code, 403)
            self.assertEqual(self.client.get(reverse('participant_cancellation_list')).status_code, 403)

    def test_unrelated_pages_do_not_load_cancellation_style(self):
        for name in ('roster_list', 'roster_planner', 'participant_list'):
            self.assertNotContains(self.client.get(reverse(name)), 'r1_admin_cancellations.css')

    def test_scoped_css_preserves_mobile_labels_and_unframed_review(self):
        path = Path(__file__).resolve().parents[1] / 'static/css/r1_admin_cancellations.css'
        self.assertTrue(path.is_file())
        css = path.read_text()
        for text in ('content:attr(data-label)', 'grid-template-columns:90px minmax(0,1fr)',
                     'width:100%;max-width:none;margin:0;padding:0;border:0', 'min-width:0;width:100%'):
            self.assertIn(text, css)
