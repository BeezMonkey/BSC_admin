from ftplib import error_perm

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.test import SimpleTestCase

from documents.storage import FTPSStorage, SFTPStorage, StorageOperationError


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


class TimeoutFTP_TLS(FakeFTP_TLS):
    def storbinary(self, command, file_handle):
        raise TimeoutError("timed out")


class FakeSFTPFile:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.content


class FakeSFTPClient:
    files = {}
    directories = set()

    def mkdir(self, path):
        self.directories.add(path)

    def putfo(self, file_handle, path):
        self.files[path] = file_handle.read()

    def open(self, path, mode="rb"):
        return FakeSFTPFile(self.files[path])

    def stat(self, path):
        if path not in self.files:
            raise FileNotFoundError(path)
        return type("Stat", (), {"st_size": len(self.files[path])})()

    def remove(self, path):
        if path not in self.files:
            raise FileNotFoundError(path)
        del self.files[path]

    def close(self):
        pass


class FakeSSHClient:
    instances = []

    def __init__(self):
        self.commands = []
        self.sftp = FakeSFTPClient()
        FakeSSHClient.instances.append(self)

    def set_missing_host_key_policy(self, policy):
        self.commands.append(("set_missing_host_key_policy", policy.__class__.__name__))

    def connect(self, **kwargs):
        self.commands.append(("connect", kwargs))

    def open_sftp(self):
        self.commands.append(("open_sftp",))
        return self.sftp

    def close(self):
        self.commands.append(("close",))


class TimeoutSFTPClient(FakeSFTPClient):
    def putfo(self, file_handle, path):
        raise TimeoutError("timed out")


class TimeoutSSHClient(FakeSSHClient):
    def __init__(self):
        super().__init__()
        self.sftp = TimeoutSFTPClient()


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
                ("connect", "ftp.example.com", 21, 10),
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

    def test_save_wraps_network_timeout_as_storage_error(self):
        storage = FTPSStorage(
            host="ftp.example.com",
            port=21,
            username="bscfiles@example.com",
            password="secret",
            root_path="/",
            timeout=8,
            ftp_class=TimeoutFTP_TLS,
        )

        with self.assertRaisesMessage(
            StorageOperationError,
            "Could not upload document to private storage",
        ):
            storage.save("documents/workers/police-check.pdf", ContentFile(b"police-check"))

        self.assertEqual(TimeoutFTP_TLS.instances[0].commands[0][3], 8)


class SFTPStorageTests(SimpleTestCase):
    def setUp(self):
        FakeSSHClient.instances = []
        FakeSFTPClient.files = {}
        FakeSFTPClient.directories = set()

    def storage(self, ssh_client_class=FakeSSHClient, pkey_loader=None):
        return SFTPStorage(
            host="ftp.example.com",
            port=22,
            username="duratech",
            private_key="-----BEGIN RSA PRIVATE KEY-----\nkey\n-----END RSA PRIVATE KEY-----",
            key_passphrase="key-secret",
            root_path="/home4/duratech/bsc_private_uploads",
            ssh_client_class=ssh_client_class,
            missing_host_key_policy_class=lambda: object(),
            pkey_loader=pkey_loader or (lambda private_key, passphrase: "loaded-key"),
        )

    def test_save_uses_sftp_key_login_and_creates_remote_directories(self):
        saved_name = self.storage().save(
            "documents/workers/police-check.pdf",
            ContentFile(b"police-check"),
        )

        self.assertEqual(saved_name, "documents/workers/police-check.pdf")
        connect_kwargs = FakeSSHClient.instances[0].commands[1][1]
        self.assertEqual(connect_kwargs["hostname"], "ftp.example.com")
        self.assertEqual(connect_kwargs["port"], 22)
        self.assertEqual(connect_kwargs["username"], "duratech")
        self.assertEqual(connect_kwargs["pkey"], "loaded-key")
        self.assertFalse(connect_kwargs["look_for_keys"])
        self.assertFalse(connect_kwargs["allow_agent"])
        self.assertIn("/home4/duratech/bsc_private_uploads/documents", FakeSFTPClient.directories)
        self.assertIn(
            "/home4/duratech/bsc_private_uploads/documents/workers",
            FakeSFTPClient.directories,
        )
        self.assertEqual(
            FakeSFTPClient.files[
                "/home4/duratech/bsc_private_uploads/documents/workers/police-check.pdf"
            ],
            b"police-check",
        )

    def test_open_reads_file_back_from_sftp(self):
        FakeSFTPClient.files[
            "/home4/duratech/bsc_private_uploads/documents/workers/police-check.pdf"
        ] = b"stored-file"

        with self.storage().open("documents/workers/police-check.pdf", "rb") as remote_file:
            self.assertEqual(remote_file.read(), b"stored-file")

    def test_exists_and_delete_use_private_sftp_path(self):
        storage = self.storage()
        FakeSFTPClient.files[
            "/home4/duratech/bsc_private_uploads/documents/workers/police-check.pdf"
        ] = b"stored-file"

        self.assertTrue(storage.exists("documents/workers/police-check.pdf"))
        storage.delete("documents/workers/police-check.pdf")

        self.assertFalse(storage.exists("documents/workers/police-check.pdf"))

    def test_url_is_not_available_for_private_sftp_files(self):
        with self.assertRaisesMessage(ValueError, "do not have public URLs"):
            self.storage().url("documents/workers/police-check.pdf")

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(SuspiciousFileOperation):
            self.storage().save("../public_html/leak.pdf", ContentFile(b"leak"))

    def test_private_key_loader_receives_passphrase(self):
        calls = []

        self.storage(
            pkey_loader=lambda private_key, passphrase: calls.append(
                (private_key, passphrase)
            )
            or "loaded-key"
        ).save("documents/workers/police-check.pdf", ContentFile(b"police-check"))

        self.assertGreaterEqual(len(calls), 1)
        self.assertTrue(
            all(
                call == (
                    "-----BEGIN RSA PRIVATE KEY-----\nkey\n-----END RSA PRIVATE KEY-----",
                    "key-secret",
                )
                for call in calls
            )
        )

    def test_save_wraps_network_timeout_as_storage_error(self):
        storage = self.storage(ssh_client_class=TimeoutSSHClient)

        with self.assertRaisesMessage(
            StorageOperationError,
            "Could not upload document to private storage",
        ):
            storage.save("documents/workers/police-check.pdf", ContentFile(b"police-check"))
