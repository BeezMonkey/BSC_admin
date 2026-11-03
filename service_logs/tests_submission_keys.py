from datetime import date
from urllib.parse import urlencode
from unittest.mock import patch
from unittest import skipUnless
from threading import Barrier, Thread

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from core.models import AuditLog
from documents.models import Document
from documents.storage import StorageOperationError
from participants.models import ParticipantWorkerAssignment

from .models import ServiceLog
from .notifications import notify_admin_service_log_submitted
from . import tests_service_logs as fixtures


TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=TEST_STORAGES)
class UnscheduledSubmissionKeyTests(TestCase):
    create_user_with_role = fixtures.ServiceLogCompletionTests.create_user_with_role
    create_shift = fixtures.ServiceLogCompletionTests.create_shift
    log_payload = fixtures.ServiceLogCompletionTests.log_payload

    def setUp(self):
        fixtures.ServiceLogCompletionTests.setUp(self)
        ParticipantWorkerAssignment.objects.create(
            participant=self.participant, worker=self.worker,
            start_date=date(2026, 1, 1), is_active=True,
        )
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.worker_user)
        self.url = reverse("worker_unscheduled_service_log_create")

    def token(self, response):
        self.assertEqual(response.status_code, 200)
        token = response.context.get("submission_token")
        self.assertTrue(token, "The real form must carry a submission identity")
        self.assertContains(response, 'name="submission_token"')
        return token

    def start(self):
        return self.token(self.client.get(self.url))

    def payload(self, token, attachment=False, **overrides):
        data = self.log_payload(
            participant=self.participant.pk, service_date="2026-06-02",
            support_item=self.support_item.pk, service_type="personal_care",
            unscheduled_reason="Fictional submission-key review.",
        )
        data.update(submission_token=token, case_notes="Fictional same-submission test.")
        data.update(overrides)
        if attachment:
            data["attachments"] = SimpleUploadedFile(
                "fictional.pdf", b"%PDF-1.4\n% Fictional local test only\n", "application/pdf",
            )
        return data

    def post(self, token, attachment=False, **overrides):
        return self.client.post(
            self.url, self.payload(token, attachment, **overrides),
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )

    def test_form_identity_survives_refresh(self):
        token = self.start()
        self.assertEqual(self.token(self.client.get(self.url)), token)

    def test_malformed_or_foreign_get_identity_is_a_controlled_rejection(self):
        self.start()
        response = self.client.get(self.url, {"submission": "invalid-signed-identity"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ServiceLog.objects.count(), 0)

    def test_same_saved_submission_returns_original_without_duplicate(self):
        token = self.start()
        first = self.post(token)
        self.assertEqual(first.status_code, 302)
        second = self.post(token)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(second.url, first.url)
        self.assertEqual(ServiceLog.objects.count(), 1)
        self.assertEqual(self.worker.shifts.count(), 1)

    def test_repeat_does_not_upload_audit_or_notify_again(self):
        token = self.start()
        with patch("service_logs.views.notify_admin_service_log_submitted", wraps=notify_admin_service_log_submitted) as notify:
            first = self.post(token, attachment=True)
            self.assertEqual(first.status_code, 302)
            audits = AuditLog.objects.count()
            with patch("service_logs.views.append_service_log_attachments", side_effect=AssertionError("Duplicate must not upload")):
                second = self.post(token, attachment=True)
            self.assertEqual(second.url, first.url)
            self.assertEqual(notify.call_count, 1)
        self.assertEqual(ServiceLog.objects.count(), 1)
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(AuditLog.objects.count(), audits)

    def test_returning_after_unseen_success_resumes_saved_record(self):
        token = self.start()
        first = self.post(token)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, first.url)
        self.assertEqual(ServiceLog.objects.count(), 1)

    def test_detail_get_does_not_discard_retry_identity(self):
        token = self.start()
        first = self.post(token)
        self.assertEqual(self.client.get(first.url).status_code, 200)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, first.url)

    def test_explicit_new_allows_identical_content_and_times(self):
        old = self.start()
        first = self.post(old, attachment=True)
        response = self.client.get(self.url + "?new=1")
        self.assertEqual(response.status_code, 302)
        new = self.token(self.client.get(response.url))
        self.assertNotEqual(new, old)
        second = self.post(new, attachment=True)
        self.assertEqual(second.status_code, 302)
        self.assertNotEqual(second.url, first.url)
        self.assertEqual(ServiceLog.objects.count(), 2)
        self.assertEqual(Document.objects.count(), 2)
        self.assertEqual(self.post(old).url, first.url)
        self.assertEqual(ServiceLog.objects.count(), 2)

    def test_new_attempt_redirect_keeps_its_identity_when_another_tab_starts(self):
        self.start()
        tab_a = self.client.get(self.url + "?new=1")
        tab_b = self.client.get(self.url + "?new=1")
        self.assertEqual(tab_a.status_code, 302)
        self.assertEqual(tab_b.status_code, 302)
        token_a = self.token(self.client.get(tab_a.url))
        token_b = self.token(self.client.get(tab_b.url))
        self.assertNotEqual(token_a, token_b)
        self.assertEqual(self.token(self.client.get(tab_a.url)), token_a)
        self.assertNotEqual(self.post(token_a).url, self.post(token_b).url)
        self.assertEqual(ServiceLog.objects.count(), 2)

    def test_invalid_tokenless_recovery_does_not_borrow_saved_attempt(self):
        saved_token = self.start()
        first = self.post(saved_token)
        data = self.payload(saved_token, case_notes="")
        del data["submission_token"]
        response = self.client.post(
            self.url, data, HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )
        recovery_token = self.token(response)
        self.assertNotEqual(recovery_token, saved_token)
        corrected = self.post(recovery_token)
        self.assertEqual(corrected.status_code, 302)
        self.assertNotEqual(corrected.url, first.url)
        self.assertEqual(ServiceLog.objects.count(), 2)

    def test_replaying_saved_attempt_does_not_replace_new_pending_attempt(self):
        old = self.start()
        first = self.post(old)
        started = self.client.get(self.url + "?new=1")
        pending = self.token(self.client.get(started.url))
        self.assertEqual(self.post(old).url, first.url)
        self.assertEqual(self.token(self.client.get(self.url)), pending)
        self.assertNotEqual(self.post(pending).url, first.url)
        self.assertEqual(ServiceLog.objects.count(), 2)

    def test_invalid_business_fields_keep_token_and_values_then_retry(self):
        token = self.start()
        bad = self.post(token, case_notes="")
        self.assertEqual(self.token(bad), token)
        self.assertIn("case_notes", bad.context["form"].errors)
        self.assertEqual(ServiceLog.objects.count(), 0)
        self.assertEqual(self.post(token).status_code, 302)
        self.assertEqual(ServiceLog.objects.count(), 1)

    def test_storage_rollback_keeps_token_and_retry_can_save(self):
        token = self.start()
        with patch("service_logs.views.append_service_log_attachments", side_effect=StorageOperationError("Fictional refusal")):
            bad = self.post(token, attachment=True)
        self.assertEqual(self.token(bad), token)
        self.assertEqual(ServiceLog.objects.count(), 0)
        self.assertEqual(self.worker.shifts.count(), 0)
        self.assertEqual(self.post(token, attachment=True).status_code, 302)
        self.assertEqual(Document.objects.count(), 1)

    def test_altered_retry_never_overwrites_saved_record(self):
        token = self.start()
        first = self.post(token)
        second = self.post(token, case_notes="", actual_end_time="08:00")
        self.assertEqual(second.status_code, 302)
        self.assertEqual(second.url, first.url)
        self.assertEqual(ServiceLog.objects.get().case_notes, "Fictional same-submission test.")

    def test_reviewed_saved_record_is_not_resubmitted(self):
        token = self.start()
        first = self.post(token)
        ServiceLog.objects.update(status=ServiceLog.Status.APPROVED)
        self.assertEqual(self.post(token).url, first.url)
        self.assertEqual(ServiceLog.objects.get().status, ServiceLog.Status.APPROVED)

    def test_missing_tampered_or_foreign_tokens_do_not_save_or_disclose(self):
        token = self.start()
        for supplied in [None, "not-a-valid-token", token + "forged"]:
            payload = self.payload(token)
            if supplied is None:
                del payload["submission_token"]
            else:
                payload["submission_token"] = supplied
            response = self.client.post(self.url, payload, HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(ServiceLog.objects.count(), 0)
            self.assertEqual(response.context["form"]["case_notes"].value(), payload["case_notes"])
        self.assertEqual(self.post(token).status_code, 302)
        self.client.force_login(self.other_worker_user)
        self.client.get(self.url)
        response = self.post(token)
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Location", response)
        self.assertEqual(ServiceLog.objects.count(), 1)

    def test_csrf_and_scheduled_path_remain_unchanged(self):
        token = self.start()
        self.assertEqual(self.client.post(self.url, self.payload(token)).status_code, 403)
        shift = self.create_shift()
        url = reverse("worker_service_log_create", args=[shift.pk])
        self.client.get(url)
        response = self.client.post(url, self.log_payload(), HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.post(url, self.log_payload(), HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value).status_code, 404)

    def test_unique_key_is_database_enforced_and_legacy_null_rows_remain_allowed(self):
        fields = {field.name for field in ServiceLog._meta.fields}
        self.assertIn("submission_key", fields)
        token = self.start()
        self.post(token)
        key = ServiceLog.objects.get().submission_key
        other_shift = self.create_shift()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ServiceLog.objects.create_from_shift(shift=other_shift, submission_key=key,
                actual_start_time="09:00", actual_end_time="11:00", break_minutes=0,
                actual_hours="2.00", case_notes="Duplicate key must fail")
        for _ in range(2):
            ServiceLog.objects.create_from_shift(shift=self.create_shift(),
                actual_start_time="09:00", actual_end_time="11:00", break_minutes=0,
                actual_hours="2.00", case_notes="Legacy unkeyed row remains supported")
        self.assertEqual(ServiceLog.objects.filter(submission_key__isnull=True).count(), 2)

    def test_attachment_integrity_error_is_not_mistaken_for_duplicate_success(self):
        token = self.start()
        with patch("service_logs.views.append_service_log_attachments", side_effect=IntegrityError("Unrelated audit constraint")):
            with self.assertRaises(IntegrityError):
                self.post(token, attachment=True)
        self.assertEqual(ServiceLog.objects.count(), 0)
        self.assertEqual(self.worker.shifts.count(), 0)


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL competing unique inserts")
@override_settings(STORAGES=TEST_STORAGES)
class UnscheduledSubmissionPostgresTests(TransactionTestCase):
    create_user_with_role = fixtures.ServiceLogCompletionTests.create_user_with_role
    create_shift = fixtures.ServiceLogCompletionTests.create_shift
    log_payload = fixtures.ServiceLogCompletionTests.log_payload

    def setUp(self):
        fixtures.ServiceLogCompletionTests.setUp(self)
        ParticipantWorkerAssignment.objects.create(participant=self.participant, worker=self.worker,
            start_date=date(2026, 1, 1), is_active=True)

    def test_competing_same_submission_saves_one_shift_log_and_attachment(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.worker_user)
        url = reverse("worker_unscheduled_service_log_create")
        token = client.get(url).context["submission_token"]
        self.assertTrue(token)
        barrier = Barrier(2, timeout=10)
        statuses, locations, errors = [], [], []
        original = type(ServiceLog.objects).create_from_shift

        def competing_insert(manager, shift, **kwargs):
            barrier.wait()
            return original(manager, shift, **kwargs)

        def submit():
            close_old_connections()
            try:
                request_client = Client(enforce_csrf_checks=True)
                request_client.cookies = client.cookies.copy()
                payload = self.log_payload(participant=self.participant.pk,
                    service_date="2026-06-02", support_item=self.support_item.pk,
                    service_type="personal_care", unscheduled_reason="Fictional race.",
                    submission_token=token,
                    attachments=SimpleUploadedFile("race.pdf", b"%PDF-1.4\n% Fictional only\n", "application/pdf"))
                response = request_client.post(url, payload, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
                statuses.append(response.status_code)
                locations.append(response.get("Location"))
            except Exception as exc:
                errors.append(repr(exc))
            finally:
                close_old_connections()

        with patch.object(type(ServiceLog.objects), "create_from_shift", competing_insert), \
                patch("service_logs.views.notify_admin_service_log_submitted", wraps=notify_admin_service_log_submitted) as notify:
            threads = [Thread(target=submit, daemon=True) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=20)
            self.assertFalse(any(thread.is_alive() for thread in threads), "Competing requests did not finish")
            self.assertEqual(errors, [])
            self.assertEqual(statuses, [302, 302])
            self.assertEqual(len(set(locations)), 1)
            self.assertEqual(notify.call_count, 1)
        self.assertEqual(ServiceLog.objects.count(), 1)
        self.assertEqual(self.worker.shifts.count(), 1)
        self.assertEqual(Document.objects.count(), 1)
