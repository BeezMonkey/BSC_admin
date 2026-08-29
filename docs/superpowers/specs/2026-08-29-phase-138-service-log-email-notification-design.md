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

### Production SMTP Provider

Production email delivery was tested with Brevo SMTP on 2026-08-29 after Microsoft 365 SMTP AUTH continued to reject application password login with `basic authentication is disabled`.

Render should use these non-secret values:

```text
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_HOST_USER=b71535001@smtp-brevo.com
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=admin@brisbanestarcare.com.au
ADMIN_NOTIFICATION_EMAILS=kun-bi@hotmail.com
BSC_ADMIN_BASE_URL=https://admin.bscare.com.au
```

`EMAIL_HOST_PASSWORD` is the Brevo SMTP key generated in Brevo and must stay secret. Do not commit it to the repository.

The sender `admin@brisbanestarcare.com.au` is verified in Brevo. The domain still needs full DKIM/DMARC authentication in Brevo for stronger deliverability and fewer sender warning banners in Outlook.

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

Production smoke test completed on 2026-08-29:

- worker submitted a service log in the Render beta environment;
- `kun-bi@hotmail.com` received the notification email;
- the message showed `admin@brisbanestarcare.com.au` as the sender through Brevo;
- the admin review link pointed to `https://admin.bscare.com.au/service-logs/<id>/`.
