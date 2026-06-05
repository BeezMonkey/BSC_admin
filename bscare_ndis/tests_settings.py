from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from bscare_ndis.settings import env_bool, env_list, render_external_hostname


class EnvironmentSettingsTests(SimpleTestCase):
    def test_business_timezone_is_fixed_to_brisbane(self):
        self.assertEqual(settings.TIME_ZONE, "Australia/Brisbane")
        self.assertTrue(settings.USE_TZ)

    def test_env_helpers_keep_local_defaults_available(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertTrue(env_bool("DJANGO_DEBUG", True))
            self.assertEqual(
                env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost"),
                ["127.0.0.1", "localhost"],
            )

    def test_env_bool_accepts_common_true_values(self):
        for value in ["1", "true", "TRUE", "yes", "on"]:
            with self.subTest(value=value), patch.dict("os.environ", {"FEATURE_FLAG": value}):
                self.assertTrue(env_bool("FEATURE_FLAG"))

    def test_env_bool_rejects_common_false_values(self):
        for value in ["0", "false", "FALSE", "no", "off", ""]:
            with self.subTest(value=value), patch.dict("os.environ", {"FEATURE_FLAG": value}):
                self.assertFalse(env_bool("FEATURE_FLAG"))

    def test_env_list_trims_values_and_ignores_blanks(self):
        with patch.dict(
            "os.environ",
            {"DJANGO_ALLOWED_HOSTS": " example.com, www.example.com, , staging.example.com "},
        ):
            self.assertEqual(
                env_list("DJANGO_ALLOWED_HOSTS"),
                ["example.com", "www.example.com", "staging.example.com"],
            )

    def test_env_list_uses_default_when_variable_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost"),
                ["127.0.0.1", "localhost"],
            )

    def test_render_external_hostname_can_extend_allowed_hosts(self):
        with patch.dict("os.environ", {"RENDER_EXTERNAL_HOSTNAME": "bsc-beta.onrender.com"}):
            self.assertEqual(render_external_hostname(), "bsc-beta.onrender.com")

    def test_whitenoise_middleware_is_enabled_after_security_middleware(self):
        security_index = settings.MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
        whitenoise_index = settings.MIDDLEWARE.index("whitenoise.middleware.WhiteNoiseMiddleware")

        self.assertEqual(whitenoise_index, security_index + 1)

    def test_staticfiles_storage_uses_whitenoise_manifest_backend(self):
        self.assertEqual(
            settings.STORAGES["staticfiles"]["BACKEND"],
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
        )
