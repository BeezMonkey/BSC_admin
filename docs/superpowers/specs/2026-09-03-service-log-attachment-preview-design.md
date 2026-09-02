# Service Log Attachment Preview Design

## Scope

Improve the admin service log detail attachment area only. The existing service log PDF download stays unchanged, compliance document pages stay available, and worker-facing document screens are unchanged.

## User Experience

On the admin service log detail page, attachments are shown as compact preview cards instead of plain list rows. Image attachments show a thumbnail. PDF attachments show a preview card. DOC and DOCX attachments show a document card with download only. The old `View` link is removed from this attachment area because it leads to a generic document detail page that repeats information already shown on the service log.

Clicking an image or PDF preview opens an in-page modal so admin can inspect the attachment without leaving the service log. Every attachment keeps a clear `Download` action using the existing download flow and original filename.

## Architecture

Add non-database helper properties to `Document` for extension and preview classification. Add an admin-only preview endpoint that streams previewable document files inline through Django, rather than exposing the private storage path. The preview endpoint supports JPG, JPEG, PNG, and PDF. Other file types return 404.

The service log detail template consumes the helper properties and the preview endpoint. A small vanilla JavaScript controller opens and closes the modal, inserts either an image or iframe, and keeps the download action available inside the modal.

## Testing

Add tests for the admin service log detail markup, image and PDF preview rendering, DOCX download-only behavior, inline content disposition from the preview endpoint, and worker denial for the admin preview endpoint.
