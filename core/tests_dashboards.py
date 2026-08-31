from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from invoices.models import Invoice
from participants.models import Participant
from scheduling.models import Shift, SupportItem
from service_logs.models import ServiceLog
from workers.models import SupportWorker


class DashboardPolishTests(TestCase):
    def test_admin_dashboard_lists_current_v1_modules(self):
        user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=user, role=UserProfile.Role.ADMIN)

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Participants")
        self.assertContains(response, "Support Workers")
        self.assertContains(response, "Roster")
        self.assertContains(response, "Service Logs")
        self.assertContains(response, "Invoices")
        self.assertContains(response, "Documents")
        self.assertContains(response, "Audit Logs")
        self.assertContains(response, "NDIS Admin")
        self.assertNotContains(response, "will be added")

    def test_admin_dashboard_shows_common_module_actions(self):
        user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=user, role=UserProfile.Role.ADMIN)

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertContains(response, "Common actions")
        self.assertContains(response, "Add participant")
        self.assertContains(response, "Add worker")
        self.assertContains(response, "Create shift")
        self.assertContains(response, "Review logs")
        self.assertContains(response, "Create invoice")
        self.assertContains(response, "Upload document")
        self.assertContains(response, reverse("participant_create"))
        self.assertContains(response, reverse("worker_create"))
        self.assertContains(response, reverse("shift_create"))
        self.assertContains(response, reverse("service_log_list"))
        self.assertContains(response, reverse("invoice_create"))
        self.assertContains(response, reverse("document_create"))

    def test_admin_dashboard_marks_sidebar_link_active(self):
        user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=user, role=UserProfile.Role.ADMIN)

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertContains(
            response,
            f'class="sidebar-link active" href="{reverse("admin_dashboard")}"',
        )

    def test_admin_shell_uses_secondary_logout_button(self):
        user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=user, role=UserProfile.Role.ADMIN)

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertContains(response, 'class="button secondary topbar-logout"')

    def test_admin_dashboard_shows_operations_summary(self):
        admin_user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=admin_user, role=UserProfile.Role.ADMIN)
        worker_user = User.objects.create_user(username="worker", password="pass")
        UserProfile.objects.create(
            user=worker_user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        worker = SupportWorker.objects.create(
            user=worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
        )
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
            address_line_1="10 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        support_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Assistance with self-care activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        base_shift = {
            "participant": participant,
            "worker": worker,
            "start_time": time(9, 0),
            "end_time": time(11, 0),
            "planned_hours": Decimal("2.00"),
            "support_item": support_item,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "created_by": admin_user,
        }
        draft_shift = Shift.objects.create(
            **base_shift,
            service_date=date(2026, 6, 4),
            status=Shift.Status.DRAFT,
        )
        submitted_shift = Shift.objects.create(
            **base_shift,
            service_date=date(2026, 6, 5),
            status=Shift.Status.COMPLETED,
        )
        approved_shift = Shift.objects.create(
            **base_shift,
            service_date=date(2026, 6, 6),
            status=Shift.Status.COMPLETED,
        )
        ServiceLog.objects.create_from_shift(
            shift=submitted_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 0),
            actual_hours=Decimal("2.00"),
            case_notes="Submitted log for review.",
            status=ServiceLog.Status.SUBMITTED,
        )
        ServiceLog.objects.create_from_shift(
            shift=approved_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 0),
            actual_hours=Decimal("2.00"),
            case_notes="Approved log awaiting invoice.",
            status=ServiceLog.Status.APPROVED,
        )
        Invoice.objects.create(
            participant=participant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
            status=Invoice.Status.DRAFT,
            created_by=admin_user,
        )
        Invoice.objects.create(
            participant=participant,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            status=Invoice.Status.ISSUED,
            created_by=admin_user,
        )

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertContains(response, "Operations summary")
        self.assertContains(response, "1 draft shift")
        self.assertContains(response, "1 submitted log")
        self.assertContains(response, "1 approved log")
        self.assertContains(response, "1 draft invoice")
        self.assertContains(response, "1 issued invoice")
        self.assertContains(response, f'{reverse("roster_list")}?status={draft_shift.status}')
        self.assertContains(response, f'{reverse("service_log_list")}?status={ServiceLog.Status.SUBMITTED}')
        self.assertContains(response, f'{reverse("service_log_list")}?status={ServiceLog.Status.APPROVED}')
        self.assertContains(response, f'{reverse("invoice_placeholder")}?status={Invoice.Status.DRAFT}')
        self.assertContains(response, f'{reverse("invoice_placeholder")}?status={Invoice.Status.ISSUED}')

    def test_admin_dashboard_shows_compact_workbench_overview_and_priority_queue(self):
        admin_user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=admin_user, role=UserProfile.Role.ADMIN)
        worker_user = User.objects.create_user(username="worker", password="pass")
        UserProfile.objects.create(
            user=worker_user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        worker = SupportWorker.objects.create(
            user=worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
            status=SupportWorker.Status.ACTIVE,
        )
        inactive_worker_user = User.objects.create_user(username="inactiveworker", password="pass")
        UserProfile.objects.create(
            user=inactive_worker_user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        SupportWorker.objects.create(
            user=inactive_worker_user,
            first_name="Inactive",
            last_name="Worker",
            email="inactive.worker@example.com",
            status=SupportWorker.Status.INACTIVE,
        )
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
            address_line_1="10 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        Participant.objects.create(
            first_name="Inactive",
            last_name="Participant",
            status=Participant.Status.INACTIVE,
            address_line_1="20 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        support_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Assistance with self-care activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        base_shift = {
            "participant": participant,
            "worker": worker,
            "start_time": time(9, 0),
            "end_time": time(11, 0),
            "planned_hours": Decimal("2.00"),
            "support_item": support_item,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "created_by": admin_user,
        }
        Shift.objects.create(
            **base_shift,
            service_date=date(2026, 8, 31),
            status=Shift.Status.DRAFT,
        )
        submitted_shift = Shift.objects.create(
            **base_shift,
            service_date=date(2026, 9, 1),
            status=Shift.Status.COMPLETED,
        )
        approved_shift = Shift.objects.create(
            **base_shift,
            service_date=date(2026, 9, 2),
            status=Shift.Status.COMPLETED,
        )
        ServiceLog.objects.create_from_shift(
            shift=submitted_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 0),
            actual_hours=Decimal("2.00"),
            case_notes="Submitted log for review.",
            status=ServiceLog.Status.SUBMITTED,
        )
        ServiceLog.objects.create_from_shift(
            shift=approved_shift,
            actual_start_time=time(9, 0),
            actual_end_time=time(11, 0),
            actual_hours=Decimal("2.00"),
            case_notes="Approved log awaiting invoice.",
            status=ServiceLog.Status.APPROVED,
        )
        Invoice.objects.create(
            participant=participant,
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            status=Invoice.Status.DRAFT,
            created_by=admin_user,
        )
        Invoice.objects.create(
            participant=participant,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            status=Invoice.Status.ISSUED,
            created_by=admin_user,
        )

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))
        content = response.content.decode()

        self.assertContains(response, "Today at BSC")
        self.assertContains(response, "Operations overview")
        self.assertContains(response, "1 active participant")
        self.assertContains(response, "1 active support worker")
        self.assertContains(response, "1 submitted log")
        self.assertContains(response, "1 ready to invoice")
        self.assertContains(response, "Priority queue")
        self.assertContains(response, "Review submitted service logs")
        self.assertContains(response, "Create invoices from approved logs")
        self.assertContains(response, "Publish draft roster shifts")
        self.assertContains(response, "Check draft invoices")
        self.assertContains(response, "Follow up issued invoices")
        self.assertContains(response, f'{reverse("service_log_list")}?status={ServiceLog.Status.SUBMITTED}')
        self.assertContains(response, f'{reverse("service_log_list")}?status={ServiceLog.Status.APPROVED}')
        self.assertContains(response, f'{reverse("roster_list")}?status={Shift.Status.DRAFT}')
        self.assertContains(response, f'{reverse("invoice_placeholder")}?status={Invoice.Status.DRAFT}')
        self.assertContains(response, f'{reverse("invoice_placeholder")}?status={Invoice.Status.ISSUED}')
        self.assertLess(
            content.index("Review submitted service logs"),
            content.index("Create invoices from approved logs"),
        )
        self.assertLess(
            content.index("Create invoices from approved logs"),
            content.index("Publish draft roster shifts"),
        )
        self.assertLess(
            content.index("Publish draft roster shifts"),
            content.index("Check draft invoices"),
        )
        self.assertLess(
            content.index("Check draft invoices"),
            content.index("Follow up issued invoices"),
        )

    def test_admin_dashboard_pluralizes_operations_summary_counts(self):
        admin_user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=admin_user, role=UserProfile.Role.ADMIN)
        worker_user = User.objects.create_user(username="worker", password="pass")
        UserProfile.objects.create(
            user=worker_user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        worker = SupportWorker.objects.create(
            user=worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
        )
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
            address_line_1="10 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        support_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Assistance with self-care activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        base_shift = {
            "participant": participant,
            "worker": worker,
            "start_time": time(9, 0),
            "end_time": time(11, 0),
            "planned_hours": Decimal("2.00"),
            "support_item": support_item,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "created_by": admin_user,
        }
        for day in [4, 5]:
            Shift.objects.create(
                **base_shift,
                service_date=date(2026, 6, day),
                status=Shift.Status.DRAFT,
            )
        for day in [6, 7]:
            shift = Shift.objects.create(
                **base_shift,
                service_date=date(2026, 6, day),
                status=Shift.Status.COMPLETED,
            )
            ServiceLog.objects.create_from_shift(
                shift=shift,
                actual_start_time=time(9, 0),
                actual_end_time=time(11, 0),
                actual_hours=Decimal("2.00"),
                case_notes="Submitted log for review.",
                status=ServiceLog.Status.SUBMITTED,
            )
        for day in [8, 9]:
            shift = Shift.objects.create(
                **base_shift,
                service_date=date(2026, 6, day),
                status=Shift.Status.COMPLETED,
            )
            ServiceLog.objects.create_from_shift(
                shift=shift,
                actual_start_time=time(9, 0),
                actual_end_time=time(11, 0),
                actual_hours=Decimal("2.00"),
                case_notes="Approved log awaiting invoice.",
                status=ServiceLog.Status.APPROVED,
            )
        for month in [5, 6]:
            Invoice.objects.create(
                participant=participant,
                period_start=date(2026, month, 1),
                period_end=date(2026, month, 28),
                status=Invoice.Status.DRAFT,
                created_by=admin_user,
            )
            Invoice.objects.create(
                participant=participant,
                period_start=date(2026, month, 1),
                period_end=date(2026, month, 28),
                status=Invoice.Status.ISSUED,
                created_by=admin_user,
            )

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertContains(response, "2 draft shifts")
        self.assertContains(response, "2 submitted logs")
        self.assertContains(response, "2 approved logs")
        self.assertContains(response, "2 draft invoices")
        self.assertContains(response, "2 issued invoices")
        self.assertNotContains(response, "2 draft shift</strong>")
        self.assertNotContains(response, "2 submitted log</strong>")
        self.assertNotContains(response, "2 approved log</strong>")
        self.assertNotContains(response, "2 draft invoice</strong>")
        self.assertNotContains(response, "2 issued invoice</strong>")

    def test_admin_dashboard_shows_zero_state_when_no_operations_need_action(self):
        user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=user, role=UserProfile.Role.ADMIN)

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertContains(response, "Operations summary")
        self.assertContains(response, "No outstanding admin actions.")
        self.assertContains(response, "0 submitted logs")
        self.assertContains(response, "0 ready to invoice")
        self.assertNotContains(response, "Publish draft roster shifts")
        self.assertNotContains(response, "Review submitted service logs")
        self.assertNotContains(response, "Create invoices from approved logs")
        self.assertNotContains(response, "Check draft invoices")
        self.assertNotContains(response, "Follow up issued invoices")

    def test_admin_dashboard_shows_workflow_checklist(self):
        user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=user, role=UserProfile.Role.ADMIN)

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertContains(response, "Workflow checklist")
        self.assertContains(response, "Add participant")
        self.assertContains(response, "Assign worker")
        self.assertContains(response, "Create roster shift")
        self.assertContains(response, "Worker submits service log")
        self.assertContains(response, "Approve service log")
        self.assertContains(response, "Create invoice")
        self.assertContains(response, reverse("participant_create"))
        self.assertContains(response, reverse("participant_list"))
        self.assertContains(response, reverse("shift_create"))
        self.assertContains(response, f'{reverse("roster_list")}?status=confirmed')
        self.assertContains(response, f'{reverse("service_log_list")}?status=submitted')
        self.assertContains(response, reverse("invoice_create"))

    def test_admin_dashboard_workflow_checklist_uses_stable_row_structure(self):
        user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=user, role=UserProfile.Role.ADMIN)

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertContains(response, 'class="workflow-checklist-number"', count=6)
        self.assertContains(response, 'class="workflow-checklist-copy"', count=6)
        self.assertContains(response, 'class="workflow-checklist-action"', count=6)
        self.assertContains(response, '<a href="/participants/new/">Open</a>', html=True)
        self.assertContains(response, '<a href="/participants/">Open</a>', html=True)
        self.assertContains(response, '<a href="/roster/new/">Open</a>', html=True)
        self.assertContains(response, '<a href="/roster/?status=confirmed">Open</a>', html=True)
        self.assertContains(response, '<a href="/service-logs/?status=submitted">Open</a>', html=True)
        self.assertContains(response, '<a href="/invoices/new/">Open</a>', html=True)

    def test_admin_dashboard_uses_overview_layout(self):
        user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=user, role=UserProfile.Role.ADMIN)

        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertContains(response, 'class="dashboard-overview dashboard-workbench-grid"')
        self.assertContains(response, 'class="card dashboard-card priority-queue"')
        self.assertContains(response, 'class="card dashboard-card workflow-checklist"')
        self.assertContains(response, 'class="dashboard-overview-strip"')
        self.assertContains(response, 'class="common-actions-grid"')

    def test_worker_dashboard_lists_current_worker_tools(self):
        user = User.objects.create_user(username="worker", password="pass")
        UserProfile.objects.create(
            user=user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        SupportWorker.objects.create(
            user=user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
        )

        self.client.login(username="worker", password="pass")
        response = self.client.get(reverse("worker_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Shifts")
        self.assertContains(response, "My Logs")
        self.assertContains(response, "My Documents")
        self.assertContains(response, "Profile")
        self.assertNotContains(response, "will appear here")

    def test_worker_dashboard_uses_worker_responsive_layout_hooks(self):
        user = User.objects.create_user(username="worker", password="pass")
        UserProfile.objects.create(
            user=user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        SupportWorker.objects.create(
            user=user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
        )

        self.client.login(username="worker", password="pass")
        response = self.client.get(reverse("worker_dashboard"))

        self.assertContains(response, 'class="app-shell worker-app-shell"')
        self.assertContains(response, 'class="sidebar worker-sidebar"')
        self.assertContains(response, 'class="topbar worker-topbar"')
        self.assertContains(response, 'class="button secondary topbar-logout"')
        self.assertContains(response, 'class="worker-mobile-menu-button"')
        self.assertContains(response, 'class="worker-mobile-drawer"')
        self.assertContains(response, 'aria-label="Worker menu"')
        self.assertContains(response, 'href="/sw/dashboard/"')
        self.assertContains(response, 'href="/sw/shifts/"')
        self.assertContains(response, 'href="/sw/logs/"')
        self.assertContains(response, 'href="/sw/documents/"')
        self.assertContains(response, 'href="/sw/profile/"')
        self.assertContains(response, 'method="post" action="/logout/"')

    def test_worker_dashboard_uses_mobile_content_polish_hooks(self):
        user = User.objects.create_user(username="worker", password="pass")
        UserProfile.objects.create(
            user=user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        SupportWorker.objects.create(
            user=user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
        )

        self.client.login(username="worker", password="pass")
        response = self.client.get(reverse("worker_dashboard"))

        self.assertContains(response, 'class="worker-content worker-dashboard-page"')
        self.assertContains(response, 'class="card worker-action-summary worker-priority-panel"')
        self.assertContains(response, 'class="card-grid worker-dashboard-grid worker-tool-grid"')
        self.assertContains(response, 'class="card worker-tool-card"')
        self.assertContains(response, "Open shifts")

    def test_worker_dashboard_shows_shift_action_summary(self):
        admin_user = User.objects.create_user(username="admin", password="pass")
        UserProfile.objects.create(user=admin_user, role=UserProfile.Role.ADMIN)
        worker_user = User.objects.create_user(username="worker", password="pass")
        UserProfile.objects.create(
            user=worker_user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        worker = SupportWorker.objects.create(
            user=worker_user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
        )
        participant = Participant.objects.create(
            first_name="Ava",
            last_name="Nguyen",
            status=Participant.Status.ACTIVE,
            address_line_1="10 Creek Street",
            suburb="Brisbane",
            state="QLD",
            postcode="4000",
        )
        support_item = SupportItem.objects.create(
            item_number="01_011_0107_1_1",
            name="Assistance with self-care activities",
            unit=SupportItem.Unit.HOUR,
            price_limit=Decimal("65.47"),
            gst_code=SupportItem.GSTCode.GST_FREE,
            is_active=True,
        )
        base_shift = {
            "participant": participant,
            "worker": worker,
            "start_time": time(9, 0),
            "end_time": time(11, 0),
            "planned_hours": Decimal("2.00"),
            "support_item": support_item,
            "service_type": Shift.ServiceType.PERSONAL_CARE,
            "created_by": admin_user,
        }
        Shift.objects.create(
            **base_shift,
            service_date=date(2026, 6, 4),
            status=Shift.Status.PUBLISHED,
        )
        Shift.objects.create(
            **base_shift,
            service_date=date(2026, 6, 5),
            status=Shift.Status.CONFIRMED,
        )
        Shift.objects.create(
            **base_shift,
            service_date=date(2026, 6, 6),
            status=Shift.Status.COMPLETED,
        )

        self.client.login(username="worker", password="pass")
        response = self.client.get(reverse("worker_dashboard"))

        self.assertContains(response, "Shift action summary")
        self.assertContains(response, "1 needs attention")
        self.assertContains(response, "1 ready for log")
        self.assertContains(response, "1 completed")
        self.assertContains(response, f'{reverse("worker_shift_list")}?view=needs_attention')
        self.assertContains(response, f'{reverse("worker_shift_list")}?view=upcoming')
        self.assertContains(response, f'{reverse("worker_shift_list")}?view=completed')

    def test_worker_dashboard_shows_zero_state_when_no_shifts_need_action(self):
        user = User.objects.create_user(username="worker", password="pass")
        UserProfile.objects.create(
            user=user,
            role=UserProfile.Role.SUPPORT_WORKER,
            is_active_worker=True,
        )
        SupportWorker.objects.create(
            user=user,
            first_name="Wendy",
            last_name="Worker",
            email="worker@example.com",
        )

        self.client.login(username="worker", password="pass")
        response = self.client.get(reverse("worker_dashboard"))

        self.assertContains(response, "Shift action summary")
        self.assertContains(response, "No shift actions need attention.")
        self.assertNotContains(response, "0 needs attention")
        self.assertNotContains(response, "0 ready for log")
        self.assertNotContains(response, "0 completed")
