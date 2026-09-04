from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from core.models import AuditLog
from participants.models import Participant

from .models import CoordinationLog, ParticipantCoordinatorAssignment, SupportCoordinator


def create_coordinator(username="coord"):
    user = get_user_model().objects.create_user(
        username=username,
        password="pass12345",
    )
    UserProfile.objects.create(
        user=user,
        role=UserProfile.Role.SUPPORT_COORDINATOR,
    )
    return SupportCoordinator.objects.create(
        user=user,
        first_name="Casey",
        last_name="Coordinator",
        email=f"{username}@example.com",
    )


def create_participant(first_name="Demo", last_name="Participant"):
    return Participant.objects.create(
        first_name=first_name,
        last_name=last_name,
        status=Participant.Status.ACTIVE,
    )


class CoordinatorRoleAccessTests(TestCase):
    def create_user_with_role(self, username, role):
        user = get_user_model().objects.create_user(
            username=username,
            password="pass12345",
        )
        UserProfile.objects.create(user=user, role=role)
        return user

    def test_role_redirect_sends_support_coordinator_to_sc_dashboard(self):
        user = self.create_user_with_role(
            "coordinator",
            UserProfile.Role.SUPPORT_COORDINATOR,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("role_redirect"))

        self.assertRedirects(response, reverse("coordinator_dashboard"))

    def test_support_coordinator_can_access_sc_dashboard(self):
        user = self.create_user_with_role(
            "coordinator",
            UserProfile.Role.SUPPORT_COORDINATOR,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("coordinator_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Support Coordinator")

    def test_support_worker_cannot_access_sc_dashboard(self):
        user = self.create_user_with_role(
            "worker",
            UserProfile.Role.SUPPORT_WORKER,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("coordinator_dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_support_coordinator_cannot_access_admin_dashboard(self):
        user = self.create_user_with_role(
            "coordinator",
            UserProfile.Role.SUPPORT_COORDINATOR,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 403)


class CoordinatorPortalParticipantTests(TestCase):
    def setUp(self):
        self.coordinator = create_coordinator("coord-portal")
        self.assigned = Participant.objects.create(
            first_name="Assigned",
            last_name="Participant",
            status=Participant.Status.ACTIVE,
            worker_visible_notes="Use side entrance.",
            internal_notes="Admin only.",
        )
        self.unassigned = Participant.objects.create(
            first_name="Hidden",
            last_name="Participant",
            status=Participant.Status.ACTIVE,
        )
        ParticipantCoordinatorAssignment.objects.create(
            participant=self.assigned,
            coordinator=self.coordinator,
            start_date=date(2026, 9, 4),
        )
        self.client.force_login(self.coordinator.user)

    def test_sc_participant_list_shows_only_assigned_participants(self):
        response = self.client.get(reverse("coordinator_participant_list"))

        self.assertContains(response, "Assigned Participant")
        self.assertNotContains(response, "Hidden Participant")

    def test_sc_participant_detail_hides_internal_notes(self):
        response = self.client.get(
            reverse("coordinator_participant_detail", args=[self.assigned.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Use side entrance.")
        self.assertNotContains(response, "Admin only.")

    def test_sc_cannot_view_unassigned_participant_detail(self):
        response = self.client.get(
            reverse("coordinator_participant_detail", args=[self.unassigned.id])
        )

        self.assertEqual(response.status_code, 404)


class CoordinatorLogSubmissionTests(TestCase):
    def setUp(self):
        self.coordinator = create_coordinator("coord-log")
        self.other_coordinator = create_coordinator("coord-other")
        self.assigned = Participant.objects.create(
            first_name="Assigned",
            last_name="Participant",
            status=Participant.Status.ACTIVE,
        )
        self.unassigned = Participant.objects.create(
            first_name="Hidden",
            last_name="Participant",
            status=Participant.Status.ACTIVE,
        )
        ParticipantCoordinatorAssignment.objects.create(
            participant=self.assigned,
            coordinator=self.coordinator,
            start_date=date(2026, 9, 4),
        )
        self.client.force_login(self.coordinator.user)

    def valid_payload(self, participant):
        return {
            "participant": participant.id,
            "service_date": "2026-09-04",
            "start_time": "09:00",
            "end_time": "10:30",
            "break_minutes": "0",
            "actual_hours": "1.50",
            "coordination_type": CoordinationLog.CoordinationType.GENERAL,
            "case_notes": "Called provider and updated the participant plan notes.",
            "coordinator_notes": "Follow up again next week.",
        }

    def create_log(self, coordinator, participant, case_notes="Called provider."):
        return CoordinationLog.objects.create(
            participant=participant,
            coordinator=coordinator,
            service_date=date(2026, 9, 4),
            start_time=time(9, 0),
            end_time=time(10, 30),
            break_minutes=0,
            actual_hours=Decimal("1.50"),
            coordination_type=CoordinationLog.CoordinationType.GENERAL,
            case_notes=case_notes,
        )

    def test_sc_can_submit_log_for_assigned_participant(self):
        response = self.client.post(
            reverse("coordinator_log_create"),
            self.valid_payload(self.assigned),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        log = CoordinationLog.objects.get(participant=self.assigned)
        self.assertEqual(log.coordinator, self.coordinator)
        self.assertEqual(log.status, CoordinationLog.Status.SUBMITTED)
        self.assertContains(response, "Coordination log submitted for admin review.")

    def test_sc_cannot_submit_log_for_unassigned_participant(self):
        response = self.client.post(
            reverse("coordinator_log_create"),
            self.valid_payload(self.unassigned),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CoordinationLog.objects.exists())
        self.assertContains(response, "Select a valid choice")

    def test_sc_cannot_submit_log_when_end_time_is_not_after_start_time(self):
        payload = self.valid_payload(self.assigned)
        payload["end_time"] = "09:00"

        response = self.client.post(reverse("coordinator_log_create"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CoordinationLog.objects.exists())
        self.assertContains(response, "End time must be after start time.")

    def test_sc_cannot_submit_log_when_break_exceeds_duration(self):
        payload = self.valid_payload(self.assigned)
        payload["break_minutes"] = "90"

        response = self.client.post(reverse("coordinator_log_create"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CoordinationLog.objects.exists())
        self.assertContains(
            response,
            "Break minutes must be less than the total duration.",
        )

    def test_sc_cannot_submit_log_when_actual_hours_do_not_match_duration(self):
        payload = self.valid_payload(self.assigned)
        payload["actual_hours"] = "1.25"

        response = self.client.post(reverse("coordinator_log_create"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CoordinationLog.objects.exists())
        self.assertContains(
            response,
            "Actual hours must match the time worked after breaks.",
        )

    def test_sc_cannot_submit_log_with_non_positive_actual_hours(self):
        payload = self.valid_payload(self.assigned)
        payload["actual_hours"] = "0.00"

        response = self.client.post(reverse("coordinator_log_create"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CoordinationLog.objects.exists())
        self.assertContains(response, "Actual hours must be greater than zero.")

    def test_sc_log_list_shows_only_current_coordinators_logs(self):
        own_log = self.create_log(
            self.coordinator,
            self.assigned,
            case_notes="Visible coordination note.",
        )
        self.create_log(
            self.other_coordinator,
            self.unassigned,
            case_notes="Hidden coordination note.",
        )

        response = self.client.get(reverse("coordinator_log_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, own_log.participant.display_name)
        self.assertContains(response, "Visible coordination note.")
        self.assertNotContains(response, "Hidden coordination note.")

    def test_sc_log_detail_404s_for_another_coordinators_log(self):
        other_log = self.create_log(self.other_coordinator, self.unassigned)

        response = self.client.get(
            reverse("coordinator_log_detail", args=[other_log.id])
        )

        self.assertEqual(response.status_code, 404)


class CoordinationLogAdminReviewTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(
            username="admin-review",
            password="pass12345",
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=UserProfile.Role.ADMIN,
        )
        self.coordinator = create_coordinator("coord-review")
        self.participant = Participant.objects.create(
            first_name="Review",
            last_name="Participant",
            status=Participant.Status.ACTIVE,
        )
        self.log = CoordinationLog.objects.create(
            participant=self.participant,
            coordinator=self.coordinator,
            service_date=date(2026, 9, 4),
            start_time=time(9, 0),
            end_time=time(10, 30),
            break_minutes=0,
            actual_hours=Decimal("1.50"),
            coordination_type=CoordinationLog.CoordinationType.GENERAL,
            case_notes="Submitted coordination work.",
        )
        self.client.force_login(self.admin_user)

    def test_admin_can_approve_submitted_coordination_log(self):
        self.log.rejection_reason = "Old correction note."
        self.log.save(update_fields=["rejection_reason", "updated_at"])

        response = self.client.post(
            reverse("coordination_log_approve", args=[self.log.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.APPROVED)
        self.assertEqual(self.log.reviewed_by, self.admin_user)
        self.assertIsNotNone(self.log.reviewed_at)
        self.assertEqual(self.log.rejection_reason, "")
        self.assertContains(response, "Coordination log approved.")

    def test_admin_reject_requires_reason(self):
        response = self.client.post(
            reverse("coordination_log_reject", args=[self.log.id]),
            {"rejection_reason": ""},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.SUBMITTED)
        self.assertContains(response, "Rejection reason is required.")

    def test_admin_can_reject_submitted_coordination_log(self):
        response = self.client.post(
            reverse("coordination_log_reject", args=[self.log.id]),
            {"rejection_reason": "Needs more detail."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.REJECTED)
        self.assertEqual(self.log.reviewed_by, self.admin_user)
        self.assertIsNotNone(self.log.reviewed_at)
        self.assertEqual(self.log.rejection_reason, "Needs more detail.")
        self.assertContains(response, "Coordination log rejected.")

    def test_support_coordinator_cannot_access_admin_coordination_log_review(self):
        self.client.force_login(self.coordinator.user)
        protected_routes = [
            ("get", reverse("coordination_log_list")),
            ("get", reverse("coordination_log_detail", args=[self.log.id])),
            ("post", reverse("coordination_log_approve", args=[self.log.id])),
            (
                "post",
                reverse("coordination_log_reject", args=[self.log.id]),
                {"rejection_reason": "No detail."},
            ),
        ]

        for route in protected_routes:
            method = route[0]
            url = route[1]
            data = route[2] if len(route) > 2 else {}
            with self.subTest(url=url):
                response = getattr(self.client, method)(url, data)
                self.assertEqual(response.status_code, 403)

    def test_admin_cannot_approve_already_reviewed_coordination_log(self):
        self.log.status = CoordinationLog.Status.APPROVED
        self.log.reviewed_by = self.admin_user
        self.log.reviewed_at = self.log.submitted_at
        self.log.rejection_reason = ""
        self.log.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "updated_at",
            ],
        )
        reviewed_at = self.log.reviewed_at

        response = self.client.post(
            reverse("coordination_log_approve", args=[self.log.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.APPROVED)
        self.assertEqual(self.log.reviewed_by, self.admin_user)
        self.assertEqual(self.log.reviewed_at, reviewed_at)
        self.assertEqual(self.log.rejection_reason, "")
        self.assertContains(response, "Coordination log has already been reviewed.")

    def test_admin_cannot_approve_rejected_coordination_log(self):
        self.log.status = CoordinationLog.Status.REJECTED
        self.log.reviewed_by = self.admin_user
        self.log.reviewed_at = self.log.submitted_at
        self.log.rejection_reason = "Original reason."
        self.log.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "updated_at",
            ],
        )
        reviewed_at = self.log.reviewed_at

        response = self.client.post(
            reverse("coordination_log_approve", args=[self.log.id]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.REJECTED)
        self.assertEqual(self.log.reviewed_by, self.admin_user)
        self.assertEqual(self.log.reviewed_at, reviewed_at)
        self.assertEqual(self.log.rejection_reason, "Original reason.")
        self.assertContains(response, "Coordination log has already been reviewed.")

    def test_admin_cannot_reject_approved_coordination_log(self):
        self.log.status = CoordinationLog.Status.APPROVED
        self.log.reviewed_by = self.admin_user
        self.log.reviewed_at = self.log.submitted_at
        self.log.rejection_reason = ""
        self.log.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "updated_at",
            ],
        )
        reviewed_at = self.log.reviewed_at

        response = self.client.post(
            reverse("coordination_log_reject", args=[self.log.id]),
            {"rejection_reason": "Changed my mind."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.APPROVED)
        self.assertEqual(self.log.reviewed_by, self.admin_user)
        self.assertEqual(self.log.reviewed_at, reviewed_at)
        self.assertEqual(self.log.rejection_reason, "")
        self.assertContains(response, "Coordination log has already been reviewed.")

    def test_admin_cannot_reject_already_reviewed_coordination_log(self):
        self.log.status = CoordinationLog.Status.REJECTED
        self.log.reviewed_by = self.admin_user
        self.log.reviewed_at = self.log.submitted_at
        self.log.rejection_reason = "Original reason."
        self.log.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "updated_at",
            ],
        )
        reviewed_at = self.log.reviewed_at

        response = self.client.post(
            reverse("coordination_log_reject", args=[self.log.id]),
            {"rejection_reason": "Changed my mind."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, CoordinationLog.Status.REJECTED)
        self.assertEqual(self.log.reviewed_by, self.admin_user)
        self.assertEqual(self.log.reviewed_at, reviewed_at)
        self.assertEqual(self.log.rejection_reason, "Original reason.")
        self.assertContains(response, "Coordination log has already been reviewed.")

    def test_review_missing_coordination_log_returns_404(self):
        missing_id = self.log.id + 100

        approve_response = self.client.post(
            reverse("coordination_log_approve", args=[missing_id])
        )
        reject_response = self.client.post(
            reverse("coordination_log_reject", args=[missing_id]),
            {"rejection_reason": "No matching log."},
        )

        self.assertEqual(approve_response.status_code, 404)
        self.assertEqual(reject_response.status_code, 404)


class CoordinatorAuditTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(
            username="admin-audit",
            password="pass12345",
        )
        UserProfile.objects.create(
            user=self.admin_user,
            role=UserProfile.Role.ADMIN,
        )
        self.coordinator = create_coordinator("coord-audit")
        self.participant = create_participant(first_name="Audit")

    def valid_log_payload(self):
        return {
            "participant": self.participant.id,
            "service_date": "2026-09-04",
            "start_time": "09:00",
            "end_time": "10:30",
            "break_minutes": "0",
            "actual_hours": "1.50",
            "coordination_type": CoordinationLog.CoordinationType.GENERAL,
            "case_notes": "Audit-covered coordination work.",
            "coordinator_notes": "",
        }

    def coordinator_payload(self, **overrides):
        data = {
            "username": "audit-newcoord",
            "email": "audit-newcoord@example.com",
            "password1": "CoordinatorPass123!",
            "password2": "CoordinatorPass123!",
            "account_active": "on",
            "first_name": "Nina",
            "last_name": "Patel",
            "phone": "0400000000",
            "status": SupportCoordinator.Status.ACTIVE,
            "notes": "Primary coordinator for complex plans.",
        }
        data.update(overrides)
        return data

    def create_submitted_log(self):
        return CoordinationLog.objects.create(
            participant=self.participant,
            coordinator=self.coordinator,
            service_date=date(2026, 9, 4),
            start_time=time(9, 0),
            end_time=time(10, 30),
            break_minutes=0,
            actual_hours=Decimal("1.50"),
            coordination_type=CoordinationLog.CoordinationType.GENERAL,
            case_notes="Submitted coordination work.",
        )

    def assert_audit_log(self, *, actor, action, obj, summary_fragment):
        audit_log = AuditLog.objects.get(action=action)
        self.assertEqual(audit_log.actor, actor)
        self.assertEqual(audit_log.object_type, obj.__class__.__name__)
        self.assertEqual(audit_log.object_id, str(obj.id))
        self.assertIn(summary_fragment, audit_log.summary)

    def test_coordination_log_submission_writes_audit_log(self):
        ParticipantCoordinatorAssignment.objects.create(
            participant=self.participant,
            coordinator=self.coordinator,
            start_date=date(2026, 9, 4),
        )
        self.client.force_login(self.coordinator.user)

        self.client.post(reverse("coordinator_log_create"), self.valid_log_payload())

        log = CoordinationLog.objects.get(participant=self.participant)
        self.assert_audit_log(
            actor=self.coordinator.user,
            action="coordination_log_submitted",
            obj=log,
            summary_fragment=f"Submitted coordination log {log.id}.",
        )

    def test_admin_create_support_coordinator_writes_audit_log(self):
        self.client.force_login(self.admin_user)

        self.client.post(reverse("coordinator_create"), self.coordinator_payload())

        coordinator = SupportCoordinator.objects.get(user__username="audit-newcoord")
        self.assert_audit_log(
            actor=self.admin_user,
            action="support_coordinator_created",
            obj=coordinator,
            summary_fragment=f"Created support coordinator {coordinator.id}.",
        )

    def test_admin_update_support_coordinator_writes_audit_log(self):
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("coordinator_edit", args=[self.coordinator.id]),
            {
                "email": "casey.audit.updated@example.com",
                "first_name": "Casey",
                "last_name": "Jordan",
                "phone": "0499999999",
                "status": SupportCoordinator.Status.INACTIVE,
                "notes": "No longer taking new participants.",
            },
        )

        self.coordinator.refresh_from_db()
        self.assert_audit_log(
            actor=self.admin_user,
            action="support_coordinator_updated",
            obj=self.coordinator,
            summary_fragment=f"Updated support coordinator {self.coordinator.id}.",
        )

    def test_admin_assign_participant_to_coordinator_writes_audit_log(self):
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("coordinator_assign_participant", args=[self.coordinator.id]),
            {
                "participant": self.participant.id,
                "start_date": "2026-09-04",
                "end_date": "",
                "is_active": "on",
                "notes": "Coordinate plan review and provider introductions.",
            },
        )

        assignment = ParticipantCoordinatorAssignment.objects.get(
            coordinator=self.coordinator,
            participant=self.participant,
        )
        self.assert_audit_log(
            actor=self.admin_user,
            action="participant_coordinator_assigned",
            obj=assignment,
            summary_fragment=f"Assigned participant {self.participant.id}",
        )

    def test_admin_approve_coordination_log_writes_audit_log(self):
        log = self.create_submitted_log()
        self.client.force_login(self.admin_user)

        self.client.post(reverse("coordination_log_approve", args=[log.id]))

        self.assert_audit_log(
            actor=self.admin_user,
            action="coordination_log_approved",
            obj=log,
            summary_fragment=f"Approved coordination log {log.id}.",
        )

    def test_admin_reject_coordination_log_writes_audit_log(self):
        log = self.create_submitted_log()
        rejection_reason = "Needs more detail."
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("coordination_log_reject", args=[log.id]),
            {"rejection_reason": rejection_reason},
        )

        self.assert_audit_log(
            actor=self.admin_user,
            action="coordination_log_rejected",
            obj=log,
            summary_fragment=f"Rejected coordination log {log.id}.",
        )
        self.assertIn(
            rejection_reason,
            AuditLog.objects.get(action="coordination_log_rejected").summary,
        )

    def test_admin_reject_without_reason_does_not_write_audit_log(self):
        log = self.create_submitted_log()
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("coordination_log_reject", args=[log.id]),
            {"rejection_reason": ""},
        )

        self.assertFalse(
            AuditLog.objects.filter(action="coordination_log_rejected").exists()
        )

    def test_admin_reject_already_reviewed_log_does_not_write_audit_log(self):
        log = self.create_submitted_log()
        log.status = CoordinationLog.Status.APPROVED
        log.reviewed_by = self.admin_user
        log.reviewed_at = log.submitted_at
        log.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        self.client.force_login(self.admin_user)

        self.client.post(
            reverse("coordination_log_reject", args=[log.id]),
            {"rejection_reason": "Changed after review."},
        )

        self.assertFalse(
            AuditLog.objects.filter(action="coordination_log_rejected").exists()
        )


class CoordinatorAdminManagementTests(TestCase):
    def create_user_with_role(self, username, role):
        user = get_user_model().objects.create_user(
            username=username,
            password="test-password-123",
            email=f"{username}@example.com",
        )
        UserProfile.objects.create(user=user, role=role)
        return user

    def setUp(self):
        self.create_user_with_role("admin", UserProfile.Role.ADMIN)
        self.worker_user = self.create_user_with_role(
            "worker",
            UserProfile.Role.SUPPORT_WORKER,
        )
        self.coordinator_user = self.create_user_with_role(
            "coordinator-user",
            UserProfile.Role.SUPPORT_COORDINATOR,
        )

    def login_admin(self):
        self.client.login(username="admin", password="test-password-123")

    def coordinator_payload(self, **overrides):
        data = {
            "username": "newcoord",
            "email": "newcoord@example.com",
            "password1": "CoordinatorPass123!",
            "password2": "CoordinatorPass123!",
            "account_active": "on",
            "first_name": "Nina",
            "last_name": "Patel",
            "phone": "0400000000",
            "status": SupportCoordinator.Status.ACTIVE,
            "notes": "Primary coordinator for complex plans.",
        }
        data.update(overrides)
        return data

    def test_admin_can_create_support_coordinator(self):
        self.login_admin()

        response = self.client.post(
            reverse("coordinator_create"),
            self.coordinator_payload(),
            follow=True,
        )

        coordinator = SupportCoordinator.objects.get(user__username="newcoord")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            coordinator.user.userprofile.role,
            UserProfile.Role.SUPPORT_COORDINATOR,
        )
        self.assertTrue(coordinator.user.check_password("CoordinatorPass123!"))
        self.assertTrue(coordinator.user.is_active)
        self.assertContains(response, "Support coordinator created.")

    def test_coordinator_create_rejects_password_that_fails_django_validation(self):
        self.login_admin()

        response = self.client.post(
            reverse("coordinator_create"),
            self.coordinator_payload(
                password1="password",
                password2="password",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This password is too common.")
        self.assertFalse(
            get_user_model().objects.filter(username="newcoord").exists()
        )
        self.assertFalse(SupportCoordinator.objects.filter(email="newcoord@example.com").exists())

    def test_coordinator_create_rejects_password_too_similar_to_pending_user(self):
        self.login_admin()

        response = self.client.post(
            reverse("coordinator_create"),
            self.coordinator_payload(
                username="nina-support-coordinator",
                email="nina.support.coordinator@example.com",
                password1="nina-support-coordinator",
                password2="nina-support-coordinator",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The password is too similar to the username.")
        self.assertFalse(
            get_user_model().objects.filter(
                username="nina-support-coordinator",
            ).exists()
        )
        self.assertFalse(
            SupportCoordinator.objects.filter(
                email="nina.support.coordinator@example.com",
            ).exists()
        )

    def test_admin_can_assign_participant_to_coordinator(self):
        coordinator = create_coordinator()
        participant = create_participant()
        self.login_admin()

        response = self.client.post(
            reverse("coordinator_assign_participant", args=[coordinator.id]),
            {
                "participant": participant.id,
                "start_date": "2026-09-04",
                "end_date": "",
                "is_active": "on",
                "notes": "Coordinate plan review and provider introductions.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ParticipantCoordinatorAssignment.objects.filter(
                coordinator=coordinator,
                participant=participant,
                start_date=date(2026, 9, 4),
                is_active=True,
            ).exists()
        )
        self.assertContains(
            response,
            "Participant assigned to support coordinator.",
        )

    def test_admin_cannot_assign_active_participant_to_inactive_coordinator(self):
        coordinator = create_coordinator()
        coordinator.status = SupportCoordinator.Status.INACTIVE
        coordinator.save(update_fields=["status"])
        participant = create_participant()
        self.login_admin()

        response = self.client.post(
            reverse("coordinator_assign_participant", args=[coordinator.id]),
            {
                "participant": participant.id,
                "start_date": "2026-09-04",
                "end_date": "",
                "is_active": "on",
                "notes": "Should be rejected.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ParticipantCoordinatorAssignment.objects.filter(
                coordinator=coordinator,
                participant=participant,
                is_active=True,
            ).exists()
        )
        self.assertContains(
            response,
            "Inactive support coordinators cannot receive new active participant assignments.",
        )

    def test_coordinator_list_active_assignment_count_excludes_inactive_participants(self):
        coordinator = create_coordinator()
        active_participant = create_participant(first_name="Active")
        inactive_participant = create_participant(first_name="Inactive")
        inactive_participant.status = Participant.Status.INACTIVE
        inactive_participant.save(update_fields=["status"])
        ParticipantCoordinatorAssignment.objects.create(
            coordinator=coordinator,
            participant=active_participant,
            start_date=date(2026, 9, 4),
            is_active=True,
        )
        ParticipantCoordinatorAssignment.objects.create(
            coordinator=coordinator,
            participant=inactive_participant,
            start_date=date(2026, 9, 4),
            is_active=True,
        )
        self.login_admin()

        response = self.client.get(reverse("coordinator_list"))

        self.assertEqual(response.context["coordinators"][0].active_assignment_count, 1)

    def test_admin_can_update_support_coordinator(self):
        coordinator = create_coordinator()
        self.login_admin()

        response = self.client.post(
            reverse("coordinator_edit", args=[coordinator.id]),
            {
                "email": "casey.updated@example.com",
                "first_name": "Casey",
                "last_name": "Jordan",
                "phone": "0499999999",
                "status": SupportCoordinator.Status.INACTIVE,
                "notes": "No longer taking new participants.",
            },
            follow=True,
        )

        coordinator.refresh_from_db()
        coordinator.user.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(coordinator.email, "casey.updated@example.com")
        self.assertEqual(coordinator.last_name, "Jordan")
        self.assertEqual(coordinator.phone, "0499999999")
        self.assertEqual(coordinator.status, SupportCoordinator.Status.INACTIVE)
        self.assertEqual(coordinator.notes, "No longer taking new participants.")
        self.assertFalse(coordinator.user.is_active)
        self.assertContains(response, "Support coordinator updated.")

    def test_support_worker_cannot_access_coordinator_admin_list(self):
        self.client.force_login(self.worker_user)

        response = self.client.get(reverse("coordinator_list"))

        self.assertEqual(response.status_code, 403)

    def test_support_coordinator_cannot_access_coordinator_admin_routes(self):
        coordinator = create_coordinator(username="managed-coordinator")
        protected_urls = [
            reverse("coordinator_list"),
            reverse("coordinator_create"),
            reverse("coordinator_detail", args=[coordinator.id]),
            reverse("coordinator_edit", args=[coordinator.id]),
            reverse("coordinator_assign_participant", args=[coordinator.id]),
        ]
        self.client.force_login(self.coordinator_user)

        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)


class CoordinatorModelTests(TestCase):

    def test_coordination_type_choices_use_plan_labels(self):
        choices = dict(CoordinationLog.CoordinationType.choices)

        self.assertEqual(
            choices,
            {
                CoordinationLog.CoordinationType.GENERAL: "General coordination",
                CoordinationLog.CoordinationType.PARTICIPANT_CONTACT: (
                    "Participant / family contact"
                ),
                CoordinationLog.CoordinationType.PROVIDER_CONTACT: "Provider contact",
                CoordinationLog.CoordinationType.PLAN_REVIEW: (
                    "Plan review / funding discussion"
                ),
                CoordinationLog.CoordinationType.INCIDENT_FOLLOW_UP: (
                    "Incident or concern follow-up"
                ),
                CoordinationLog.CoordinationType.OTHER: "Other",
            },
        )

    def test_support_coordinator_display_name(self):
        coordinator = create_coordinator()

        self.assertEqual(coordinator.display_name, "Casey Coordinator")
        self.assertEqual(str(coordinator), "Casey Coordinator")

    def test_assignment_tracks_active_participant_access(self):
        coordinator = create_coordinator()
        participant = create_participant()

        assignment = ParticipantCoordinatorAssignment.objects.create(
            participant=participant,
            coordinator=coordinator,
            start_date=date(2026, 9, 4),
        )

        self.assertTrue(assignment.is_active)
        self.assertEqual(str(assignment), "Demo Participant -> Casey Coordinator")

    def test_coordination_log_defaults_to_submitted(self):
        coordinator = create_coordinator()
        participant = create_participant()

        log = CoordinationLog.objects.create(
            participant=participant,
            coordinator=coordinator,
            service_date=date(2026, 9, 4),
            start_time=time(9, 0),
            end_time=time(10, 30),
            break_minutes=0,
            actual_hours=Decimal("1.50"),
            coordination_type=CoordinationLog.CoordinationType.GENERAL,
            case_notes="Called provider and updated participant record.",
        )

        self.assertEqual(log.status, CoordinationLog.Status.SUBMITTED)
        self.assertEqual(str(log), "2026-09-04 Demo Participant / Casey Coordinator")
