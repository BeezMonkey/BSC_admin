# Worker Service Log Attachment Picker Design

## Scope

Improve the support worker service log form attachment selection experience only. The existing backend upload flow, storage flow, and maximum limits stay the same: up to 3 files, 5 MB each, PDF/JPG/PNG/DOC/DOCX.

## User Experience

The attachment section should guide workers through adding files without requiring them to know multi-select keyboard behavior. Workers see an `Add file` button, a live list of selected files, each file's size, a `Ready to upload` status, and a `Remove` action before submission.

Selecting another file appends to the existing list instead of replacing it. When 3 files are selected, the add button is disabled and the section explains that the limit has been reached. If a worker removes a file, the add button becomes available again.

The page should avoid saying a file was uploaded before the service log is submitted. The accurate state before submission is selected or ready to upload.

## Architecture

Keep the form submission as a normal multipart POST. Use a single file input named `attachments` so the current Django view can continue reading `request.FILES.getlist("attachments")`. Add a small progressive-enhancement script that maintains a client-side file list using `DataTransfer`, updates the input's `files`, and renders selection feedback.

If JavaScript is unavailable, the native file input remains usable as a fallback.

## Testing

Add template-level tests for the worker form to ensure the attachment picker hooks, limits, helper text, selected-file feedback text, and remove affordance are rendered. Keep existing backend tests for multiple attachment creation and over-limit rejection.
