from contextlib import contextmanager
from contextlib import suppress
from ftplib import FTP_TLS, all_errors, error_perm
from io import BytesIO
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
