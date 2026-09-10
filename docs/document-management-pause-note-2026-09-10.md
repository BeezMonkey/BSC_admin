# Document Management Direction Note - 2026-09-10

## Current status

Document storage redesign work is paused. Do not continue developing Google Drive, CrazyDomains storage changes, or a broader file-manager replacement until the product direction is reviewed again.

The Admin user experience direction has been narrowed: file management should be reached from each Participant or Support Worker detail page, not from a standalone primary sidebar module.

The latest document-management PR is merged into `origin/main`:

- PR: `#233`
- Merge commit: `3a40718` - `Merge pull request #233 from BeezMonkey/codex/uploaded-file-manager-focus`
- Feature commit: `49facf7` - `Refocus documents as uploaded file manager`

Related recently merged document-management work:

- `#226` - Admin document manager structure
- `#227` - Document upload context
- `#228` - Safe admin document deletion
- `#231` - Dedicated document directory pages
- `#232` - Document upload form UI simplification
- `#233` - Uploaded file manager focus

## What exists now

The standalone `Uploaded Files` URL still exists for compatibility, but it should not be treated as the primary Admin entry point.

The current flow organizes uploaded files by person:

- Participants
- Support Workers
- Person-level file pages
- Upload, download, preview, review, and delete actions

The current implementation still uses the existing storage approach. Google Drive integration has not been implemented.

## Paused direction

The next storage direction under consideration is to stop treating Admin Documents as a broad business-record attachment area and instead make it a focused file-management area for files that genuinely need external storage.

The preferred future direction is likely:

- Google Drive or Shared Drive stores the files.
- BSC keeps metadata, ownership, permissions, and audit history.
- Admin sees a clean person/folder-based file manager.
- Logs, invoices, and generated records stay out of this file manager unless there is a specific business need.

## Entry recommendation

Avoid keeping Uploaded Files as a prominent sidebar item.

Recommended approach:

- Remove `Uploaded Files` from the main Admin sidebar.
- Keep the URLs and views available for Admin users.
- Use contextual links from Participant and Support Worker detail pages.
- Let the person-level file page handle review, download, upload, and delete actions.

This keeps file management reachable without making it look like an active primary module.

## Resume checklist

Before continuing development:

- Decide whether the future storage target is CrazyDomains, Google Drive Shared Drive, or another provider.
- Decide whether Admin Documents should be renamed to `Files`, `Uploaded Files`, or `Document Library`.
- Decide whether existing uploaded files should be migrated or left in the old storage.
- Confirm whether service logs and invoices should remain excluded from the Admin file manager.
- Start with a visual prototype before changing storage code.
