# Phase 124: Invoice PDF Multi-Page Pagination

## Goal

Keep multi-line invoices readable by moving overflowing line items onto additional PDF pages, without changing invoice data, numbering, totals, payment details, permissions, or business workflow.

## Confirmed Problem

The current PDF builder creates exactly one Letter-sized page. Line items continue downward regardless of available space, while Invoice Total and Payment Details are clamped to fixed bottom positions. Invoices with several service and travel rows therefore overlap the total and payment sections.

## Chosen Approach

Extend the existing lightweight PDF builder to accept a list of pages. Keep the current first-page header and participant information design, then paginate only the line-item table when the next complete row cannot fit above the reserved footer area.

Each continuation page will:

- show a compact invoice identity line;
- repeat the `Date`, `Description`, `Qty`, `Rate`, and `Amount` table headers;
- continue with complete line-item rows without splitting one row across pages.

Invoice Total and Payment Details will appear once, after the final line item on the final page. If they do not fit below the final item, they will move together to a new final page.

## Layout Rules

- Calculate each line-item height from its wrapped Description plus the NDIS support item code line.
- Reserve a bottom safety margin before placing a row.
- Start a continuation page before rendering a row that would cross that margin.
- Repeat the table header after every page break.
- Keep current fonts, column positions, Australian dates, money formatting, logo, and purple accent styling.
- Do not reduce the existing body font size merely to keep an invoice on one page.
- Keep the current one-page result for invoices that fit safely on one page.

## Alternatives Considered

### Shrink the table to one page

Rejected because the required font reduction would make real invoices harder to read and would still fail at a larger number of rows.

### Move only the footer lower

Rejected because the page has a fixed height; it would hide content outside the printable area rather than solve the overlap.

### Use a new third-party PDF framework now

Deferred because it would increase change risk across the already-approved invoice design. The existing generator can support this phase with a focused multi-page extension.

## Files

- Modify `invoices/views.py` to support multiple PDF pages and paginate invoice rows.
- Modify `invoices/tests_exports.py` to reproduce the current overlap and verify multi-page output, repeated headers, and final-page footer placement.

## Exclusions

- No invoice model or migration changes.
- No changes to invoice creation, travel calculation, numbering, status, or download filename.
- No redesign of the approved header, participant, Sent To, line-item columns, or payment content.
- No automatic page numbers in this phase unless required to identify continuation pages safely.

## Verification

- A short invoice remains one page.
- The reproduced eight-line invoice produces more than one page.
- Every source line item appears exactly once.
- No line item occupies the reserved Total or Payment Details area.
- Table headers repeat on continuation pages.
- Invoice Total and Payment Details appear once on the final page.
- `invoices.tests_exports`, `invoices.tests_invoices`, and `manage.py check` pass.
- Rendered PNGs of both a short and a multi-page PDF show no overlaps, clipping, or unreadable text.
