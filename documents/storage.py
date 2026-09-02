from contextlib import contextmanager
from contextlib import suppress
from ftplib import FTP_TLS, all_errors, error_perm
from io import BytesIO
from io import StringIO
import posixpath

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import File
from django.core.files.storage import Storage


class StorageOperationError(Exception):
    pass


class FTPSStorage(Storage):
    def __init__(
        self,
        host,
        username,
        password,
        port=21,
        root_path="/",
        timeout=10,
        ftp_class=FTP_TLS,
    ):
        self.host = host
        self.username = username
        self.password = password
        self.port = int(port)
        self.root_path = self._normalize_root_path(root_path)
        self.timeout = timeout
        self.ftp_class = ftp_class

    @staticmethod
    def _normalize_root_path(root_path):
        root = str(root_path or "/").replace("\\", "/").strip()
        if not root:
            return "/"
        if not root.startswith("/"):
            root = f"/{root}"
        root = posixpath.normpath(root)
        return "/" if root == "." else root

    @staticmethod
    def _normalize_name(name):
        raw_name = str(name).replace("\\", "/")
        normalized = posixpath.normpath(raw_name)
        if (
            not normalized
            or normalized == "."
            or normalized == ".."
            or normalized.startswith("../")
            or normalized.startswith("/")
        ):
            raise SuspiciousFileOperation(f"Invalid remote file path: {name}")
        return normalized

    def _remote_path(self, name):
        normalized_name = self._normalize_name(name)
        if self.root_path == "/":
            return f"/{normalized_name}"
        return posixpath.join(self.root_path, normalized_name)

    @contextmanager
    def _connection(self):
        ftp = self.ftp_class()
        ftp.connect(self.host, self.port, timeout=self.timeout)
        ftp.login(self.username, self.password)
        ftp.prot_p()
        try:
            yield ftp
        finally:
            with suppress(*all_errors):
                ftp.quit()

    def _ensure_directories(self, ftp, remote_path):
        directory = posixpath.dirname(remote_path)
        if not directory or directory == "/":
            return

        current = ""
        for part in directory.strip("/").split("/"):
            current = f"{current}/{part}"
            try:
                ftp.mkd(current)
            except error_perm:
                pass

    def _open(self, name, mode="rb"):
        if mode not in {"rb", "r"}:
            raise ValueError("FTPSStorage only supports read modes for open().")

        buffer = BytesIO()
        with self._connection() as ftp:
            ftp.retrbinary(f"RETR {self._remote_path(name)}", buffer.write)
        buffer.seek(0)
        return File(buffer, name=name)

    def _save(self, name, content):
        remote_path = self._remote_path(name)
        if hasattr(content, "open"):
            content.open()
        if hasattr(content, "seek"):
            content.seek(0)

        try:
            with self._connection() as ftp:
                self._ensure_directories(ftp, remote_path)
                ftp.storbinary(f"STOR {remote_path}", content)
        except all_errors as exc:
            raise StorageOperationError(
                "Could not upload document to private storage. Please try again later or contact admin."
            ) from exc
        return self._normalize_name(name)

    def delete(self, name):
        try:
            with self._connection() as ftp:
                ftp.delete(self._remote_path(name))
        except error_perm:
            pass

    def exists(self, name):
        try:
            with self._connection() as ftp:
                ftp.size(self._remote_path(name))
        except error_perm:
            return False
        return True

    def size(self, name):
        with self._connection() as ftp:
            return ftp.size(self._remote_path(name))

    def url(self, name):
        raise ValueError("Private FTPS files do not have public URLs.")


class SFTPStorage(Storage):
    def __init__(
        self,
        host,
        username,
        private_key,
        key_passphrase="",
        port=22,
        root_path="/",
        timeout=10,
        ssh_client_class=None,
        missing_host_key_policy_class=None,
        pkey_loader=None,
    ):
        self.host = host
        self.username = username
        self.private_key = private_key.replace("\\n", "\n")
        self.key_passphrase = key_passphrase or None
        self.port = int(port)
        self.root_path = FTPSStorage._normalize_root_path(root_path)
        self.timeout = int(timeout)
        self.ssh_client_class = ssh_client_class
        self.missing_host_key_policy_class = missing_host_key_policy_class
        self.pkey_loader = pkey_loader

    def _remote_path(self, name):
        normalized_name = FTPSStorage._normalize_name(name)
        if self.root_path == "/":
            return f"/{normalized_name}"
        return posixpath.join(self.root_path, normalized_name)

    def _paramiko(self):
        import paramiko

        return paramiko

    def _load_private_key(self):
        if self.pkey_loader:
            return self.pkey_loader(self.private_key, self.key_passphrase)
        return self._paramiko().RSAKey.from_private_key(
            StringIO(self.private_key),
            password=self.key_passphrase,
        )

    def _ssh_client(self):
        if self.ssh_client_class:
            return self.ssh_client_class()
        return self._paramiko().SSHClient()

    def _missing_host_key_policy(self):
        if self.missing_host_key_policy_class:
            return self.missing_host_key_policy_class()
        return self._paramiko().AutoAddPolicy()

    @contextmanager
    def _connection(self):
        ssh = self._ssh_client()
        sftp = None
        try:
            ssh.set_missing_host_key_policy(self._missing_host_key_policy())
            ssh.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                pkey=self._load_private_key(),
                timeout=self.timeout,
                banner_timeout=self.timeout,
                auth_timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False,
            )
            sftp = ssh.open_sftp()
            yield sftp
        finally:
            if sftp:
                with suppress(Exception):
                    sftp.close()
            with suppress(Exception):
                ssh.close()

    def _ensure_directories(self, sftp, remote_path):
        directory = posixpath.dirname(remote_path)
        if not directory or directory == "/":
            return

        current = ""
        for part in directory.strip("/").split("/"):
            current = f"{current}/{part}"
            try:
                sftp.mkdir(current)
            except OSError:
                pass

    def _open(self, name, mode="rb"):
        if mode not in {"rb", "r"}:
            raise ValueError("SFTPStorage only supports read modes for open().")

        with self._connection() as sftp:
            with sftp.open(self._remote_path(name), "rb") as remote_file:
                buffer = BytesIO(remote_file.read())
        buffer.seek(0)
        return File(buffer, name=name)

    def _save(self, name, content):
        remote_path = self._remote_path(name)
        if hasattr(content, "open"):
            content.open()
        if hasattr(content, "seek"):
            content.seek(0)

        try:
            with self._connection() as sftp:
                self._ensure_directories(sftp, remote_path)
                sftp.putfo(content, remote_path)
        except Exception as exc:
            raise StorageOperationError(
                "Could not upload document to private storage. Please try again later or contact admin."
            ) from exc
        return FTPSStorage._normalize_name(name)

    def delete(self, name):
        try:
            with self._connection() as sftp:
                sftp.remove(self._remote_path(name))
        except FileNotFoundError:
            pass

    def exists(self, name):
        try:
            with self._connection() as sftp:
                sftp.stat(self._remote_path(name))
        except FileNotFoundError:
            return False
        return True

    def size(self, name):
        with self._connection() as sftp:
            return sftp.stat(self._remote_path(name)).st_size

    def url(self, name):
        raise ValueError("Private SFTP files do not have public URLs.")
