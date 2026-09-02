# Service Log Attachment Preview Plan

## Steps

1. Add failing tests for service log attachment preview markup and admin-only inline preview behavior.
2. Add `Document` helper properties for file extension and preview support.
3. Add an admin-only `document_preview` view and URL.
4. Replace the service log attachment list with preview cards, remove the attachment `View` action, and add a modal for image/PDF preview.
5. Add focused CSS for the cards and modal while following existing admin styling.
6. Run focused tests, `manage.py check`, and diff hygiene checks before committing.
