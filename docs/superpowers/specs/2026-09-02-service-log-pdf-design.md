# Service Log PDF Design

## Goal

Allow admins to download a service log as a PDF for offline records and business archiving.

## Scope

The first version is admin-only. Support workers do not get a PDF download button. The PDF is generated on demand from the current service log record and is not stored as another uploaded document.

## PDF Content

The PDF includes the Brisbane Star Care logo already used by invoice PDFs, a clear "SERVICE LOG" heading, participant and worker details, service date, shift ID, support item, actual time, break, actual hours, kilometres, status, submitted and reviewed timestamps, case notes, worker notes, rejection reason when present, and an attachment filename list.

Attachments are listed by original filename only. The attached files are not embedded into the service log PDF.

## Admin Flow

The admin service log detail page gains a `Download PDF` button beside the existing back action. The download filename should be stable and readable: `ServiceLog_<date>_<id>_<participant>.pdf`.

## Testing

Tests cover that an admin can download the PDF, the PDF uses a clear filename, expected service log content appears in the PDF stream, the detail page shows the button, and a support worker cannot access the admin PDF endpoint.
