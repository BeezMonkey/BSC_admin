from django.test import SimpleTestCase
from django.urls import reverse


class PublicRouteTests(SimpleTestCase):
    def test_root_redirects_to_login(self):
        response = self.client.get("/")

        self.assertRedirects(
            response,
            reverse("login"),
            fetch_redirect_response=False,
        )

    def test_health_check_reports_ok(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
