from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.test import RequestFactory, SimpleTestCase


class AdminAppearanceIsolationTests(SimpleTestCase):
    def render_shell(self, template):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        return render_to_string(template, request=request)

    def test_admin_loads_appearance_after_shared_styles(self):
        html = self.render_shell("admin_base.html")

        self.assertIn('class="app-shell" data-admin-theme', html)
        self.assertLess(
            html.index(static("css/app.css")),
            html.index(static("css/admin.css")),
        )

    def test_other_shells_do_not_load_admin_appearance(self):
        for template in ("base.html", "worker_base.html", "coordinator_base.html"):
            with self.subTest(template=template):
                html = self.render_shell(template)
                self.assertNotIn(static("css/admin.css"), html)
                self.assertNotIn("data-admin-theme", html)
