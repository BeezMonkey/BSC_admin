from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from bscare_ndis.settings import (
    document_storage_config,
    env_bool,
    env_list,
    render_external_hostname,
)


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

    def test_default_document_storage_uses_local_filesystem(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                document_storage_config(),
                {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            )

    def test_ftps_document_storage_reads_required_environment(self):
        with patch.dict(
            "os.environ",
            {
                "DOCUMENT_STORAGE_BACKEND": "ftps",
                "DOCUMENT_FTPS_HOST": "ftp.example.com",
                "DOCUMENT_FTPS_PORT": "21",
                "DOCUMENT_FTPS_USERNAME": "bscfiles@example.com",
                "DOCUMENT_FTPS_PASSWORD": "secret",
                "DOCUMENT_FTPS_ROOT": "/",
            },
            clear=True,
        ):
            self.assertEqual(
                document_storage_config(),
                {
                    "BACKEND": "documents.storage.FTPSStorage",
                    "OPTIONS": {
                        "host": "ftp.example.com",
                        "port": 21,
                        "username": "bscfiles@example.com",
                        "password": "secret",
                        "root_path": "/",
                    },
                },
            )

    def test_ftps_document_storage_requires_credentials(self):
        with patch.dict(
            "os.environ",
            {
                "DOCUMENT_STORAGE_BACKEND": "ftps",
                "DOCUMENT_FTPS_HOST": "ftp.example.com",
                "DOCUMENT_FTPS_USERNAME": "bscfiles@example.com",
            },
            clear=True,
        ):
            with self.assertRaisesMessage(
                ImproperlyConfigured,
                "DOCUMENT_FTPS_PASSWORD is required",
            ):
                document_storage_config()
