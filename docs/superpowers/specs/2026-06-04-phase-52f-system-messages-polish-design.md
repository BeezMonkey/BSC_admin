# Phase 52F System Messages Polish Design

## Goal
Show existing Django success, error, warning, and info messages consistently in the admin and worker shells.

## Scope
This phase renders and styles messages that views already create through `django.contrib.messages`.

Included:

- Admin shell message display
- Worker shell message display
- Shared alert styling for success, error, warning, and info
- A regression test proving an existing success message is visible after redirect

## Safety Rules
This phase must not create new business messages, alter existing message text, change redirects, change forms, alter models, change permissions, or copy external template code.

## Implementation
Add the same message block below the topbar in `templates/admin_base.html` and `templates/worker_base.html`. Style the shared `.messages` and `.message` selectors in `static/css/app.css`.

## Testing
Use an existing participant create flow because it already sets `messages.success(request, "Participant created.")`. The test should submit a valid participant, follow the redirect, and assert the message is rendered with a success class.
