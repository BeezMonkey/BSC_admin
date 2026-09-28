from datetime import date, datetime, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from core.models import AuditLog
from participants.models import Participant
from scheduling import models as scheduling_models
from scheduling.models import ParticipantCancellation, Shift, SupportItem
from workers.models import SupportWorker


User = get_user_model()


class ParticipantCancellationTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="worker.cancellation",
            password="test-password",
        )
        UserProfile.objects.create(
            user=self.user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        self.worker = SupportWorker.objects.create(
            user=self.user,
            first_name="Cristhian",
            last_name="Caceres",
            email="worker@example.com",
        )
        self.participant = Participant.objects.create(
            first_name="Julie",
            last_name="Steinback",
            ndis_number="431211998",
        )
        self.support_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Assistance With Self-Care Activities",
            price_limit=Decimal("65.47"),
            unit=SupportItem.Unit.HOUR,
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        self.shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=date(2026, 9, 28),
            start_time=time(10, 0),
            end_time=time(12, 0),
            planned_hours=Decimal("2.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.CONFIRMED,
            created_by=self.user,
        )

    def get_model(self):
        model = getattr(scheduling_models, "ParticipantCancellation", None)
        self.assertIsNotNone(model, "ParticipantCancellation model is required")
        return model

    def cancellation_values(self):
        model = self.get_model()
        return {
            "shift": self.shift,
            "cancellation_type": model.CancellationType.SHORT_NOTICE,
            "reason": model.Reason.HEALTH,
            "details": "Participant became unwell before the shift.",
            "received_at": timezone.make_aware(datetime(2026, 9, 28, 9, 30)),
            "previous_shift_status": Shift.Status.CONFIRMED,
            "submitted_by": self.user,
        }


class ParticipantCancellationModelTests(ParticipantCancellationTestBase):
    def test_model_records_internal_cancellation_claim_data(self):
        model = self.get_model()

        cancellation = model.objects.create(**self.cancellation_values())

        self.assertEqual(cancellation.claim_type, "CANC")
        self.assertEqual(cancellation.status, model.Status.PENDING)
        self.assertEqual(cancellation.shift, self.shift)

    def test_only_one_cancellation_can_be_recorded_for_a_shift(self):
        model = self.get_model()
        values = self.cancellation_values()
        model.objects.create(**values)

        with self.assertRaises(IntegrityError), transaction.atomic():
            model.objects.create(**values)

    def test_choices_keep_worker_and_admin_states_explicit(self):
        model = self.get_model()

        self.assertEqual(
            set(model.CancellationType.values),
            {"short_notice", "no_show"},
        )
        self.assertEqual(
            set(model.Reason.values),
            {"health", "family", "transport", "other"},
        )
        self.assertEqual(
            set(model.Status.values),
            {"pending", "approved", "waived", "rejected"},
        )

    def test_shift_has_cancellation_review_status(self):
        self.assertEqual(Shift.Status.CANCELLATION_REVIEW, "cancellation_review")


class WorkerCancellationFlowTests(ParticipantCancellationTestBase):
    def setUp(self):
        super().setUp()
        self.other_user = User.objects.create_user(
            username="other.worker",
            password="test-password",
        )
        UserProfile.objects.create(
            user=self.other_user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        self.other_worker = SupportWorker.objects.create(
            user=self.other_user,
            first_name="Other",
            last_name="Worker",
            email="other.worker@example.com",
        )

    def submission_payload(self, **overrides):
        payload = {
            "cancellation_type": ParticipantCancellation.CancellationType.SHORT_NOTICE,
            "reason": ParticipantCancellation.Reason.HEALTH,
            "details": "Participant called to cancel before the shift.",
            "received_at": "2026-09-28T09:30",
        }
        payload.update(overrides)
        return payload

    def test_assigned_worker_can_open_cancellation_form(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("worker_participant_cancellation_create", args=[self.shift.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Report Participant Cancellation")
        self.assertContains(response, self.participant.display_name)

    def test_assigned_worker_submits_participant_cancellation(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("worker_participant_cancellation_create", args=[self.shift.id]),
            self.submission_payload(),
        )

        self.assertRedirects(
            response,
            reverse("worker_shift_detail", args=[self.shift.id]),
        )
        cancellation = ParticipantCancellation.objects.get(shift=self.shift)
        self.assertEqual(cancellation.previous_shift_status, Shift.Status.CONFIRMED)
        self.assertEqual(cancellation.submitted_by, self.user)
        self.shift.refresh_from_db()
        self.assertEqual(self.shift.status, Shift.Status.CANCELLATION_REVIEW)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.PARTICIPANT_CANCELLATION_SUBMITTED,
                object_type="ParticipantCancellation",
                object_id=str(cancellation.id),
                actor=self.user,
            ).exists()
        )

    def test_details_are_required(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("worker_participant_cancellation_create", args=[self.shift.id]),
            self.submission_payload(details=""),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required.")
        self.assertFalse(ParticipantCancellation.objects.exists())
        self.shift.refresh_from_db()
        self.assertEqual(self.shift.status, Shift.Status.CONFIRMED)

    def test_unassigned_worker_cannot_report_cancellation(self):
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse("worker_participant_cancellation_create", args=[self.shift.id]),
            self.submission_payload(),
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ParticipantCancellation.objects.exists())

    def test_unscheduled_shift_cannot_use_cancellation_workflow(self):
        self.shift.source = Shift.Source.UNSCHEDULED
        self.shift.save(update_fields=["source", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("worker_participant_cancellation_create", args=[self.shift.id]),
            self.submission_payload(),
        )

        self.assertEqual(response.status_code, 404)

    def test_duplicate_cancellation_is_blocked(self):
        ParticipantCancellation.objects.create(**self.cancellation_values())
        self.shift.status = Shift.Status.CANCELLATION_REVIEW
        self.shift.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("worker_participant_cancellation_create", args=[self.shift.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_pending_cancellation_blocks_service_log_creation(self):
        ParticipantCancellation.objects.create(**self.cancellation_values())
        self.shift.status = Shift.Status.CANCELLATION_REVIEW
        self.shift.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("worker_service_log_create", args=[self.shift.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_shift_detail_replaces_actions_with_review_message(self):
        ParticipantCancellation.objects.create(**self.cancellation_values())
        self.shift.status = Shift.Status.CANCELLATION_REVIEW
        self.shift.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("worker_shift_detail", args=[self.shift.id]))

        self.assertContains(response, "Cancellation awaiting admin review")
        self.assertNotContains(response, "Complete Service Log")


class AdminCancellationReviewTests(ParticipantCancellationTestBase):
    def setUp(self):
        super().setUp()
        self.admin_user = User.objects.create_user(
            username="cancellation.admin",
            password="test-password",
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=UserProfile.Role.ADMIN,
        )
        self.cancellation = ParticipantCancellation.objects.create(
            **self.cancellation_values()
        )
        self.shift.status = Shift.Status.CANCELLATION_REVIEW
        self.shift.save(update_fields=["status", "updated_at"])

    def test_admin_queue_lists_pending_cancellation(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("participant_cancellation_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Participant Cancellations")
        self.assertContains(response, self.participant.display_name)
        self.assertEqual(
            list(response.context["pending_cancellations"]),
            [self.cancellation],
        )

    def test_worker_cannot_open_admin_queue(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("participant_cancellation_list"))

        self.assertEqual(response.status_code, 403)

    def test_admin_approves_chargeable_cancellation(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("participant_cancellation_approve", args=[self.cancellation.id]),
            {"admin_note": "Service agreement checked."},
        )

        self.assertRedirects(response, reverse("participant_cancellation_list"))
        self.cancellation.refresh_from_db()
        self.shift.refresh_from_db()
        self.assertEqual(
            self.cancellation.status,
            ParticipantCancellation.Status.APPROVED,
        )
        self.assertEqual(self.cancellation.admin_note, "Service agreement checked.")
        self.assertEqual(self.cancellation.reviewed_by, self.admin_user)
        self.assertIsNotNone(self.cancellation.reviewed_at)
        self.assertEqual(self.shift.status, Shift.Status.CANCELLED)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.PARTICIPANT_CANCELLATION_APPROVED,
                object_id=str(self.cancellation.id),
                actor=self.admin_user,
            ).exists()
        )

    def test_admin_waives_charge(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("participant_cancellation_waive", args=[self.cancellation.id]),
            {"admin_note": "Waived as a goodwill adjustment."},
        )

        self.assertRedirects(response, reverse("participant_cancellation_list"))
        self.cancellation.refresh_from_db()
        self.shift.refresh_from_db()
        self.assertEqual(self.cancellation.status, ParticipantCancellation.Status.WAIVED)
        self.assertEqual(self.shift.status, Shift.Status.CANCELLED)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.PARTICIPANT_CANCELLATION_WAIVED,
                object_id=str(self.cancellation.id),
            ).exists()
        )

    def test_admin_rejects_and_restores_previous_shift_status(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("participant_cancellation_reject", args=[self.cancellation.id]),
            {"admin_note": "Worker confirmed the service still occurred."},
        )

        self.assertRedirects(response, reverse("participant_cancellation_list"))
        self.cancellation.refresh_from_db()
        self.shift.refresh_from_db()
        self.assertEqual(
            self.cancellation.status,
            ParticipantCancellation.Status.REJECTED,
        )
        self.assertEqual(self.shift.status, Shift.Status.CONFIRMED)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.PARTICIPANT_CANCELLATION_REJECTED,
                object_id=str(self.cancellation.id),
            ).exists()
        )

    def test_reviewed_cancellation_cannot_be_decided_again(self):
        self.cancellation.status = ParticipantCancellation.Status.APPROVED
        self.cancellation.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("participant_cancellation_reject", args=[self.cancellation.id]),
            {"admin_note": "Second decision."},
        )

        self.assertEqual(response.status_code, 404)
