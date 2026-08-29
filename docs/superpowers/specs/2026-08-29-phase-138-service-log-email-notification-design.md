# Phase 138: Service Log Email Notification

Notify the admin team when a support worker submits a completed service log.

## Scope

- Send one internal email after a worker successfully submits a service log.
- Keep the worker submission flow unchanged.
- Do not send participant or worker-facing emails in this phase.
- Do not include case notes in the email body.

## Trigger

The notification is sent from the worker service log submission flow after:

- the `ServiceLog` record is created;
- the related shift is marked `Completed`.

If email delivery fails, the service log submission still succeeds and the failure is logged.

## Configuration

The recipient list is environment-driven:

```text
ADMIN_NOTIFICATION_EMAILS=kun-bi@hotmail.com
```

The admin review link uses:

```text
BSC_ADMIN_BASE_URL=https://admin.bscare.com.au
```

The sender and SMTP connection are configured through Django email environment variables such as `DEFAULT_FROM_EMAIL`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `EMAIL_USE_SSL`.

## Email Content

The email includes:

- participant name;
- worker name;
- service date;
- actual time;
- actual hours;
- kilometres;
- a link to review the submitted service log in the admin portal.

## Testing

Tests cover:

- an email is sent to configured admin recipients when a worker submits a service log;
- the admin link uses `BSC_ADMIN_BASE_URL`;
- the worker submission still completes if the email backend fails.
