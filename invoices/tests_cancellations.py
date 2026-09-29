from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from invoices import views as invoice_views
from invoices.models import Invoice, InvoiceLine
from participants.models import Participant
from scheduling.models import ParticipantCancellation, Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


User = get_user_model()


class ParticipantCancellationInvoiceTests(TestCase):
    def create_user(self, username, role):
        user = User.objects.create_user(
            username=username,
            password="test-password",
            email=f"{username}@example.com",
        )
        UserProfile.objects.create(
            user=user,
            role=role,
            is_active_worker=role == UserProfile.Role.SUPPORT_WORKER,
        )
        return user

    def setUp(self):
        self.admin_user = self.create_user("admin.cancel.invoice", UserProfile.Role.ADMIN)
        self.accountant_user = self.create_user(
            "accountant.cancel.invoice",
            UserProfile.Role.ACCOUNTANT,
        )
        self.worker_user = self.create_user(
            "worker.cancel.invoice",
            UserProfile.Role.SUPPORT_WORKER,
        )
        self.participant = Participant.objects.create(
            first_name="Julie",
            last_name="Steinback",
            ndis_number="431211998",
            status=Participant.Status.ACTIVE,
        )
        self.worker = SupportWorker.objects.create(
            user=self.worker_user,
            first_name="Cristhian",
            last_name="Caceres",
            email="worker.cancel.invoice@example.com",
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
            status=Shift.Status.CANCELLED,
            created_by=self.admin_user,
        )
        self.private_details = "Participant reported a private health matter."
        self.cancellation = ParticipantCancellation.objects.create(
            shift=self.shift,
            cancellation_type=ParticipantCancellation.CancellationType.SHORT_NOTICE,
            reason=ParticipantCancellation.Reason.HEALTH,
            details=self.private_details,
            received_at=timezone.now(),
            previous_shift_status=Shift.Status.CONFIRMED,
            status=ParticipantCancellation.Status.APPROVED,
            admin_note="Service agreement checked.",
            submitted_by=self.worker_user,
            reviewed_by=self.admin_user,
            reviewed_at=timezone.now(),
        )

    def create_invoice(self, status=Invoice.Status.DRAFT):
        return Invoice.objects.create(
            participant=self.participant,
            period_start=self.shift.service_date,
            period_end=self.shift.service_date,
            status=status,
            created_by=self.accountant_user,
        )

    def create_service_log(self):
        service_shift = Shift.objects.create(
            participant=self.participant,
            worker=self.worker,
            service_date=self.shift.service_date,
            start_time=time(13, 0),
            end_time=time(14, 30),
            planned_hours=Decimal("1.50"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        service_log = ServiceLog.objects.create_from_shift(
            shift=service_shift,
            actual_start_time=service_shift.start_time,
            actual_end_time=service_shift.end_time,
            break_minutes=0,
            actual_hours=Decimal("1.50"),
            kilometres=Decimal("0.00"),
            case_notes="Completed afternoon support.",
            worker_notes="",
        )
        service_log.status = ServiceLog.Status.APPROVED
        service_log.save(update_fields=["status", "updated_at"])
        return service_log

    def create_cancellation_for_participant(self, participant, service_date):
        shift = Shift.objects.create(
            participant=participant,
            worker=self.worker,
            service_date=service_date,
            start_time=time(9, 0),
            end_time=time(10, 0),
            planned_hours=Decimal("1.00"),
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.CANCELLED,
            created_by=self.admin_user,
        )
        return ParticipantCancellation.objects.create(
            shift=shift,
            cancellation_type=ParticipantCancellation.CancellationType.SHORT_NOTICE,
            reason=ParticipantCancellation.Reason.OTHER,
            details="Participant cancelled.",
            received_at=timezone.now(),
            previous_shift_status=Shift.Status.CONFIRMED,
            status=ParticipantCancellation.Status.APPROVED,
            admin_note="Approved for billing.",
            submitted_by=self.worker_user,
            reviewed_by=self.admin_user,
            reviewed_at=timezone.now(),
        )

    def test_line_uses_rostered_quantity_rate_and_normal_description(self):
        invoice = self.create_invoice()

        line = InvoiceLine.objects.create_from_participant_cancellation(
            invoice=invoice,
            cancellation=self.cancellation,
        )

        self.assertEqual(line.participant_cancellation, self.cancellation)
        self.assertEqual(line.line_type, InvoiceLine.LineType.CANCELLATION)
        self.assertEqual(line.quantity, self.shift.planned_hours)
        self.assertEqual(line.unit_price, self.support_item.price_limit)
        self.assertEqual(line.description, self.support_item.name)
        self.assertEqual(line.line_total, Decimal("130.94"))

    def test_cancellation_can_only_be_invoiced_once(self):
        first_invoice = self.create_invoice()
        second_invoice = self.create_invoice()
        InvoiceLine.objects.create_from_participant_cancellation(
            invoice=first_invoice,
            cancellation=self.cancellation,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            InvoiceLine.objects.create_from_participant_cancellation(
                invoice=second_invoice,
                cancellation=self.cancellation,
            )

    def test_only_approved_uninvoiced_cancellation_is_billable(self):
        getter = getattr(invoice_views, "get_billable_cancellations", None)
        self.assertIsNotNone(getter)

        self.assertEqual(
            list(
                getter(
                    self.participant,
                    self.shift.service_date,
                    self.shift.service_date,
                )
            ),
            [self.cancellation],
        )
        invoice = self.create_invoice()
        InvoiceLine.objects.create_from_participant_cancellation(
            invoice=invoice,
            cancellation=self.cancellation,
        )
        self.assertFalse(
            getter(
                self.participant,
                self.shift.service_date,
                self.shift.service_date,
            ).exists()
        )

    def test_invoice_create_supports_cancellation_only(self):
        self.client.force_login(self.accountant_user)

        response = self.client.post(
            reverse("invoice_create"),
            {
                "participant": self.participant.id,
                "period_start": "2026-09-28",
                "period_end": "2026-09-28",
            },
        )

        invoice = Invoice.objects.get()
        self.assertRedirects(response, invoice.get_absolute_url())
        self.assertEqual(invoice.lines.count(), 1)
        self.assertEqual(
            invoice.lines.get().participant_cancellation,
            self.cancellation,
        )

    def test_invoice_create_combines_service_log_and_cancellation(self):
        service_log = self.create_service_log()
        self.client.force_login(self.accountant_user)

        response = self.client.post(
            reverse("invoice_create"),
            {
                "participant": self.participant.id,
                "period_start": "2026-09-28",
                "period_end": "2026-09-28",
                f"travel-{service_log.id}-amount": "0.00",
            },
        )

        invoice = Invoice.objects.get()
        self.assertRedirects(response, invoice.get_absolute_url())
        self.assertEqual(invoice.lines.count(), 2)
        self.assertTrue(invoice.lines.filter(service_log=service_log).exists())
        self.assertTrue(
            invoice.lines.filter(participant_cancellation=self.cancellation).exists()
        )

    def test_selected_cancellation_only_opens_invoice_preview(self):
        self.client.force_login(self.accountant_user)

        response = self.client.get(
            reverse("invoice_create"),
            {"participant_cancellation_ids": self.cancellation.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["selected_participant_cancellation_ids"],
            [str(self.cancellation.id)],
        )
        self.assertContains(response, "Approved rostered charge")
        self.assertContains(
            response,
            f'name="participant_cancellation_ids" value="{self.cancellation.id}"',
            html=False,
        )

    def test_selected_service_log_and_cancellation_open_combined_preview(self):
        service_log = self.create_service_log()
        self.client.force_login(self.accountant_user)

        response = self.client.get(
            reverse("invoice_create"),
            {
                "service_log_ids": service_log.id,
                "participant_cancellation_ids": self.cancellation.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["invoice_rows"]), 2)
        self.assertContains(response, "Completed afternoon support.")
        self.assertContains(response, "Approved rostered charge")

    def test_selected_service_log_and_cancellation_create_one_combined_invoice(self):
        service_log = self.create_service_log()
        self.client.force_login(self.accountant_user)

        response = self.client.post(
            reverse("invoice_create"),
            {
                "participant": self.participant.id,
                "period_start": "2026-09-28",
                "period_end": "2026-09-28",
                "service_log_ids": service_log.id,
                "participant_cancellation_ids": self.cancellation.id,
                f"travel-{service_log.id}-amount": "0.00",
            },
        )

        invoice = Invoice.objects.get()
        self.assertRedirects(response, invoice.get_absolute_url())
        self.assertEqual(invoice.lines.count(), 2)
        self.assertTrue(invoice.lines.filter(service_log=service_log).exists())
        self.assertTrue(
            invoice.lines.filter(participant_cancellation=self.cancellation).exists()
        )

    def test_explicit_service_log_selection_does_not_add_unselected_cancellation(self):
        service_log = self.create_service_log()
        self.client.force_login(self.accountant_user)

        response = self.client.post(
            reverse("invoice_create"),
            {
                "participant": self.participant.id,
                "period_start": "2026-09-28",
                "period_end": "2026-09-28",
                "service_log_ids": service_log.id,
                f"travel-{service_log.id}-amount": "0.00",
            },
        )

        invoice = Invoice.objects.get()
        self.assertRedirects(response, invoice.get_absolute_url())
        self.assertEqual(invoice.lines.count(), 1)
        self.assertTrue(invoice.lines.filter(service_log=service_log).exists())
        self.assertFalse(invoice.lines.filter(participant_cancellation__isnull=False).exists())

    def test_stale_selected_cancellation_is_rejected(self):
        self.cancellation.status = ParticipantCancellation.Status.REJECTED
        self.cancellation.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.accountant_user)

        response = self.client.post(
            reverse("invoice_create"),
            {
                "participant": self.participant.id,
                "period_start": "2026-09-28",
                "period_end": "2026-09-28",
                "participant_cancellation_ids": self.cancellation.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Selected cancellation charges are no longer available for invoicing.",
        )
        self.assertFalse(Invoice.objects.exists())

    def test_selected_cancellations_for_multiple_participants_are_grouped(self):
        other_participant = Participant.objects.create(
            first_name="Haylie",
            last_name="Taylor",
            ndis_number="431038153",
            status=Participant.Status.ACTIVE,
        )
        other_cancellation = self.create_cancellation_for_participant(
            other_participant,
            date(2026, 9, 29),
        )
        self.client.force_login(self.accountant_user)

        response = self.client.get(
            reverse("invoice_create"),
            {
                "participant_cancellation_ids": [
                    self.cancellation.id,
                    other_cancellation.id,
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["selected_invoice_groups"]), 2)
        self.assertContains(response, self.participant.display_name)
        self.assertContains(response, other_participant.display_name)

    def test_cancelling_invoice_releases_cancellation_for_rebilling(self):
        invoice = self.create_invoice()
        InvoiceLine.objects.create_from_participant_cancellation(
            invoice=invoice,
            cancellation=self.cancellation,
        )
        self.client.force_login(self.accountant_user)

        response = self.client.post(reverse("invoice_cancel", args=[invoice.id]))

        self.assertRedirects(response, invoice.get_absolute_url())
        self.assertFalse(InvoiceLine.objects.filter(invoice=invoice).exists())
        getter = getattr(invoice_views, "get_billable_cancellations", None)
        self.assertIsNotNone(getter)
        self.assertTrue(
            getter(
                self.participant,
                self.shift.service_date,
                self.shift.service_date,
            ).filter(id=self.cancellation.id).exists()
        )

    def test_pdf_uses_normal_item_and_hides_cancellation_metadata(self):
        invoice = self.create_invoice()
        InvoiceLine.objects.create_from_participant_cancellation(
            invoice=invoice,
            cancellation=self.cancellation,
        )
        self.client.force_login(self.accountant_user)

        response = self.client.get(reverse("invoice_pdf", args=[invoice.id]))
        content = response.content.decode("latin-1")

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.support_item.name, content)
        self.assertIn(self.support_item.item_number, content)
        self.assertNotIn("CANC", content)
        self.assertNotIn("Short notice", content)
        self.assertNotIn(self.private_details, content)
