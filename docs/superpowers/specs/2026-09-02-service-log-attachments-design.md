# Service Log Attachments Design

## Goal

Make service log attachments production-reliable now that private SFTP document storage is available.

## Scope

This phase keeps the existing worker and admin service log screens intact. Workers still attach files while submitting a service log, and admins still review those files inside the related service log detail page. Compliance documents remain in the Documents area; service log attachments stay attached to the service log.

## Behavior

If every attachment stores successfully, the service log is created, attachment `Document` records are created, the shift becomes completed, audit logs are written, and the worker sees the existing success message.

If any attachment storage operation fails, the submission is treated as failed. The app shows the same private-storage error message used by compliance uploads, does not keep a partially created service log, does not leave attachment `Document` records behind, and does not mark the shift completed. Any files that were already stored during the failed request should be removed when possible.

Existing attachment limits stay unchanged: up to 3 files, 5 MB each, with PDF, JPG, PNG, DOC, or DOCX formats.

## Testing

Add tests around the worker service log submission flow for storage failure rollback. Re-run the existing service log, document, storage, and settings tests to confirm the SFTP work and current attachment behavior remain intact.
