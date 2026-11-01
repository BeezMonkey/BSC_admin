from datetime import date, time
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from participants.models import Participant
from scheduling.models import ParticipantCancellation, Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class ControlParser(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.nodes = []
        self.roster_depth = None
        self.depth = 0
        self.dialog_roots = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.nodes.append((tag, attrs))
        if tag == 'div':
            self.depth += 1
            if 'r1-admin-roster' in attrs.get('class', '').split():
                self.roster_depth = self.depth
            if attrs.get('id') == 'shift-modal-root':
                self.dialog_roots.append(self.roster_depth is not None)
        if tag == 'dialog' and attrs.get('id') == 'planner-billing-drawer':
            self.dialog_roots.append(self.roster_depth is not None)

    def handle_endtag(self, tag):
        if tag == 'div':
            if self.depth == self.roster_depth:
                self.roster_depth = None
            self.depth -= 1


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class R1RosterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for role in (UserProfile.Role.ADMIN, UserProfile.Role.SUPPORT_WORKER, UserProfile.Role.SUPPORT_COORDINATOR):
            user = get_user_model().objects.create_user(username=f'roster-ui-{role}')
            UserProfile.objects.create(user=user, role=role)
            cls.users[role] = user
        cls.admin = cls.users[UserProfile.Role.ADMIN]
        cls.person = Participant.objects.create(first_name='Fictional', last_name='Participant')
        cls.worker = SupportWorker.objects.create(first_name='Fictional', last_name='Worker',
            email='roster-ui@example.invalid', user=cls.users[UserProfile.Role.SUPPORT_WORKER])
        cls.item = SupportItem.objects.create(item_number='ROSTER-UI-ONLY', name='Fictional support', price_limit=Decimal('100'))
        cls.shifts = {}
        for index, key in enumerate(('missing', 'review', 'rejected', 'cancelreview', 'check', 'draft')):
            shift = Shift.objects.create(participant=cls.person, worker=cls.worker,
                service_date=date(2020, 1, 6 + index), start_time=time(9), end_time=time(12),
                planned_hours=Decimal('3'), support_item=cls.item, service_type='personal_care',
                status='draft' if key == 'draft' else 'confirmed', created_by=cls.admin)
            cls.shifts[key] = shift
            if key in ('review', 'rejected', 'check'):
                ServiceLog.objects.create_from_shift(shift, actual_start_time=time(9), actual_end_time=time(12),
                    actual_hours=Decimal('3'), case_notes='FICTIONAL UI fixture.',
                    status={'review': 'submitted', 'rejected': 'rejected', 'check': 'invoiced'}[key])
            if key == 'cancelreview':
                ParticipantCancellation.objects.create(shift=shift, cancellation_type='short_notice',
                    reason='other', details='FICTIONAL UI fixture.', received_at=timezone.now(),
                    previous_shift_status='confirmed', submitted_by=cls.admin, status='pending')

    def setUp(self):
        self.client.force_login(self.admin)
        self.params = {'date_from': '2020-01-06', 'date_to': '2020-01-12'}

    def page(self, name='roster_list', **extra):
        return self.client.get(reverse(name), {**self.params, **extra})

    def test_both_pages_opt_in_without_changing_navigation_theme(self):
        for name in ('roster_list', 'roster_planner'):
            response = self.page(name)
            self.assertContains(response, 'class="r1-ui r1-admin-roster"', count=1)
            text = response.content.decode()
            paths = ['css/admin.css', 'css/r1_tokens.css', 'css/r1_admin_roster.css', 'css/form_focus.css']
            for path in paths:
                self.assertContains(response, static(path), count=1)
            self.assertEqual([text.index(static(p)) for p in paths], sorted(text.index(static(p)) for p in paths))
            self.assertNotContains(response, 'r1_shell.css')

    def test_list_has_eight_mobile_fields_and_original_inline_actions(self):
        response = self.page()
        for label in ('Date', 'Time', 'Participant', 'Worker', 'Service', 'Status', 'Next action', 'Actions'):
            self.assertContains(response, f'data-label="{label}"', count=6)
        self.assertContains(response, 'class="roster-inline-actions"', count=6)
        for shift in self.shifts.values():
            self.assertContains(response, reverse('shift_detail', args=[shift.pk]))
            self.assertContains(response, reverse('shift_edit', args=[shift.pk]))

    def test_original_named_date_fields_and_unnamed_calendar_proxies(self):
        for name in ('roster_list', 'roster_planner'):
            response = self.page(name)
            nodes = ControlParser(response.content.decode()).nodes
            for field in ('date_from', 'date_to'):
                matches = [a for tag, a in nodes if tag == 'input' and a.get('name') == field]
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0]['type'], 'date')
                self.assertEqual(matches[0]['value'], self.params[field])
            proxies = [a for tag, a in nodes if tag == 'input' and 'data-invoice-date-proxy' in a]
            self.assertEqual(len(proxies), 2)
            self.assertTrue(all('name' not in a for a in proxies))
            self.assertContains(response, 'data-roster-filters', count=1)

    def test_planner_keeps_original_scripts_once_and_only_adds_date_adapter(self):
        response = self.page('roster_planner', billing='1')
        for name in ('planner_billing.js', 'date_time_picker.js', 'support_item_picker.js', 'shift_modal.js', 'admin_nav.js', 'r1_roster_filters.js'):
            self.assertContains(response, static('js/' + name), count=1)
        self.assertNotContains(response, 'preview-guard.js')
        self.assertNotContains(response, 'offline-billing.js')

    def test_all_three_views_keep_existing_fields_and_original_action_conditions(self):
        for view in ('daily', 'participant', 'worker'):
            response = self.page('roster_planner', view=view)
            self.assertEqual(response.context['view_mode'], view)
            self.assertEqual(len(response.context['shifts']), 6)
            self.assertEqual(len(response.context['planner_days']), 7)
            for text in ('Daily overview', 'Participant view', 'Worker view', 'Billing check', 'New Shift', 'Recurring Shift'):
                self.assertContains(response, text)
            self.assertContains(response, 'aria-label="Copy shift from')
            self.assertContains(response, 'aria-label="View shift"')
            self.assertContains(response, 'data-delete-participant=')
            self.assertContains(response, 'js-shift-paste-target')

    def test_billing_is_off_by_default_and_attention_keeps_all_five_existing_states(self):
        off = self.page('roster_planner')
        self.assertNotContains(off, 'data-planner-billing-url=')
        for view in ('daily', 'participant', 'worker'):
            response = self.page('roster_planner', view=view, billing='1', billing_status='attention')
            self.assertEqual({s.billing_summary['key'] for s in response.context['shifts']},
                             {'missing', 'review', 'rejected', 'cancelreview', 'check'})
            for label in ('Missing service log', 'Log awaiting review', 'Log rejected', 'Cancellation review', 'Check billing records'):
                self.assertContains(response, label)
            self.assertContains(response, 'data-planner-billing-url=', count=5)
        self.assertEqual(ServiceLog.objects.count(), 3)

    def test_original_dialog_roots_are_outside_content_style_scope(self):
        response = self.page('roster_planner', billing='1')
        self.assertEqual(ControlParser(response.content.decode()).dialog_roots, [False, False])

    def test_draft_publish_original_post_and_filter_fields_remain(self):
        response = self.page(status='draft')
        self.assertEqual(response.context['draft_publish_count'], 1)
        self.assertContains(response, 'Publish 1 draft shift')
        self.assertContains(response, f'method="post" action="{reverse("shift_bulk_publish")}"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        for name, value in (('status', 'draft'), *self.params.items()):
            self.assertContains(response, f'type="hidden" name="{name}" value="{value}"')
        self.assertNotContains(self.page(), 'Publish 1 draft shift')
        self.shifts['draft'].refresh_from_db()
        self.assertEqual(self.shifts['draft'].status, Shift.Status.DRAFT)

    def test_original_filtered_empty_copy_is_kept(self):
        response = self.page(participant='NO-MATCH-UI-ONLY')
        self.assertContains(response, 'No shifts match the current filters.')
        self.assertContains(response, 'Clear the filters to review all scheduled work.')
        self.assertContains(response, 'Clear filters')

    def test_shared_navigation_and_logout_are_not_replaced(self):
        for name in ('roster_list', 'roster_planner'):
            response = self.page(name)
            self.assertContains(response, 'aria-label="Admin navigation"', count=2)
            self.assertContains(response, 'class="admin-mobile-header"')
            self.assertContains(response, 'class="sidebar-link active" href="' + reverse('roster_list') + '"')
            self.assertContains(response, f'method="post" action="{reverse("logout")}"', count=2)

    def test_sw_sc_and_anonymous_access_remain_restricted(self):
        for role in (UserProfile.Role.SUPPORT_WORKER, UserProfile.Role.SUPPORT_COORDINATOR):
            self.client.force_login(self.users[role])
            for name in ('roster_list', 'roster_planner'):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        self.client.logout()
        for name in ('roster_list', 'roster_planner'):
            self.assertRedirects(self.client.get(reverse(name)), reverse('login') + '?next=' + reverse(name))

    def test_base_and_other_page_families_do_not_load_roster_styles(self):
        request = RequestFactory().get('/')
        request.user = self.admin
        for template in ('admin_base.html', 'worker_base.html', 'coordinator_base.html', 'accounts/login.html'):
            text = render_to_string(template, {'request': request})
            self.assertNotIn('r1_admin_roster.css', text)
            self.assertNotIn('r1_roster_filters.js', text)


class R1RosterStyleTests(SimpleTestCase):
    def test_shift_card_typography_matches_main_without_resizing_other_controls(self):
        css = (Path(__file__).resolve().parents[1] / 'static/css/r1_admin_roster.css').read_text()
        expected = {
            '.planner-shift-time': ('0.72rem', '1.3', '600'),
            '.planner-shift-primary': ('0.72rem', '1.3', '500'),
            '.planner-shift-meta': ('0.72rem', '1.3', '400'),
            '.status-pill': ('0.69rem', '1.25', '600'),
            '.planner-billing-link': ('11px', '1.35', '500'),
            '.planner-conflict-tag': ('0.66rem', '1.1', '600'),
            '.planner-multi-worker-tag': ('0.66rem', '1.1', '600'),
            '.source-pill': ('11px', '1', '600'),
        }
        for suffix, (size, height, weight) in expected.items():
            selector = '[data-admin-theme] .r1-admin-roster .planner-shift-tile ' + suffix + ' {'
            with self.subTest(selector=suffix):
                self.assertIn(selector, css)
                rule = css.split(selector, 1)[1].split('}', 1)[0]
                for declaration in (f'font-size:{size}', f'line-height:{height}', f'font-weight:{weight}'):
                    self.assertIn(declaration, rule)
                for property_name in ('padding:', 'margin:', 'width:', 'height:', 'color:', 'background:'):
                    self.assertNotIn(property_name, rule.replace('line-height:', ''))

    def test_existing_copy_source_and_quick_date_active_styles_are_preserved(self):
        css = (Path(__file__).resolve().parents[1] / 'static/css/r1_admin_roster.css').read_text()
        for selector in (
            '[data-admin-theme] .r1-admin-roster .planner-shift-action-active {',
            '[data-admin-theme] .r1-admin-roster .planner-shift-action-active:hover,',
            '[data-admin-theme] .r1-admin-roster .planner-shift-action-active:focus {',
            '[data-admin-theme] .r1-admin-roster .quick-filter-row .button.active {',
        ):
            self.assertIn(selector, css)
        for token in ('var(--planner-copy-border)', 'var(--planner-copy-ink)',
                      'var(--planner-copy-bg)', 'var(--planner-copy-bg-hover)'):
            self.assertIn(token, css)

    def test_styles_are_content_scoped_and_keep_hidden_paste_v02_warning_and_scroll(self):
        path = Path(__file__).resolve().parents[1] / 'static/css/r1_admin_roster.css'
        self.assertTrue(path.is_file())
        css = path.read_text()
        for value in ('.r1-admin-roster', '.roster-inline-actions', 'flex-wrap:nowrap',
                      'table-layout:fixed', 'border-radius:6px', 'var(--r1-warning)',
                      'var(--r1-warning-soft)', '.planner-paste-shift-hidden',
                      'overflow:auto', '@media(max-width:760px)', 'min-height:44px',
                      'appearance:base-select', 'invoice-calendar'):
            self.assertIn(value, css)
        for value in (':root', '.sidebar', '.login-card', 'overflow-y:hidden'):
            self.assertNotIn(value, css)

    def test_date_adapter_keeps_native_control_and_no_network_or_submission_hooks(self):
        path = Path(__file__).resolve().parents[1] / 'static/js/r1_roster_filters.js'
        self.assertTrue(path.is_file())
        script = path.read_text()
        self.assertIn('.r1-admin-roster [data-roster-filters]', script)
        self.assertIn('native.value = proxy.value', script)
        self.assertIn('native.validity.valid', script)
        self.assertIn('desktop.matches', script)
        for value in ('fetch(', 'requestSubmit(', '.submit(', 'localStorage', 'billing_status'):
            self.assertNotIn(value, script)
