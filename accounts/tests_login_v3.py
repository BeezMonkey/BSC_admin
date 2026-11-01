from html.parser import HTMLParser
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.templatetags.static import static
from django.urls import reverse

from .models import UserProfile
from .views import BSCLoginView, get_login_portal_context


class Markup(HTMLParser):
    def __init__(self, response):
        super().__init__()
        self.nodes = []
        self.feed(response.content.decode())

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))

    def one(self, tag, **attrs):
        return next(node for kind, node in self.nodes if kind == tag and all(node.get(k) == v for k, v in attrs.items()))


@override_settings(ALLOWED_HOSTS=['testserver', 'admin.bscare.com.au', 'sw.bscare.com.au', 'sc.bscare.com.au'])
class LoginV3MarkupTests(TestCase):
    def test_three_host_variants_use_static_badges_and_exact_v3_copy(self):
        for host, badge, title in (
            ('admin.bscare.com.au', 'ADMIN', 'Administrator'),
            ('sw.bscare.com.au', 'SW', 'Support Worker'),
            ('sc.bscare.com.au', 'SC', 'Support Coordinator'),
        ):
            with self.subTest(host=host):
                response = self.client.get(reverse('login'), HTTP_HOST=host)
                self.assertContains(response, f'<h1>{title}</h1>', html=True)
                self.assertContains(response, f'<span class="v3-badge" data-role="{badge}">{badge}</span>', html=True)
                self.assertContains(response, 'Sign in to your workspace.')
                self.assertContains(response, 'NDIS workspace')
                self.assertContains(response, '>Login</button>')
                self.assertNotContains(response, 'Portal')
                self.assertFalse(any(tag in ('a', 'select') for tag, _ in Markup(response).nodes))

    def test_generic_host_keeps_existing_generic_identity(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, '<h1>NDIS Admin System</h1>', html=True)
        self.assertNotContains(response, 'class="v3-badge"')
        self.assertContains(response, 'class="login-page r1-ui login-v3"')

    def test_original_field_contract_and_only_username_placeholder(self):
        response = self.client.get(reverse('login'))
        markup = Markup(response)
        username = markup.one('input', name='username')
        for key, value in {'type': 'text', 'id': 'id_username', 'autocapitalize': 'none', 'autocomplete': 'username', 'maxlength': '150', 'placeholder': 'Enter your username'}.items():
            self.assertEqual(username[key], value)
        self.assertIn('required', username)
        self.assertIn('autofocus', username)
        password = markup.one('input', name='password')
        self.assertEqual(password['type'], 'password')
        self.assertEqual(password['id'], 'id_password')
        self.assertEqual(password['autocomplete'], 'current-password')
        self.assertIn('required', password)
        self.assertNotIn('placeholder', password)
        self.assertEqual([a['name'] for t, a in markup.nodes if t == 'input'], ['csrfmiddlewaretoken', 'username', 'password'])

    def test_current_url_post_and_csrf_are_preserved(self):
        response = self.client.get(reverse('login') + '?next=/sc/dashboard/')
        markup = Markup(response)
        self.assertEqual(markup.one('form')['method'], 'post')
        self.assertNotIn('action', markup.one('form'))
        self.assertTrue(markup.one('input', name='csrfmiddlewaretoken')['value'])
        self.assertEqual(len([1 for t, _ in markup.nodes if t == 'form']), 1)

    def test_original_assets_and_login_only_styles_are_ordered(self):
        response = self.client.get(reverse('login'))
        content = response.content.decode()
        for name in ('css/r1_tokens.css', 'css/r1_login.css', 'css/form_focus.css'):
            self.assertContains(response, static(name), count=1)
        self.assertLess(content.index(static('css/r1_tokens.css')), content.index(static('css/r1_login.css')))
        self.assertLess(content.index(static('css/r1_login.css')), content.index(static('css/form_focus.css')))
        self.assertContains(response, static('img/bsc-logo.png'), count=2)
        self.assertContains(response, 'class="v3-watermark-layer" aria-hidden="true"')
        for name in ('r1_shell.css', 'admin.css', 'portal.css', '<script', 'remember', 'SSO'):
            self.assertNotContains(response, name)

    def test_invalid_post_keeps_generic_error_and_never_echoes_password(self):
        response = self.client.post(reverse('login'), {'username': 'fictional.invalid', 'password': 'fictional-private-password'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password.', count=1)
        self.assertContains(response, 'id="login-error" role="alert"')
        self.assertEqual(Markup(response).one('form')['aria-describedby'], 'login-error')
        self.assertEqual(Markup(response).one('input', name='username')['value'], 'fictional.invalid')
        self.assertNotContains(response, 'fictional-private-password')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_required_field_errors_still_come_from_authentication_form(self):
        response = self.client.post(reverse('login'), {'username': '', 'password': ''})
        self.assertIsInstance(response.context['form'], AuthenticationForm)
        self.assertEqual(set(response.context['form'].errors), {'username', 'password'})
        self.assertContains(response, 'Invalid username or password.')

    def test_login_view_keeps_inherited_authentication_form(self):
        self.assertIs(BSCLoginView().get_form_class(), AuthenticationForm)

    def test_existing_hostname_normalization_is_preserved(self):
        self.assertEqual(get_login_portal_context('SW.BSCARE.COM.AU:443')['portal_badge'], 'SW')
        self.assertEqual(get_login_portal_context('localhost:8000')['portal_name'], 'NDIS Admin System')


class LoginV3StylesTests(SimpleTestCase):
    def test_login_styles_keep_original_font_watermark_and_natural_height(self):
        css = (Path(__file__).resolve().parents[1] / 'static/css/r1_login.css').read_text()
        for expected in ('../fonts/inter/InterVariable.woff2', '.login-v3', 'height: 44px', 'opacity: .04', 'pointer-events: none', 'aspect-ratio: 432 / 418', 'min-height: 100svh'):
            self.assertIn(expected, css)
        self.assertNotIn('height: 100vh', css.replace('min-height: 100vh', ''))
        self.assertNotIn('outline: none', css)


@override_settings(ALLOWED_HOSTS=['testserver', 'admin.bscare.com.au', 'sw.bscare.com.au', 'sc.bscare.com.au'])
class LoginV3AuthenticationContractTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('fictional-login-worker', password='fictional-test-password')
        UserProfile.objects.create(user=self.user, role=UserProfile.Role.SUPPORT_WORKER)
        self.credentials = {'username': self.user.username, 'password': 'fictional-test-password'}

    def test_real_login_post_still_redirects_to_role_router(self):
        response = self.client.post(reverse('login'), self.credentials)
        self.assertRedirects(response, reverse('role_redirect'), fetch_redirect_response=False)
        self.assertEqual(self.client.session['_auth_user_id'], str(self.user.pk))

    def test_query_string_next_is_still_used(self):
        target = reverse('worker_log_list')
        response = self.client.post(reverse('login') + '?next=' + target, self.credentials)
        self.assertRedirects(response, target, fetch_redirect_response=False)

    def test_post_next_takes_existing_precedence(self):
        response = self.client.post(reverse('login') + '?next=/ignored/', {**self.credentials, 'next': reverse('worker_dashboard')})
        self.assertRedirects(response, reverse('worker_dashboard'), fetch_redirect_response=False)

    def test_external_next_is_still_rejected(self):
        for target in ('https://outside.example.invalid/', '//outside.example.invalid/'):
            with self.subTest(target=target):
                self.client.logout()
                response = self.client.post(reverse('login'), {**self.credentials, 'next': target})
                self.assertRedirects(response, reverse('role_redirect'), fetch_redirect_response=False)

    def test_domain_badge_cannot_grant_admin_role(self):
        response = self.client.post(reverse('login'), self.credentials, HTTP_HOST='admin.bscare.com.au')
        self.assertRedirects(response, reverse('role_redirect'), fetch_redirect_response=False)
        routed = self.client.get(reverse('role_redirect'), HTTP_HOST='admin.bscare.com.au')
        self.assertRedirects(routed, reverse('worker_dashboard'), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse('admin_dashboard'), HTTP_HOST='admin.bscare.com.au').status_code, 403)

    def test_inactive_user_is_rejected_by_existing_form(self):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        response = self.client.post(reverse('login'), self.credentials)
        self.assertContains(response, 'Invalid username or password.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_missing_role_retains_original_routing(self):
        self.user.userprofile.delete()
        response = self.client.post(reverse('login'), self.credentials)
        self.assertRedirects(response, reverse('role_redirect'), fetch_redirect_response=False)
        response = self.client.get(reverse('role_redirect'))
        self.assertRedirects(response, reverse('login'), fetch_redirect_response=False)

    def test_csrf_enforcement_is_retained(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse('login'))
        token = Markup(response).one('input', name='csrfmiddlewaretoken')['value']
        self.assertEqual(client.post(reverse('login'), self.credentials).status_code, 403)
        response = client.post(reverse('login'), {**self.credentials, 'csrfmiddlewaretoken': token})
        self.assertRedirects(response, reverse('role_redirect'), fetch_redirect_response=False)
