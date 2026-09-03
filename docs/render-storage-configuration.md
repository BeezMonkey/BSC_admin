# Render Document Storage Configuration

This runbook records the current Render document-storage setup for Brisbane Star Care. It is intended for future maintenance, redeploys, and troubleshooting. Do not store real passwords, private keys, database URLs, or recovery codes in this file.

## Current Status

- Status as of 2026-09-03: worker document uploads and service log attachments have passed the live smoke test.
- Active storage backend: SFTP.
- Storage host: CrazyDomains cPanel hosting for `duratechequip.com`.
- Storage root on cPanel: `/home4/duratech/bsc_private_uploads`.
- Uploaded files are private. The app streams downloads and previews through Django permission-protected views.
- The file names inside `bsc_private_uploads` may look random or hashed. This is normal. The app stores the worker's original filename separately and uses that original name for the admin/worker download experience.

## Render Environment Variables

Set these in the Render web service environment tab.

```text
DOCUMENT_STORAGE_BACKEND=sftp
DOCUMENT_SFTP_HOST=ftp.duratechequip.com
DOCUMENT_SFTP_PORT=22
DOCUMENT_SFTP_USERNAME=duratech
DOCUMENT_SFTP_PRIVATE_KEY=<complete private key, including BEGIN/END lines>
DOCUMENT_SFTP_KEY_PASSPHRASE=<private key passphrase, if the key has one>
DOCUMENT_SFTP_ROOT=/home4/duratech/bsc_private_uploads
DOCUMENT_SFTP_TIMEOUT=10
```

Rules:
- Keep exactly one `DOCUMENT_STORAGE_BACKEND` key in Render. Duplicate keys can prevent saving or make the active value unclear.
- `DOCUMENT_SFTP_PRIVATE_KEY` must be the private key, not the public `ssh-rsa ...` key.
- If Render does not preserve line breaks in the private key value, store the key with literal `\n` sequences. The app converts `\n` back into real newlines.
- `DOCUMENT_SFTP_KEY_PASSPHRASE` is optional only for keys created without a passphrase. If the cPanel SSH key has a passphrase, this value is required.
- Do not paste the private key or passphrase into GitHub, documentation, screenshots, issue comments, or chat.

## cPanel / CrazyDomains Setup

Current setup:
- cPanel account path: `/home4/duratech`.
- Private upload folder: `/home4/duratech/bsc_private_uploads`.
- SSH key name used during setup: `bsc_render_storage`.
- SFTP login user: `duratech`.
- SFTP host: `ftp.duratechequip.com`.
- SFTP port: `22`.

Required cPanel state:
- The `bsc_render_storage` public key must remain authorized in cPanel SSH Access.
- The private key copied into Render must match that authorized public key.
- The `bsc_private_uploads` directory should stay outside `public_html`.
- The directory must be writable by the `duratech` hosting account.

## Why SFTP, Not FTPS

The app still supports `DOCUMENT_STORAGE_BACKEND=ftps`, but the current Render deployment should use SFTP.

During setup, Render could connect to port 22 on both `duratechequip.com` and `ftp.duratechequip.com`. The FTPS upload path failed during the file transfer step with a timeout. That made SFTP the more reliable option for this deployment.

Leave old `DOCUMENT_FTPS_*` values out of the active configuration unless FTPS is intentionally retested later.

## Smoke Test Commands

Run these from Render Shell after changing storage settings.

Confirm the active storage class:

```bash
python manage.py shell -c "from django.core.files.storage import default_storage; print(default_storage.__class__)"
```

Expected result:

```text
<class 'documents.storage.SFTPStorage'>
```

Confirm port 22 is reachable from Render:

```bash
python - <<'PY'
import socket

hosts = ["duratechequip.com", "ftp.duratechequip.com"]
for host in hosts:
    try:
        sock = socket.create_connection((host, 22), timeout=10)
        sock.close()
        print(f"OK {host}:22")
    except Exception as exc:
        print(f"FAIL {host}:22 -> {type(exc).__name__}: {exc}")
PY
```

Confirm Django can write to private storage:

```bash
python manage.py shell -c "from django.core.files.base import ContentFile; from django.core.files.storage import default_storage; name=default_storage.save('diagnostics/render-sftp-test.txt', ContentFile(b'render sftp diagnostic')); print(name)"
```

Expected result:

```text
diagnostics/render-sftp-test.txt
```

Clean up the diagnostic file:

```bash
python manage.py shell -c "from django.core.files.storage import default_storage; default_storage.delete('diagnostics/render-sftp-test.txt'); print('deleted')"
```

Then test through the browser with fake files only:
- Support worker uploads a compliance document.
- Support worker submits a service log with up to three attachments.
- Admin can see the document/service log attachment.
- Admin can preview JPG/PNG/PDF attachments.
- Admin downloads DOC/DOCX attachments instead of previewing them.
- Admin can download the service log PDF.

## Troubleshooting

If uploads fail with `Could not upload document to private storage`:

1. Check `DOCUMENT_STORAGE_BACKEND` is exactly `sftp`.
2. Check there is no duplicate `DOCUMENT_STORAGE_BACKEND` key in Render.
3. Check `DOCUMENT_SFTP_PRIVATE_KEY` is the complete private key.
4. Check the key's passphrase matches `DOCUMENT_SFTP_KEY_PASSPHRASE`.
5. Check cPanel SSH Access still shows the matching public key as authorized.
6. Check Render Shell can connect to `ftp.duratechequip.com:22`.
7. Check `/home4/duratech/bsc_private_uploads` exists and is writable.
8. Check Render was redeployed after environment variables were saved.

If PDF preview fails but download works:
- Confirm the file is a real PDF.
- Confirm the attachment uses the app's `document_preview` route, not a public cPanel URL.
- Use Download as the fallback. DOC/DOCX files are download-only by design.

If a file appears in cPanel with a random filename:
- This is expected. Do not rename files directly in cPanel.
- Use the app UI for review and download, because the database stores the user-facing original filename and permissions.

## Security And Maintenance

- Rotate the SFTP key and passphrase before accepting real compliance or service log records.
- Store the Render environment values in a password manager.
- Keep screenshots of the Render Environment tab cropped or redacted.
- Confirm CrazyDomains backup coverage for `/home4/duratech/bsc_private_uploads`.
- Before production use, perform a backup-and-restore test for at least one uploaded document.
- Remove unused FTPS credentials from Render once SFTP has been confirmed stable.
