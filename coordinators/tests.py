from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
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
