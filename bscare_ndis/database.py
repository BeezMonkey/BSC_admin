from pathlib import Path
from urllib.parse import unquote, urlparse


def database_config_from_url(database_url, default_sqlite_path):
    if not database_url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": default_sqlite_path,
        }

    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()

    if scheme in {"postgres", "postgresql"}:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
        }

    if scheme == "sqlite":
        if parsed.netloc and parsed.path:
            name = f"//{parsed.netloc}{parsed.path}"
        else:
            name = parsed.path
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": Path(unquote(name)),
        }

    raise ValueError(f"Unsupported DATABASE_URL scheme: {scheme}")
