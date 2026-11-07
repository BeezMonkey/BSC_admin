from html.parser import HTMLParser
from pathlib import Path

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from coordinators.models import SupportCoordinator
from participants.models import Participant
from workers.models import SupportWorker


class NavigationLinks(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'sidebar-link' in attrs.get('class', '').split():
            self.links.append(attrs['href'])


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class UnifiedAdminNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user('navigation-fictional-admin')
        UserProfile.objects.create(user=cls.admin, role=UserProfile.Role.ADMIN)
        cls.participant = Participant.objects.create(first_name='Fictional', last_name='Participant')
        worker_user = get_user_model().objects.create_user('navigation-fictional-worker')
        coordinator_user = get_user_model().objects.create_user('navigation-fictional-sc')
        cls.worker = SupportWorker.objects.create(user=worker_user, first_name='Fictional', last_name='Worker')
        cls.coordinator = SupportCoordinator.objects.create(user=coordinator_user, first_name='Fictional', last_name='Coordinator')

    def test_all_admin_families_share_navigation_without_changing_routes(self):
        self.client.force_login(self.admin)
        names = ('admin_dashboard', 'participant_list', 'worker_list', 'coordinator_list',
                 'participant_create', 'worker_create', 'coordinator_create', 'roster_list',
                 'roster_planner', 'shift_create', 'recurring_shift_create', 'service_log_list',
                 'coordination_log_list', 'invoice_placeholder', 'weekly_billing', 'invoice_create', 'invoice_settings',
                 'support_coordination_invoice_list', 'support_coordination_invoice_create',
                 'support_item_list', 'support_item_create', 'participant_cancellation_list', 'audit_log_list')
        targets = [(name, ()) for name in names]
        targets += [(name, (record.pk,)) for record, pair in (
            (self.participant, ('participant_detail', 'participant_edit')),
            (self.worker, ('worker_detail', 'worker_edit')),
            (self.coordinator, ('coordinator_detail', 'coordinator_edit')),
        ) for name in pair]
        targets += [('participant_assign_worker', (self.participant.pk,)),
                    ('coordinator_assign_participant', (self.coordinator.pk,))]
        expected = [reverse(name) for name in (
            'admin_dashboard', 'participant_list', 'worker_list', 'roster_list', 'service_log_list',
            'participant_cancellation_list', 'invoice_placeholder', 'weekly_billing', 'support_item_list',
            'coordinator_list', 'coordination_log_list', 'support_coordination_invoice_list', 'audit_log_list')]
        for name, args in targets:
            with self.subTest(page=name):
                response = self.client.get(reverse(name, args=args))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-admin-theme', count=1)
                self.assertContains(response, static('css/admin_navigation.css'), count=1)
                html = response.content.decode()
                self.assertLess(html.index(static('css/admin.css')), html.index(static('css/admin_navigation.css')))
                self.assertLess(html.index(static('css/admin_navigation.css')), html.index(static('css/form_focus.css')))
                self.assertEqual(NavigationLinks(html).links, expected * 2)
                self.assertContains(response, static('js/admin_nav.js'), count=1)
                self.assertContains(response, f'method="post" action="{reverse("logout")}"')

    def test_navigation_does_not_opt_plain_content_into_r1_shell(self):
        self.client.force_login(self.admin)
        for name in ('admin_dashboard', 'participant_create', 'roster_planner', 'support_item_list', 'audit_log_list'):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, 'class="app-shell" data-admin-theme>')
                self.assertNotContains(response, 'css/r1_shell.css')

    def test_other_role_and_login_bases_do_not_receive_admin_navigation(self):
        request = RequestFactory().get('/')
        request.user = self.admin
        for template in ('worker_base.html', 'coordinator_base.html', 'accounts/login.html'):
            with self.subTest(template=template):
                html = render_to_string(template, {'request': request})
                self.assertNotIn('admin_navigation.css', html)

    def test_admin_access_remains_restricted(self):
        for role in (UserProfile.Role.SUPPORT_WORKER, UserProfile.Role.SUPPORT_COORDINATOR):
            user = get_user_model().objects.create_user('navigation-' + role)
            UserProfile.objects.create(user=user, role=role)
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 403)


class UnifiedAdminNavigationStyleTests(SimpleTestCase):
    def test_styles_are_navigation_scoped_with_existing_icons_and_mobile_targets(self):
        root = Path(__file__).resolve().parents[1]
        path = root / 'static/css/admin_navigation.css'
        self.assertTrue(path.is_file())
        css = path.read_text()
        for token in ('html .app-shell[data-admin-theme]', '212px minmax(0, 1fr)', '#f0ebff',
                      '@media (max-width: 760px)', 'min-height: 44px', '::before'):
            self.assertIn(token, css)
        for icon in ('admin-dashboard', 'admin-users', 'admin-calendar', 'admin-file',
                     'admin-receipt', 'admin-layers', 'admin-shield'):
            self.assertIn(f'{icon}.svg', css)
            self.assertTrue((root / f'static/img/r1/icons/{icon}.svg').is_file())
        for token in ('.content', '.topbar', '.page-header', '.card', '.field', '.button',
                      'input', 'textarea', ':root', '--brand:', '--ink:', '--r1-'):
            self.assertNotIn(token, css)
