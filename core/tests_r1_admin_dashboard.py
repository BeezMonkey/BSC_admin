from pathlib import Path

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class R1AdminDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user('dashboard-ui-admin')
        UserProfile.objects.create(user=cls.admin, role=UserProfile.Role.ADMIN)
        cls.worker = get_user_model().objects.create_user('dashboard-ui-worker')
        UserProfile.objects.create(user=cls.worker, role=UserProfile.Role.SUPPORT_WORKER)
        cls.coordinator = get_user_model().objects.create_user('dashboard-ui-sc')
        UserProfile.objects.create(user=cls.coordinator, role=UserProfile.Role.SUPPORT_COORDINATOR)

    def dashboard(self):
        self.client.force_login(self.admin)
        return self.client.get(reverse('admin_dashboard'))

    def test_dashboard_opts_in_independently_and_keeps_shared_focus_last(self):
        response = self.dashboard()
        self.assertContains(response, 'class="r1-ui r1-admin-dashboard"', count=1)
        text = response.content.decode()
        styles = ('css/admin.css', 'css/r1_tokens.css', 'css/r1_admin_dashboard.css', 'css/form_focus.css')
        for path in styles:
            self.assertContains(response, static(path), count=1)
        positions = [text.index(static(path)) for path in styles]
        self.assertEqual(positions, sorted(positions))
        self.assertNotContains(response, 'r1_shell.css')

    def test_original_four_counts_six_workflow_steps_and_six_actions_remain(self):
        response = self.dashboard()
        for key, count in (('operations_overview', 4), ('workflow_checklist', 6), ('module_links', 6)):
            self.assertEqual(len(response.context[key]), count)
        for item in response.context['operations_overview']:
            self.assertContains(response, item['label'])
            self.assertContains(response, item['description'])
        for item in response.context['workflow_checklist']:
            self.assertContains(response, item['label'])
            self.assertContains(response, item['detail'])
            self.assertContains(response, item['description'])

    def test_every_existing_dashboard_destination_and_query_is_retained(self):
        response = self.dashboard()
        for key in ('operations_overview', 'priority_queue', 'workflow_checklist', 'module_links'):
            for item in response.context[key]:
                target = reverse(item['url_name'])
                if item.get('query'):
                    target += '?' + item['query']
                self.assertContains(response, f'href="{target}"')

    def test_empty_queue_keeps_original_message_and_does_not_invent_tasks(self):
        response = self.dashboard()
        self.assertEqual(response.context['priority_queue'], [])
        self.assertContains(response, 'No outstanding admin actions.')
        self.assertContains(response, 'New roster, service log, and invoice tasks are listed here.')

    def test_navigation_and_original_post_logout_are_retained(self):
        response = self.dashboard()
        self.assertContains(response, f'class="sidebar-link active" href="{reverse("admin_dashboard")}"')
        self.assertContains(response, 'aria-label="Admin navigation"', count=2)
        self.assertContains(response, 'class="admin-mobile-header"')
        self.assertContains(response, static('js/admin_nav.js'), count=1)
        self.assertContains(response, f'method="post" action="{reverse("logout")}"', count=2)
        self.assertNotContains(response, 'r1_login.css')

    def test_other_page_families_do_not_load_dashboard_css(self):
        request = RequestFactory().get('/')
        request.user = self.admin
        for template in ('admin_base.html', 'worker_base.html', 'coordinator_base.html', 'accounts/login.html'):
            with self.subTest(template=template):
                text = render_to_string(template, {'request': request})
                self.assertNotIn('r1_admin_dashboard.css', text)
                self.assertNotIn('r1-admin-dashboard', text)

    def test_existing_access_is_unchanged_for_sw_and_sc(self):
        for user in (self.worker, self.coordinator):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 403)
        self.client.logout()
        self.assertRedirects(self.client.get(reverse('admin_dashboard')), reverse('login') + '?next=' + reverse('admin_dashboard'))


class R1AdminDashboardStyleTests(SimpleTestCase):
    def test_dashboard_styles_are_scoped_and_responsive_without_login_rules(self):
        path = Path(__file__).resolve().parents[1] / 'static/css/r1_admin_dashboard.css'
        self.assertTrue(path.is_file())
        css = path.read_text()
        for token in ('.r1-admin-dashboard', 'min-height:96px', 'repeat(4,minmax(0,1fr))', 'repeat(2,minmax(0,1fr))', '@media(max-width:1100px)', '@media(max-width:760px)', 'min-height:44px'):
            self.assertIn(token, css)
        for token in ('.login-card', '.login-page', ':root', 'body {', '.sidebar', 'overflow-y:hidden'):
            self.assertNotIn(token, css)
