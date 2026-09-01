from ftplib import error_perm

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.test import SimpleTestCase

from documents.storage import FTPSStorage


class FakeFTP_TLS:
    instances = []
    files = {}
    directories = set()

    def __init__(self):
        self.commands = []
        FakeFTP_TLS.instances.append(self)

    def connect(self, host, port, timeout=None):
        self.commands.append(("connect", host, port, timeout))

    def login(self, username, password):
        self.commands.append(("login", username, password))

    def prot_p(self):
        self.commands.append(("prot_p",))

    def mkd(self, path):
        self.directories.add(path)

    def storbinary(self, command, file_handle):
        prefix, path = command.split(" ", 1)
        if prefix != "STOR":
            raise AssertionError(f"Unexpected command {command}")
        self.files[path] = file_handle.read()

    def retrbinary(self, command, callback):
        prefix, path = command.split(" ", 1)
        if prefix != "RETR":
            raise AssertionError(f"Unexpected command {command}")
        callback(self.files[path])

    def size(self, path):
        if path not in self.files:
            raise error_perm("550 File not found")
        return len(self.files[path])

    def delete(self, path):
        if path not in self.files:
            raise error_perm("550 File not found")
        del self.files[path]

    def quit(self):
        self.commands.append(("quit",))


class FTPSStorageTests(SimpleTestCase):
    def setUp(self):
        FakeFTP_TLS.instances = []
        FakeFTP_TLS.files = {}
        FakeFTP_TLS.directories = set()

    def storage(self):
        return FTPSStorage(
            host="ftp.example.com",
            port=21,
            username="bscfiles@example.com",
            password="secret",
            root_path="/",
            ftp_class=FakeFTP_TLS,
        )

    def test_save_uses_explicit_ftps_and_creates_remote_directories(self):
        saved_name = self.storage().save(
            "documents/workers/police-check.pdf",
            ContentFile(b"police-check"),
        )

        self.assertEqual(saved_name, "documents/workers/police-check.pdf")
        self.assertEqual(
            FakeFTP_TLS.instances[0].commands[:3],
            [
                ("connect", "ftp.example.com", 21, 30),
                ("login", "bscfiles@example.com", "secret"),
                ("prot_p",),
            ],
        )
        self.assertIn("/documents", FakeFTP_TLS.directories)
        self.assertIn("/documents/workers", FakeFTP_TLS.directories)
        self.assertEqual(
            FakeFTP_TLS.files["/documents/workers/police-check.pdf"],
            b"police-check",
        )

    def test_open_reads_file_back_from_ftps(self):
        FakeFTP_TLS.files["/documents/workers/police-check.pdf"] = b"stored-file"

        with self.storage().open("documents/workers/police-check.pdf", "rb") as remote_file:
            self.assertEqual(remote_file.read(), b"stored-file")

    def test_exists_and_delete_use_private_remote_path(self):
        storage = self.storage()
        FakeFTP_TLS.files["/documents/workers/police-check.pdf"] = b"stored-file"

        self.assertTrue(storage.exists("documents/workers/police-check.pdf"))
        storage.delete("documents/workers/police-check.pdf")

        self.assertFalse(storage.exists("documents/workers/police-check.pdf"))

    def test_url_is_not_available_for_private_ftps_files(self):
        with self.assertRaisesMessage(ValueError, "do not have public URLs"):
            self.storage().url("documents/workers/police-check.pdf")

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(SuspiciousFileOperation):
            self.storage().save("../public_html/leak.pdf", ContentFile(b"leak"))
