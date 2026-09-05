from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import RequestFactory, SimpleTestCase, override_settings


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class PortalAppearanceIsolationTests(SimpleTestCase):
    def render_shell(self, template):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        return render_to_string(template, request=request)

    def test_worker_and_coordinator_load_portal_appearance_after_shared_styles(self):
        for template in ("worker_base.html", "coordinator_base.html"):
            with self.subTest(template=template):
                html = self.render_shell(template)

                self.assertIn('data-portal-theme', html)
                self.assertLess(
                    html.index(static("css/app.css")),
                    html.index(static("css/portal.css")),
                )

    def test_admin_and_login_do_not_load_portal_appearance(self):
        for template in ("admin_base.html", "accounts/login.html"):
            with self.subTest(template=template):
                html = self.render_shell(template)

                self.assertNotIn(static("css/portal.css"), html)
                self.assertNotIn("data-portal-theme", html)
