from datetime import date, datetime, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from participants.models import Participant
from scheduling import models as scheduling_models
from scheduling.models import Shift, SupportItem
from workers.models import SupportWorker


User = get_user_model()


class ParticipantCancellationModelTests(TestCase):
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
