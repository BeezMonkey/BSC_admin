from datetime import date
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.templatetags.static import static
from django.urls import reverse

from core.models import AuditLog
from documents.tests_r1_ui import Page
from participants.models import Participant

from .models import ParticipantCoordinatorAssignment
from .tests import create_coordinator


class CoordinatorProfileUITests(TestCase):
    def setUp(self):
        self.coordinator = create_coordinator("r1-profile-sc")
        self.participant = Participant.objects.create(
            first_name="Fictional", last_name="Participant", preferred_name="Preferred example",
            ndis_number="QA-R1-001", phone="0491570006", email="person@example.invalid",
            address_line_1="12 Fictional Street", address_line_2="Unit 4",
            suburb="West End", state="QLD", postcode="4101",
            emergency_contact_name="Fictional Emergency", emergency_contact_relationship="Sibling",
            emergency_contact_phone="0491570007", emergency_contact_email="emergency@example.invalid",
            worker_visible_notes="VISIBLE SUPPORT NOTE", address_access_instructions="VISIBLE ACCESS NOTE",
            risk_safety_notes="VISIBLE SAFETY NOTE", internal_notes="PRIVATE INTERNAL NOTE",
        )
        ParticipantCoordinatorAssignment.objects.create(
            participant=self.participant, coordinator=self.coordinator, start_date=date(2026, 1, 1),
        )
        self.client.force_login(self.coordinator.user)

    def detail(self):
        return self.client.get(reverse("coordinator_participant_detail", args=[self.participant.pk]))

    def account(self):
        return self.client.get(reverse("coordinator_account"))

    def test_account_opts_into_scoped_r1_layout(self):
        response = self.account()
        self.assertContains(response, "r1-coordinator-details")
        self.assertContains(response, static("css/r1_coordinator_details.css"), count=1)
        self.assertContains(response, "coordinator-account-identity")

    def test_account_preserves_fields_and_original_logout_post(self):
        self.coordinator.phone = "0491570021"
        self.coordinator.save(update_fields=["phone"])
        response = self.account()
        for text in [self.coordinator.display_name, self.coordinator.user.username,
                     self.coordinator.email, self.coordinator.phone, "Username", "Email", "Phone", "Status"]:
            self.assertContains(response, text)
        forms = Page(response).root.find("form")
        self.assertTrue(forms)
        for form in forms:
            self.assertEqual(form.attrs.get("method"), "post")
            self.assertEqual(form.attrs.get("action"), reverse("logout"))
            self.assertTrue(form.find("input", name="csrfmiddlewaretoken"))
        self.assertNotContains(response, 'name="email"')

    def test_missing_coordinator_preserves_setup_pending(self):
        from django.contrib.auth import get_user_model
        from accounts.models import UserProfile
        user = get_user_model().objects.create_user(username="r1-profile-pending")
        UserProfile.objects.create(user=user, role=UserProfile.Role.SUPPORT_COORDINATOR)
        self.client.force_login(user)
        response = self.account()
        self.assertContains(response, "Account setup pending")
        self.assertContains(response, "Your coordinator profile has not been set up yet.")
        self.assertContains(response, "r1-coordinator-details")

    def test_participant_keeps_every_visible_field_and_no_internal_notes(self):
        response = self.detail()
        for text in ["r1-coordinator-details", "coordinator-detail-columns", "Emergency contact",
                     self.participant.display_name, self.participant.preferred_name,
                     self.participant.ndis_number, self.participant.phone, self.participant.email,
                     self.participant.address_line_1, self.participant.address_line_2,
                     self.participant.suburb, self.participant.state, self.participant.postcode,
                     self.participant.emergency_contact_name, self.participant.emergency_contact_relationship,
                     self.participant.emergency_contact_phone, self.participant.emergency_contact_email,
                     self.participant.worker_visible_notes, self.participant.address_access_instructions,
                     self.participant.risk_safety_notes]:
            self.assertContains(response, text)
        self.assertNotContains(response, self.participant.internal_notes)
        self.assertContains(response, reverse("coordinator_participant_list"))

    def test_missing_fields_keep_original_fallback_and_emergency_conditions(self):
        for field in ["preferred_name", "phone", "email", "emergency_contact_name", "address_line_1",
                      "address_line_2", "suburb", "state", "postcode", "worker_visible_notes",
                      "address_access_instructions", "risk_safety_notes"]:
            setattr(self.participant, field, "")
        self.participant.save()
        response = self.detail()
        self.assertContains(response, "Not provided")
        self.assertNotContains(response, "emergency@example.invalid")

    def test_long_values_and_html_escaping_remain_intact(self):
        value = "Fictional support line " * 160 + '<script>alert("no")</script>'
        self.participant.worker_visible_notes = value
        self.participant.save(update_fields=["worker_visible_notes"])
        response = self.detail()
        self.assertContains(response, "Fictional support line " * 160)
        self.assertNotContains(response, '<script>alert("no")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_get_requests_do_not_change_records_or_audit(self):
        before = list(Participant.objects.values()), AuditLog.objects.count()
        self.detail()
        self.account()
        self.assertEqual(before, (list(Participant.objects.values()), AuditLog.objects.count()))

    def test_unassigned_person_still_returns_404(self):
        other = Participant.objects.create(first_name="Unassigned", last_name="Fictional")
        response = self.client.get(reverse("coordinator_participant_detail", args=[other.pk]))
        self.assertEqual(response.status_code, 404)

    def test_other_sc_pages_do_not_load_target_page_assets(self):
        for name in ["coordinator_dashboard", "coordinator_participant_list", "coordinator_log_list",
                     "coordinator_log_create"]:
            response = self.client.get(reverse(name))
            self.assertNotContains(response, static("css/r1_coordinator_details.css"))
            self.assertNotContains(response, "r1-coordinator-details")

    def test_approved_account_has_identity_and_information_cards(self):
        page = Page(self.account()).root
        grids = [node for node in page.find("div") if node.has_class("coordinator-account-cards")]
        self.assertEqual(len(grids), 1)
        cards = [node for node in grids[0].find("section") if node.has_class("coordinator-info-card")]
        self.assertEqual(len(cards), 2)
        details = next(node for node in cards if node.has_class("coordinator-account-details"))
        self.assertEqual([node.text for node in details.find("dt")], ["Username", "Email", "Phone", "Status"])
        self.assertEqual(len(details.find("form")), 1)

    def test_approved_person_cards_group_contact_address_emergency_and_notes(self):
        page = Page(self.detail()).root
        cards = [node for node in page.find("section") if node.has_class("coordinator-info-card")]
        self.assertEqual(len(cards), 3)
        self.assertEqual([node.find("h2")[0].text for node in cards], ["Contact", "Emergency contact", "Support notes"])
        contact, emergency, notes = cards
        self.assertIn("Address", contact.text)
        self.assertNotIn(self.participant.emergency_contact_name, contact.text)
        self.assertEqual([node.text for node in emergency.find("dt")], ["Name", "Relationship", "Phone", "Email"])
        self.assertEqual([node.text for node in notes.find("dt")], ["Worker visible notes", "Address access instructions", "Risk/safety notes"])
        for card in cards:
            self.assertFalse(any(node.has_class("coordinator-info-card") for node in card.find("section")))

    def test_address_has_four_rows_and_preserves_unit_in_address(self):
        page = Page(self.detail()).root
        addresses = [node for node in page.find("dl") if node.has_class("coordinator-address-fields")]
        self.assertEqual(len(addresses), 1)
        self.assertEqual([node.text for node in addresses[0].find("dt")], ["Address:", "Suburb:", "State:", "Postcode:"])
        self.assertEqual(addresses[0].find("dd")[0].text, "12 Fictional Street, Unit 4")
        self.assertNotContains(self.detail(), "Address line 2")

    def test_address_second_line_only_and_empty_have_no_lost_data_or_extra_comma(self):
        for first, second, expected in [("", "Unit 4", "Unit 4"), ("Street only", "", "Street only"), ("", "", "Not provided")]:
            with self.subTest(first=first, second=second):
                self.participant.address_line_1, self.participant.address_line_2 = first, second
                self.participant.save(update_fields=["address_line_1", "address_line_2"])
                page = Page(self.detail()).root
                addresses = [node for node in page.find("dl") if node.has_class("coordinator-address-fields")]
                self.assertEqual(len(addresses), 1, "Approved four-row address group must exist")
                address = addresses[0]
                self.assertEqual(address.find("dd")[0].text, expected)

    def test_joined_address_keeps_autoescaping(self):
        self.participant.address_line_1 = '<script>alert("address")</script>'
        self.participant.address_line_2 = "<b>Unit</b>"
        self.participant.save(update_fields=["address_line_1", "address_line_2"])
        response = self.detail()
        self.assertNotContains(response, '<script>alert("address")</script>')
        self.assertContains(response, "&lt;script&gt;")
        self.assertContains(response, "&lt;b&gt;Unit&lt;/b&gt;")

    def test_anonymous_access_and_original_account_phone_fallback(self):
        self.coordinator.phone = ""
        self.coordinator.save(update_fields=["phone"])
        self.assertContains(self.account(), "<dd>-</dd>", html=True)
        self.client.logout()
        for route in [reverse("coordinator_account"), reverse("coordinator_participant_detail", args=[self.participant.pk])]:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("login"), response.url)


class CoordinatorCardStyleTests(SimpleTestCase):
    def test_approved_cards_use_tokens_and_responsive_two_column_structure(self):
        path = Path(settings.BASE_DIR) / "static/css/r1_coordinator_details.css"
        self.assertTrue(path.is_file(), "Two-page stylesheet must exist")
        css = path.read_text(encoding="utf-8")
        for token in ["var(--r1-surface)", "var(--r1-border)", "var(--r1-text)",
                      ".coordinator-info-card", ".coordinator-account-cards", ".coordinator-contact-card",
                      ".coordinator-emergency-card", "grid-column: 1 / -1;", "border-radius: 8px;",
                      "@media (max-width:980px)", "overflow-wrap:anywhere"]:
            self.assertIn(token, css)
        self.assertNotIn("line-clamp", css)
