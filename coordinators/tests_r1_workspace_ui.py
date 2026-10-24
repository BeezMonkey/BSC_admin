from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.templatetags.static import static
from django.urls import reverse

from core.models import AuditLog
from documents.tests_r1_ui import Page
from invoices.models import Invoice, InvoiceLine
from participants.models import Participant
from scheduling.models import SupportItem

from .models import CoordinationLog, ParticipantCoordinatorAssignment
from .tests import create_coordinator


class CoordinatorWorkspaceUITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sc = create_coordinator('workspace-sc')
        cls.person = Participant.objects.create(
            first_name='Fictional', last_name='Participant', ndis_number='QA-NOT-REAL-001',
            phone='0491570006', email='person@example.invalid', address_line_1='12 Example Street',
            suburb='West End', state='QLD', postcode='4101', internal_notes='PRIVATE WORKSPACE NOTE',
        )
        ParticipantCoordinatorAssignment.objects.create(participant=cls.person, coordinator=cls.sc, start_date=date(2026, 1, 1))
        cls.logs = {}
        for status in ['submitted', 'approved', 'rejected', 'invoiced']:
            cls.logs[status] = CoordinationLog.objects.create(
                participant=cls.person, coordinator=cls.sc, service_date=date(2026, 10, 12),
                actual_hours=Decimal('1.25'), status=status, case_notes='Original fictional coordination notes.',
            )

    def setUp(self):
        self.client.force_login(self.sc.user)

    def get(self, name):
        response = self.client.get(reverse(name))
        self.assertEqual(response.status_code, 200)
        return response

    def test_three_workspace_routes_opt_into_only_new_assets(self):
        for name in ['coordinator_dashboard', 'coordinator_participant_list', 'coordinator_log_list']:
            with self.subTest(route=name):
                response = self.get(name)
                self.assertContains(response, 'r1-coordinator-workspace')
                self.assertContains(response, static('css/r1_coordinator_workspace.css'), count=1)
                self.assertNotContains(response, static('css/r1_coordinator_details.css'))

    def test_dashboard_original_count_and_two_cards_preserved(self):
        page = Page(self.get('coordinator_dashboard')).root
        cards = [n for n in page.find('section') if n.has_class('coordinator-dashboard-card')]
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].find('p')[0].text, '1 active participant assigned to you.')
        self.assertEqual(cards[1].find('p')[0].text, 'Review your submitted support coordination records.')
        self.assertFalse(cards[0].find('strong'))
        self.assertNotContains(self.get('coordinator_dashboard'), 'participant-count-value')
        self.assertContains(self.get('coordinator_dashboard'), 'r1-workspace-dashboard')

    def test_dashboard_important_original_destinations_preserved(self):
        response = self.get('coordinator_dashboard')
        for name in ['coordinator_participant_list', 'coordinator_log_list', 'coordinator_log_create']:
            self.assertContains(response, reverse(name))
        self.assertNotContains(response, 'Search')

    def test_participant_table_has_original_information_and_view_button(self):
        response = self.get('coordinator_participant_list')
        for text in [self.person.display_name, self.person.ndis_number, self.person.phone, self.person.email,
                     self.person.address_line_1, 'West End QLD 4101']:
            self.assertContains(response, text)
        page = Page(response).root
        self.assertEqual([n.text for n in page.find('th')], ['Participant', 'Contact', 'Address', 'Actions'])
        names = [n for n in page.find('a') if n.has_class('r1-workspace-name')]
        self.assertEqual(len(names), 1)
        url = reverse('coordinator_participant_detail', args=[self.person.pk])
        self.assertEqual(names[0].attrs['href'], url)
        view = next(n for n in page.find('a', href=url) if n.text == 'View')
        self.assertTrue(view.has_class('button'))
        self.assertNotContains(response, self.person.internal_notes)

    def test_participant_fallbacks_and_empty_state_preserved(self):
        for field in ['phone', 'email', 'ndis_number', 'address_line_1']:
            setattr(self.person, field, '')
        self.person.save()
        response = self.get('coordinator_participant_list')
        for text in ['No phone', 'No email', 'No address', 'not recorded']:
            self.assertContains(response, text)
        ParticipantCoordinatorAssignment.objects.all().delete()
        self.assertContains(self.get('coordinator_participant_list'), 'No assigned participants yet.')
        self.assertContains(self.get('coordinator_dashboard'), '0 active participants assigned to you.')

    def test_log_table_preserves_seven_fields_and_original_action_classes(self):
        response = self.get('coordinator_log_list')
        page = Page(response).root
        self.assertEqual([n.text for n in page.find('th')], ['Date', 'Participant', 'Type', 'Hours', 'Status', 'Notes', 'Actions'])
        self.assertEqual(len(page.find('a', **{'class': 'sc-log-action sc-log-action--view'})), 4)
        self.assertEqual(len(page.find('a', **{'class': 'sc-log-action sc-log-action--edit'})), 3)
        for log in self.logs.values():
            self.assertContains(response, reverse('coordinator_log_detail', args=[log.pk]))
        self.assertContains(response, 'r1-workspace-table')

    def test_log_edit_links_keep_all_status_eligibility(self):
        response = self.get('coordinator_log_list')
        for status, log in self.logs.items():
            url = reverse('coordinator_log_edit', args=[log.pk])
            if status == 'invoiced':
                self.assertNotContains(response, url)
            else:
                self.assertContains(response, url)

    def test_approved_log_with_linked_invoice_remains_uneditable(self):
        log = self.logs['approved']
        item = SupportItem.objects.create(item_number='QA-WORKSPACE', name='Fictional coordination', unit=SupportItem.Unit.HOUR, price_limit=Decimal('100.00'))
        invoice = Invoice.objects.create(participant=self.person, period_start=log.service_date,
                                        period_end=log.service_date, created_by=self.sc.user, invoice_type=Invoice.InvoiceType.SUPPORT_COORDINATION)
        InvoiceLine.objects.create_from_coordination_log(invoice, log, item)
        response = self.get('coordinator_log_list')
        self.assertNotContains(response, reverse('coordinator_log_edit', args=[log.pk]))
        self.assertContains(response, reverse('coordinator_log_detail', args=[log.pk]))

    def test_log_notes_keep_existing_twelve_word_summary(self):
        log = self.logs['submitted']
        log.case_notes = ' '.join(f'word{n}' for n in range(1, 21))
        log.save(update_fields=['case_notes'])
        response = self.get('coordinator_log_list')
        self.assertContains(response, 'word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12')
        self.assertNotContains(response, 'word13')

    def test_empty_log_table_preserves_copy_and_seven_columns(self):
        CoordinationLog.objects.all().delete()
        response = self.get('coordinator_log_list')
        self.assertContains(response, 'No coordination logs submitted yet.')
        self.assertContains(response, 'colspan="7"')

    def test_long_values_and_html_are_escaped_without_new_filters(self):
        self.person.first_name = '<script>alert("no")</script>'
        self.person.last_name = 'Long' * 35
        self.person.email = 'long.' + 'x' * 100 + '@example.invalid'
        self.person.save()
        response = self.get('coordinator_participant_list')
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert("no")</script>')
        self.assertContains(response, self.person.email)
        self.assertTrue(all(n.attrs.get('type') == 'hidden' for n in Page(response).root.find('input')))

    def test_gets_preserve_records_and_original_logout_csrf(self):
        before = (list(Participant.objects.values()), list(CoordinationLog.objects.values()), AuditLog.objects.count())
        for name in ['coordinator_dashboard', 'coordinator_participant_list', 'coordinator_log_list']:
            page = Page(self.get(name)).root
            for form in page.find('form'):
                self.assertEqual(form.attrs.get('method'), 'post')
                self.assertEqual(form.attrs.get('action'), reverse('logout'))
                self.assertTrue(form.find('input', name='csrfmiddlewaretoken'))
        self.assertEqual(before, (list(Participant.objects.values()), list(CoordinationLog.objects.values()), AuditLog.objects.count()))

    def test_accepted_pages_and_log_forms_details_do_not_load_workspace_assets(self):
        routes = [reverse('coordinator_account'), reverse('coordinator_participant_detail', args=[self.person.pk]),
                  reverse('coordinator_log_create'), reverse('coordinator_log_detail', args=[self.logs['submitted'].pk]),
                  reverse('coordinator_log_edit', args=[self.logs['submitted'].pk])]
        for url in routes:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'r1-coordinator-workspace')
            self.assertNotContains(response, static('css/r1_coordinator_workspace.css'))

    def test_anonymous_user_cannot_access_workspace_routes(self):
        self.client.logout()
        for name in ['coordinator_dashboard', 'coordinator_participant_list', 'coordinator_log_list']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('login'), response.url)


class CoordinatorWorkspaceStyleTests(SimpleTestCase):
    def test_legacy_log_width_status_and_secondary_border_are_overridden_locally(self):
        path = Path(settings.BASE_DIR) / 'static/css/r1_coordinator_workspace.css'
        self.assertTrue(path.is_file())
        css = path.read_text(encoding='utf-8')
        self.assertIn('[data-portal-theme].r1-coordinator-workspace .sc-log-list .coordinator-log-table { min-width:0; width:100%; }', css)
        self.assertIn('.app-shell.r1-ui.r1-coordinator-workspace .status-pill.status-approved', css)
        self.assertIn('.app-shell.r1-ui.r1-coordinator-workspace .status-pill.status-rejected', css)
        self.assertIn('border-width:1px;', css)
        self.assertIn('gap:8px; padding:7px 12px; border-width:1px;', css)
        self.assertIn('.app-shell.r1-ui.r1-coordinator-workspace .button { padding:7px 12px; }', css)
        self.assertIn('height:auto; min-height:0;', css)
        self.assertIn('justify-self:start;', css)

    def test_scoped_style_keeps_confirmed_layout_and_description_weight_only(self):
        path = Path(settings.BASE_DIR) / 'static/css/r1_coordinator_workspace.css'
        self.assertTrue(path.is_file(), 'Dedicated three-page stylesheet must exist')
        css = path.read_text(encoding='utf-8')
        for text in ['.r1-coordinator-workspace', 'var(--r1-surface)', 'var(--r1-border)', 'var(--r1-text)',
                     'border-radius:8px', 'border-radius:6px', 'font-weight:500', '@media (max-width:980px)',
                     'overflow-wrap:anywhere', '.r1-workspace-dashboard', '.r1-workspace-table']:
            self.assertIn(text, css)
        self.assertNotIn('font-size:32px', css)
        self.assertNotIn('line-clamp', css)
