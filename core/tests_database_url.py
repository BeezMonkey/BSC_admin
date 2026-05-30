from pathlib import Path

from django.test import SimpleTestCase

from bscare_ndis.database import database_config_from_url


class DatabaseUrlConfigTests(SimpleTestCase):
    def test_empty_database_url_uses_default_sqlite(self):
        config = database_config_from_url("", Path("db.sqlite3"))

        self.assertEqual(config["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(config["NAME"], Path("db.sqlite3"))

    def test_postgres_database_url_is_parsed(self):
        config = database_config_from_url(
            "postgres://bsc_user:secret%21@db.example.com:5432/bsc_admin",
            Path("db.sqlite3"),
        )

        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["NAME"], "bsc_admin")
        self.assertEqual(config["USER"], "bsc_user")
        self.assertEqual(config["PASSWORD"], "secret!")
        self.assertEqual(config["HOST"], "db.example.com")
        self.assertEqual(config["PORT"], "5432")

    def test_sqlite_database_url_is_parsed(self):
        config = database_config_from_url(
            "sqlite:///C:/data/bsc.sqlite3",
            Path("db.sqlite3"),
        )

        self.assertEqual(config["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(config["NAME"], Path("/C:/data/bsc.sqlite3"))
