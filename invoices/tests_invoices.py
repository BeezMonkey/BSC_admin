from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from invoices.models import Invoice, InvoiceLine, InvoiceSettings
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class InvoiceGenerationTests(TestCase):
    def create_user_with_role(self, username, role):
        user = get_user_model().objects.create_user(
            username=username,
            password="test-password-123",
            email=f"{username}@example.com",
        )
        UserProfile.objects.create(
            user=user,
            role=role,
            is_active_worker=role == UserProfile.Role.SUPPORT_WORKER,
        )
        return user

    def setUp(self):
        self.admin_user = self.create_user_with_role("admin", UserProfile.Role.ADMIN)
        self.accountant_user = self.create_user_with_role(
            "accountant",
            UserProfile.Role.ACCOUNTANT,
        )
        self.worker_user = self.create_user_with_role(
            "worker",
            UserProfile.Role.SUPPORT_WORKER,
        )
        self.participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
            address_line_1="10 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        self.other_participant = Participant.objects.create(
            first_name="Ben",
            last_name="Taylor",
            status=Participant.Status.ACTIVE,
            address_line_1="20 River Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        self.worker = SupportWorker.objects.create(
            user=self.worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        self.support_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Assistance with self-care activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )

    def create_service_log(self, **overrides):
        participant = overrides.pop("participant", self.participant)
        service_date = overrides.pop("service_date", date(2026, 6, 1))
        status = overrides.pop("status", ServiceLog.Status.APPROVED)
        actual_hours = overrides.pop("actual_hours", Decimal("2.00"))
        case_notes = overrides.pop("case_notes", f"Log for {participant.display_name}")
        shift = Shift.objects.create(
            participant=participant,
            worker=self.worker,
            service_date=service_date,
            start_time=time(9, 0),
            end_time=time(11, 0),
            break_minutes=0,
            planned_hours=actual_hours,
            support_item=self.support_item,
            service_type=Shift.ServiceType.PERSONAL_CARE,
            status=Shift.Status.COMPLETED,
            created_by=self.admin_user,
        )
        service_log = ServiceLog.objects.create_from_shift(
            shift=shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 0),
            break_minutes=0,
            actual_hours=actual_hours,
            kilometres=Decimal("0.0"),
            case_notes=case_notes,
            worker_notes="",
        )
        service_log.status = status
        service_log.save(update_fields=["status", "updated_at"])
        return service_log

    def login_accountant(self):
        self.client.login(username="accountant", password="test-password-123")

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def login_worker(self):
        self.client.login(username="worker", password="test-password-123")

    def test_admin_can_view_invoice_settings(self):
        self.login_admin()

        response = self.client.get(reverse("invoice_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invoice Settings")
        self.assertContains(response, "Business name")
        self.assertContains(response, "Invoice prefix")
        self.assertContains(response, "Logo")
        self.assertContains(
            response,
            f'class="sidebar-link active" href="{reverse("invoice_placeholder")}"',
        )

    def test_invoice_settings_logo_field_uses_compact_custom_layout(self):
        settings = InvoiceSettings.load()
        settings.logo.name = "invoice_settings/logos/BSC-Logo-h.png"
        settings.save(update_fields=["logo"])
        self.login_admin()

        response = self.client.get(reverse("invoice_settings"))

        self.assertContains(response, "Current logo")
        self.assertContains(response, "BSC-Logo-h.png")
        self.assertContains(response, "Remove current logo")
        self.assertContains(response, "invoice-logo-field")
        self.assertContains(response, "invoice-logo-placeholder")
        self.assertNotContains(response, "Currently:")
        self.assertNotContains(response, 'alt="Current logo"')

    def test_accountant_cannot_manage_invoice_settings(self):
        self.login_accountant()

        response = self.client.get(reverse("invoice_settings"))

        self.assertEqual(response.status_code, 403)

    def test_admin_can_update_invoice_settings(self):
        self.login_admin()
        logo = SimpleUploadedFile(
            "bsc-logo.png",
            b"fake image bytes",
            content_type="image/png",
        )

        response = self.client.post(
            reverse("invoice_settings"),
            {
                "business_name": "Brisbane Star Care",
                "abn": "36 601 940 023",
                "phone": "0455 102 973",
                "email": "admin@brisbanestarcare.com.au",
                "address": "Brisbane QLD",
                "bank_name": "Suncorp Australia",
                "account_name": "Brisbane Star Care",
                "bsb": "484 799",
                "account_number": "353 422 224",
                "invoice_prefix": "BSC",
                "next_invoice_sequence": "7",
                "accent_colour": "#6f2c80",
                "logo": logo,
            },
        )

        self.assertRedirects(response, reverse("invoice_settings"))
        settings = InvoiceSettings.load()
        self.assertEqual(settings.business_name, "Brisbane Star Care")
        self.assertEqual(settings.invoice_prefix, "BSC")
        self.assertEqual(settings.next_invoice_sequence, 7)
        self.assertTrue(settings.logo.name.startswith("invoice_settings/logos/"))

    def test_admin_can_remove_invoice_settings_logo(self):
        settings = InvoiceSettings.load()
        settings.logo.name = "invoice_settings/logos/BSC-Logo-h.png"
        settings.save(update_fields=["logo"])
        self.login_admin()

        response = self.client.post(
            reverse("invoice_settings"),
            {
                "business_name": "Brisbane Star Care",
                "abn": "36 601 940 023",
                "phone": "",
                "email": "",
                "address": "",
                "bank_name": "",
                "account_name": "",
                "bsb": "",
                "account_number": "",
                "invoice_prefix": "BSC",
                "next_invoice_sequence": "1",
                "accent_colour": "#6f2c80",
                "remove_logo": "on",
            },
        )

        self.assertRedirects(response, reverse("invoice_settings"))
        settings.refresh_from_db()
        self.assertEqual(settings.logo.name, "")

    def test_invoice_list_links_to_invoice_settings(self):
        self.login_admin()

        response = self.client.get(reverse("invoice_placeholder"))

        self.assertContains(response, reverse("invoice_settings"))
        self.assertContains(response, "Invoice Settings")

    def create_payload(self, **overrides):
        data = {
            "participant": self.participant.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-30",
        }
        data.update(overrides)
        return data

    def test_finance_user_can_preview_approved_uninvoiced_logs(self):
        self.create_service_log()
        self.create_service_log(status=ServiceLog.Status.SUBMITTED)
        self.create_service_log(participant=self.other_participant)
        self.login_accountant()

        response = self.client.get(reverse("invoice_create"), self.create_payload())

        self.assertContains(response, "Log for Ava Nguyen", count=1)
        self.assertNotContains(response, "Log for Ben Taylor")
        self.assertContains(response, "Create Invoice")

    def test_invoice_create_filter_uses_aligned_field_layout(self):
        self.login_accountant()

        response = self.client.get(reverse("invoice_create"))

        self.assertContains(response, 'class="filter-bar invoice-preview-filter"')
        self.assertNotContains(response, "<p>\n    <label")

    def test_invoice_create_wraps_approved_logs_table_for_small_screens(self):
        self.login_accountant()

        response = self.client.get(reverse("invoice_create"))

        self.assertContains(response, 'class="card table-card invoice-preview-table"')

    def test_finance_user_can_create_invoice_from_approved_logs(self):
        first_log = self.create_service_log(actual_hours=Decimal("2.00"))
        second_log = self.create_service_log(
            service_date=date(2026, 6, 2),
            actual_hours=Decimal("1.50"),
        )
        self.login_accountant()

        response = self.client.post(reverse("invoice_create"), self.create_payload())

        invoice = Invoice.objects.get()
        self.assertRedirects(response, reverse("invoice_detail", args=[invoice.id]))
        self.assertEqual(invoice.participant, self.participant)
        self.assertEqual(invoice.created_by, self.accountant_user)
        self.assertEqual(invoice.lines.count(), 2)
        self.assertEqual(invoice.total_amount, Decimal("229.15"))
        first_log.refresh_from_db()
        second_log.refresh_from_db()
        self.assertEqual(first_log.status, ServiceLog.Status.INVOICED)
        self.assertEqual(second_log.status, ServiceLog.Status.INVOICED)

    def test_invoice_line_preserves_support_item_values(self):
        service_log = self.create_service_log(actual_hours=Decimal("2.00"))
        self.login_accountant()

        self.client.post(reverse("invoice_create"), self.create_payload())

        line = InvoiceLine.objects.get(service_log=service_log)
        self.assertEqual(line.support_item_number, "01_011_0107_1_1")
        self.assertEqual(line.description, "Assistance with self-care activities")
        self.assertEqual(line.unit, SupportItem.Unit.HOUR)
        self.assertEqual(line.unit_price, Decimal("65.47"))
        self.assertEqual(line.quantity, Decimal("2.00"))
        self.assertEqual(line.line_total, Decimal("130.94"))

    def test_already_invoiced_logs_are_excluded(self):
        service_log = self.create_service_log()
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(invoice=invoice, service_log=service_log)
        service_log.status = ServiceLog.Status.INVOICED
        service_log.save(update_fields=["status", "updated_at"])
        self.login_accountant()

        response = self.client.get(reverse("invoice_create"), self.create_payload())

        self.assertNotContains(response, "Log for Ava Nguyen")
        self.assertContains(response, "No approved logs found")

    def test_worker_cannot_access_invoice_generation(self):
        self.login_worker()

        response = self.client.get(reverse("invoice_create"))

        self.assertEqual(response.status_code, 403)

    def test_invoice_list_has_explicit_view_action(self):
        service_log = self.create_service_log()
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(invoice=invoice, service_log=service_log)
        self.login_accountant()

        response = self.client.get(reverse("invoice_placeholder"))

        self.assertContains(response, "Actions")
        self.assertContains(response, reverse("invoice_detail", args=[invoice.id]))
        self.assertContains(response, "View")

    def test_invoice_list_displays_australian_period_dates(self):
        service_log = self.create_service_log()
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(invoice=invoice, service_log=service_log)
        self.login_accountant()

        response = self.client.get(reverse("invoice_placeholder"))

        self.assertContains(response, "01/06/2026 - 30/06/2026")
        self.assertNotContains(response, "June 1, 2026 - June 30, 2026")

    def test_invoice_detail_displays_australian_period_dates(self):
        service_log = self.create_service_log()
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(invoice=invoice, service_log=service_log)
        self.login_accountant()

        response = self.client.get(reverse("invoice_detail", args=[invoice.id]))

        self.assertContains(response, "Ava Nguyen | 01/06/2026 - 30/06/2026")
        self.assertNotContains(response, "Ava Nguyen | June 1, 2026 - June 30, 2026")

    def test_invoice_list_delete_action_keeps_inline_form_structure(self):
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=Invoice.Status.DRAFT,
            created_by=self.accountant_user,
        )
        self.login_accountant()

        response = self.client.get(reverse("invoice_placeholder"))

        self.assertContains(response, 'td class="actions"')
        self.assertContains(response, f'action="{reverse("invoice_delete", args=[invoice.id])}"')
        self.assertContains(response, 'class="inline-form"')
        self.assertContains(response, '<button class="danger" type="submit">Delete</button>')

    def test_invoice_detail_back_link_preserves_list_state(self):
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=Invoice.Status.DRAFT,
            created_by=self.accountant_user,
        )
        list_path = (
            f"{reverse('invoice_placeholder')}?participant=Ava&status=draft"
            "&sort=total&direction=desc&page=2"
        )
        self.login_accountant()

        list_response = self.client.get(list_path)
        detail_response = self.client.get(reverse("invoice_detail", args=[invoice.id]), {"next": list_path})

        self.assertContains(
            list_response,
            f"{reverse('invoice_detail', args=[invoice.id])}?next=",
        )
        self.assertContains(detail_response, f'href="{list_path.replace("&", "&amp;")}"')

    def test_approved_service_log_list_has_invoice_shortcut(self):
        approved_log = self.create_service_log(service_date=date(2026, 6, 2))
        submitted_log = self.create_service_log(
            service_date=date(2026, 6, 3),
            status=ServiceLog.Status.SUBMITTED,
        )
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        shortcut_url = (
            f"{reverse('invoice_create')}?participant={self.participant.id}"
            f"&period_start={approved_log.service_date:%Y-%m-%d}"
            f"&period_end={approved_log.service_date:%Y-%m-%d}"
        )
        submitted_shortcut_url = (
            f"{reverse('invoice_create')}?participant={self.participant.id}"
            f"&period_start={submitted_log.service_date:%Y-%m-%d}"
            f"&period_end={submitted_log.service_date:%Y-%m-%d}"
        )
        self.assertContains(response, shortcut_url)
        self.assertContains(response, "Create Invoice")
        self.assertNotContains(response, submitted_shortcut_url)

    def test_approved_service_log_list_has_bulk_invoice_selection(self):
        approved_log = self.create_service_log(service_date=date(2026, 6, 2))
        submitted_log = self.create_service_log(
            service_date=date(2026, 6, 3),
            status=ServiceLog.Status.SUBMITTED,
        )
        self.login_admin()

        response = self.client.get(reverse("service_log_list"))

        self.assertContains(response, f'action="{reverse("invoice_create")}"')
        self.assertContains(response, 'name="service_log_ids"')
        self.assertContains(response, f'value="{approved_log.id}"')
        self.assertNotContains(response, f'value="{submitted_log.id}"')
        self.assertContains(response, "Create Invoice from Selected")

    def test_invoice_list_formats_total_to_two_decimal_places(self):
        service_log = self.create_service_log(actual_hours=Decimal("2.00"))
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(invoice=invoice, service_log=service_log)
        self.login_accountant()

        response = self.client.get(reverse("invoice_placeholder"))

        self.assertContains(response, "$130.94")
        self.assertNotContains(response, "$130.940000000000")

    def test_invoice_list_can_filter_by_number_participant_status_and_period(self):
        ava_log = self.create_service_log(service_date=date(2026, 6, 1))
        ava_invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=Invoice.Status.DRAFT,
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(ava_invoice, ava_log)
        ben_log = self.create_service_log(
            participant=self.other_participant,
            service_date=date(2026, 7, 1),
        )
        ben_invoice = Invoice.objects.create(
            participant=self.other_participant,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            status=Invoice.Status.ISSUED,
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(ben_invoice, ben_log)
        self.login_accountant()

        response = self.client.get(
            reverse("invoice_placeholder"),
            {
                "q": ava_invoice.invoice_number[-4:],
                "participant": "Ava",
                "status": Invoice.Status.DRAFT,
                "period_from": "2026-06-01",
                "period_to": "2026-06-30",
            },
        )

        self.assertContains(response, ava_invoice.invoice_number)
        self.assertNotContains(response, ben_invoice.invoice_number)
        self.assertContains(response, "Ava")
        self.assertContains(response, "Draft")

    def test_invoice_list_renders_status_specific_class(self):
        service_log = self.create_service_log()
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=Invoice.Status.DRAFT,
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(invoice, service_log)
        self.login_accountant()

        response = self.client.get(reverse("invoice_placeholder"))

        self.assertContains(response, 'class="status-pill status-draft"')

    def test_invoice_list_shows_status_filter_summary(self):
        service_log = self.create_service_log()
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=Invoice.Status.DRAFT,
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(invoice, service_log)
        self.login_accountant()

        response = self.client.get(
            reverse("invoice_placeholder"),
            {"status": Invoice.Status.DRAFT},
        )

        self.assertContains(response, "Showing draft invoices.")
        self.assertContains(response, reverse("invoice_placeholder"))

    def test_invoice_list_shows_multi_filter_summary(self):
        service_log = self.create_service_log(service_date=date(2026, 6, 1))
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=Invoice.Status.DRAFT,
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(invoice, service_log)
        self.login_accountant()

        response = self.client.get(
            reverse("invoice_placeholder"),
            {
                "q": invoice.invoice_number[-4:],
                "participant": "Ava",
                "status": Invoice.Status.DRAFT,
                "period_from": "2026-06-01",
                "period_to": "2026-06-30",
            },
        )

        self.assertContains(
            response,
            (
                f"Showing draft invoices matching &quot;{invoice.invoice_number[-4:]}&quot; "
                "for Ava from 01/06/2026 to 30/06/2026."
            ),
        )

    def test_invoice_list_is_paginated_and_preserves_filters(self):
        for index in range(25):
            Invoice.objects.create(
                participant=self.participant,
                period_start=date(2026, 6, 1),
                period_end=date(2026, 6, 30),
                status=Invoice.Status.DRAFT,
                created_by=self.accountant_user,
            )
        Invoice.objects.create(
            participant=self.other_participant,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            status=Invoice.Status.ISSUED,
            created_by=self.accountant_user,
        )
        self.login_accountant()

        response = self.client.get(
            reverse("invoice_placeholder"),
            {
                "q": "INV-",
                "participant": "Ava",
                "status": Invoice.Status.DRAFT,
                "period_from": "2026-06-01",
                "period_to": "2026-06-30",
            },
        )

        self.assertEqual(response.context["invoices"].paginator.count, 25)
        self.assertEqual(len(response.context["invoices"]), 20)
        self.assertContains(response, "Showing 1-20 of 25 records")
        self.assertContains(
            response,
            "?q=INV-&amp;participant=Ava&amp;status=draft&amp;period_from=2026-06-01&amp;period_to=2026-06-30&amp;page=2",
        )
        self.assertNotContains(response, "Ben Taylor")

    def test_invoice_list_can_sort_by_total_and_preserve_filters(self):
        low_log = self.create_service_log(actual_hours=Decimal("1.00"))
        low_invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=Invoice.Status.DRAFT,
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(low_invoice, low_log)
        high_log = self.create_service_log(
            service_date=date(2026, 6, 2),
            actual_hours=Decimal("3.00"),
        )
        high_invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=Invoice.Status.DRAFT,
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(high_invoice, high_log)
        self.login_accountant()

        response = self.client.get(
            reverse("invoice_placeholder"),
            {
                "status": Invoice.Status.DRAFT,
                "participant": "Ava",
                "sort": "total",
                "direction": "desc",
            },
        )
        content = response.content.decode()

        self.assertLess(content.index("$196.41"), content.index("$65.47"))
        self.assertContains(
            response,
            "?status=draft&amp;participant=Ava&amp;sort=total&amp;direction=asc",
        )

    def test_invoice_list_distinguishes_empty_filter_results(self):
        Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=Invoice.Status.DRAFT,
            created_by=self.accountant_user,
        )
        self.login_accountant()

        response = self.client.get(reverse("invoice_placeholder"), {"participant": "Missing"})

        self.assertContains(response, "No invoices match the current filters.")
        self.assertContains(response, "Clear filters")
        self.assertNotContains(response, "Create an invoice or adjust the filters")

    def test_invoice_create_previews_only_selected_service_logs(self):
        selected_log = self.create_service_log(
            service_date=date(2026, 6, 1),
            case_notes="Selected June service",
        )
        unselected_log = self.create_service_log(
            service_date=date(2026, 6, 2),
            case_notes="Unselected June service",
        )
        self.login_accountant()

        response = self.client.get(
            reverse("invoice_create"),
            {"service_log_ids": [selected_log.id]},
        )

        self.assertContains(response, "Selected June service")
        self.assertNotContains(response, "Unselected June service")
        self.assertContains(response, f'name="service_log_ids" value="{selected_log.id}"')
        self.assertContains(response, "2026-06-01")
        self.assertNotContains(response, f'name="service_log_ids" value="{unselected_log.id}"')

    def test_invoice_create_preview_displays_australian_service_log_dates(self):
        service_log = self.create_service_log(service_date=date(2026, 6, 1))
        self.login_accountant()

        response = self.client.get(reverse("invoice_create"), self.create_payload())

        self.assertContains(response, "<td>01/06/2026</td>", html=True)
        self.assertNotContains(response, "<td>June 1, 2026</td>", html=True)
        self.assertContains(response, 'name="period_start" value="2026-06-01"')

    def test_invoice_create_selected_logs_must_be_same_participant(self):
        ava_log = self.create_service_log(case_notes="Ava selected service")
        ben_log = self.create_service_log(
            participant=self.other_participant,
            case_notes="Ben selected service",
        )
        self.login_accountant()

        response = self.client.get(
            reverse("invoice_create"),
            {"service_log_ids": [ava_log.id, ben_log.id]},
        )

        self.assertContains(
            response,
            "Selected service logs must belong to one participant.",
        )
        self.assertNotContains(response, "Ava selected service")
        self.assertNotContains(response, "Ben selected service")

    def test_invoice_create_creates_invoice_from_selected_logs_only(self):
        selected_log = self.create_service_log(
            service_date=date(2026, 6, 1),
            case_notes="Selected billing service",
        )
        unselected_log = self.create_service_log(
            service_date=date(2026, 6, 2),
            case_notes="Unselected billing service",
        )
        self.login_accountant()

        response = self.client.post(
            reverse("invoice_create"),
            {
                "participant": self.participant.id,
                "period_start": "2026-06-01",
                "period_end": "2026-06-02",
                "service_log_ids": [selected_log.id],
            },
        )

        invoice = Invoice.objects.get()
        self.assertRedirects(response, reverse("invoice_detail", args=[invoice.id]))
        self.assertEqual(invoice.lines.count(), 1)
        self.assertTrue(invoice.lines.filter(service_log=selected_log).exists())
        selected_log.refresh_from_db()
        unselected_log.refresh_from_db()
        self.assertEqual(selected_log.status, ServiceLog.Status.INVOICED)
        self.assertEqual(unselected_log.status, ServiceLog.Status.APPROVED)

    def test_draft_invoice_can_be_deleted_and_releases_service_logs(self):
        service_log = self.create_service_log()
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=Invoice.Status.DRAFT,
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(invoice, service_log)
        service_log.status = ServiceLog.Status.INVOICED
        service_log.save(update_fields=["status", "updated_at"])
        self.login_accountant()

        response = self.client.post(reverse("invoice_delete", args=[invoice.id]))

        service_log.refresh_from_db()
        self.assertRedirects(response, reverse("invoice_placeholder"))
        self.assertFalse(Invoice.objects.filter(id=invoice.id).exists())
        self.assertEqual(service_log.status, ServiceLog.Status.APPROVED)
        self.assertFalse(InvoiceLine.objects.filter(service_log=service_log).exists())

    def test_issued_invoice_cannot_be_deleted(self):
        service_log = self.create_service_log()
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=Invoice.Status.ISSUED,
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(invoice, service_log)
        self.login_accountant()

        response = self.client.post(reverse("invoice_delete", args=[invoice.id]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Invoice.objects.filter(id=invoice.id).exists())

    def test_invoice_detail_formats_amounts_to_two_decimal_places(self):
        service_log = self.create_service_log(actual_hours=Decimal("2.00"))
        invoice = Invoice.objects.create(
            participant=self.participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            created_by=self.accountant_user,
        )
        InvoiceLine.objects.create_from_service_log(invoice=invoice, service_log=service_log)
        self.login_accountant()

        response = self.client.get(reverse("invoice_detail", args=[invoice.id]))

        self.assertContains(response, "$130.94")
        self.assertContains(response, "$65.47")
        self.assertContains(response, "2.00")
        self.assertNotContains(response, "$130.940000000000")

    def test_exports_page_marks_invoices_sidebar_link_as_active(self):
        self.login_accountant()

        response = self.client.get(reverse("exports_placeholder"))

        self.assertContains(
            response,
            f'class="sidebar-link active" href="{reverse("invoice_placeholder")}"',
        )
