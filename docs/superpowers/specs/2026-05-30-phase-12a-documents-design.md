# Phase 12A Documents Design

## Goal

Phase 12A adds basic document management. Admin users can upload and view documents linked to business records, while workers can only view documents linked directly to their own worker profile.

## Scope

This phase includes:

- `Document` model with uploaded file, title, category, notes, and uploader.
- Optional links to participant, worker, invoice, and service log.
- Admin document list, create, detail, and download.
- Worker document list, detail, and download for their own worker-linked documents only.
- Basic file type and file size validation.

This phase does not include full audit logging, antivirus scanning, participant/family portal access, object-level participant document access for workers, backup automation, or production storage integration.

## Data Model

`Document` stores:

- `title`
- `category`
- `file`
- `participant`
- `worker`
- `invoice`
- `service_log`
- `notes`
- `uploaded_by`
- timestamps

At least one linked object is required.

## Validation

Allowed file extensions:

- `.pdf`
- `.jpg`
- `.jpeg`
- `.png`
- `.doc`
- `.docx`

Maximum file size is 10 MB.

## Permissions

Admins and super admins can manage all documents. Workers can only access documents where `document.worker.user` is their own user. Worker access to participant, service log, or invoice documents stays closed in this phase to avoid privacy leaks.

## Tests

Tests cover:

- Admin can upload participant-linked document.
- Admin can view document detail and download file.
- Upload requires at least one linked object.
- Unsupported file extensions are rejected.
- Oversized files are rejected.
- Worker sees only own worker-linked documents.
- Worker cannot access participant-linked documents.
