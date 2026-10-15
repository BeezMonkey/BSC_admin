from datetime import date, time
from decimal import Decimal

from django.test import TestCase, override_settings
from django.test.html import parse_html
from django.templatetags.static import static
from django.urls import reverse

from core import tests_r1_shell
from participants.models import Participant
from scheduling.models import Shift
from service_logs.models import ServiceLog
from workers.models import SupportWorker


def elements(node):
    if not isinstance(node, str):
        yield node
        for child in node.children:
            yield from elements(child)


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ADMIN_NOTIFICATION_EMAILS=[],
)
class R1WorkerLogContractTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        tests_r1_shell.R1ShellIsolationTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.client.force_login(self.worker_user)

    def routes(self):
        return (
            (False, reverse("worker_service_log_create", args=[self.shift.pk])),
            (True, reverse("worker_unscheduled_service_log_create")),
        )

    def form_tree(self, response):
        self.assertEqual(response.status_code, 200)
        tree = parse_html(response.content.decode())
        forms = [node for node in elements(tree) if node.name == "form"
                 and "worker-log-form" in dict(node.attributes).get("class", "").split()]
        self.assertEqual(len(forms), 1)
        return tree, forms[0]

    def with_class(self, tree, name):
        matches = [node for node in elements(tree)
                   if name in dict(node.attributes).get("class", "").split()]
        self.assertEqual(len(matches), 1, name)
        return matches[0]

    def payload(self, unscheduled=False, **overrides):
        data = {
            "actual_start_time": "09:15", "actual_end_time": "12:15",
            "break_minutes": "15", "kilometres": "4.50",
            "case_notes": "Fictional B02 participant support.",
            "worker_notes": "Fictional B02 worker follow-up.",
        }
        if unscheduled:
            data.update(
                participant=str(self.participant.pk), service_date="2026-10-13",
                support_item=str(self.shift.support_item_id),
                service_type=Shift.ServiceType.PERSONAL_CARE,
                unscheduled_reason="Fictional urgent participant request.",
            )
        data.update(overrides)
        return data

    def test_form_stylesheet_is_loaded_once_after_shell_on_both_routes(self):
        for unscheduled, url in self.routes():
            with self.subTest(unscheduled=unscheduled):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                styles = [dict(node.attributes).get("href") for node in
                          elements(parse_html(response.content.decode())) if node.name == "link"
                          and dict(node.attributes).get("rel") == "stylesheet"]
                self.assertEqual(styles.count(static("css/r1_worker_logs.css")), 1)
                self.assertLess(styles.index(static("css/r1_shell.css")),
                                styles.index(static("css/r1_worker_logs.css")))

    def test_form_stylesheet_does_not_leak_to_other_routes(self):
        for user, urls in (
            (self.worker_user, [reverse(name) for name in
             ("worker_dashboard", "worker_log_list", "worker_shift_list")]
             + [reverse("worker_shift_detail", args=[self.shift.pk]),
                reverse("worker_service_log_detail", args=[self.log.pk])]),
            (self.admin, [reverse(name) for name in
             ("admin_dashboard", "roster_planner", "invoice_placeholder", "service_log_list")]
             + [reverse("service_log_detail", args=[self.log.pk])]),
        ):
            self.client.force_login(user)
            for url in urls:
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotContains(response, "r1_worker_logs.css")

    def test_semantic_layout_context_and_labelled_sections(self):
        headings = {
            "r1-time-travel": "Actual time & travel",
            "r1-service-notes": "Service notes",
            "r1-attachments": "Attachments",
        }
        for unscheduled, url in self.routes():
            with self.subTest(unscheduled=unscheduled):
                tree, form = self.form_tree(self.client.get(url))
                page = self.with_class(tree, "r1-log-page")
                layout = self.with_class(page, "r1-log-layout")
                context = self.with_class(layout, "r1-log-context")
                self.assertEqual(context.name, "aside")
                nodes = list(elements(layout))
                self.assertLess(nodes.index(context), nodes.index(form))
                self.assertFalse(any(node.name in ("input", "select", "textarea")
                                     for node in elements(context)))
                expected = dict(headings)
                if unscheduled:
                    expected.update({"r1-service-details": "Service details",
                                     "r1-unscheduled-reason": "Unscheduled reason"})
                for heading_id, text in expected.items():
                    sections = [node for node in elements(form) if node.name == "section"
                                and "r1-log-section" in dict(node.attributes).get("class", "").split()
                                and dict(node.attributes).get("aria-labelledby") == heading_id]
                    self.assertEqual(len(sections), 1, heading_id)
                    heading = [node for node in elements(sections[0]) if node.name == "h2"
                               and dict(node.attributes).get("id") == heading_id]
                    self.assertEqual(len(heading), 1)
                    self.assertEqual(" ".join(child for child in heading[0].children
                                              if isinstance(child, str)), text)

    def test_rostered_context_retains_participant_date_time_and_service(self):
        response = self.client.get(self.routes()[0][1])
        tree, _ = self.form_tree(response)
        context = str(self.with_class(tree, "r1-log-context"))
        for value in (self.participant.display_name, "14/10/2026", "9:00 am", "12:00 pm",
                      self.shift.get_service_type_display()):
            self.assertIn(value, context)

    def test_back_and_cancel_retain_original_route_targets(self):
        for unscheduled, url in self.routes():
            with self.subTest(unscheduled=unscheduled):
                tree, form = self.form_tree(self.client.get(url))
                target = reverse("worker_log_list") if unscheduled else reverse(
                    "worker_shift_detail", args=[self.shift.pk])
                back = self.with_class(tree, "r1-log-back")
                self.assertEqual(back.name, "a")
                self.assertEqual(dict(back.attributes).get("href"), target)
                self.assertTrue(any(node.name == "a" and node.children == ["Cancel"]
                                    and dict(node.attributes).get("href") == target
                                    for node in elements(form)))

    def test_original_fields_requiredness_notes_and_attachment_contracts(self):
        required = dict(actual_start_time=True, actual_end_time=True, break_minutes=True,
                        kilometres=True, case_notes=True, worker_notes=False)
        for unscheduled, url in self.routes():
            with self.subTest(unscheduled=unscheduled):
                response = self.client.get(url)
                _, form = self.form_tree(response)
                expected = dict(required)
                if unscheduled:
                    expected.update(participant=True, service_date=True, support_item=True,
                                    service_type=True, unscheduled_reason=False)
                self.assertEqual({name: field.required for name, field in
                                  response.context["form"].fields.items()}, expected)
                controls = {dict(node.attributes)["name"]: node for node in elements(form)
                            if node.name in ("input", "select", "textarea")
                            and "name" in dict(node.attributes)}
                self.assertEqual(set(controls), set(expected) | {"attachments", "csrfmiddlewaretoken"})
                self.assertEqual(dict(form.attributes).get("method"), "post")
                self.assertEqual(dict(form.attributes).get("enctype"), "multipart/form-data")
                for name, is_required in expected.items():
                    attrs = dict(controls[name].attributes)
                    self.assertNotIn("disabled", attrs, name)
                    if attrs.get("type") != "hidden":
                        # The existing choice-only service-type select has no empty option.
                        self.assertEqual("required" in attrs, is_required and name != "service_type", name)
                # ISS-004 is deferred: both existing note inputs remain visible.
                for name in ("case_notes", "worker_notes"):
                    self.assertEqual(controls[name].name, "textarea")
                    for node in elements(form):
                        if controls[name] in list(elements(node)):
                            attrs = dict(node.attributes)
                            self.assertNotIn("hidden", attrs, name)
                            self.assertNotEqual(attrs.get("aria-hidden"), "true", name)
                            style = attrs.get("style", "").replace(" ", "").lower()
                            self.assertNotIn("display:none", style, name)
                attachment = dict(controls["attachments"].attributes)
                self.assertEqual(attachment.get("type"), "file")
                self.assertIn("multiple", attachment)
                self.assertNotIn("required", attachment)
                self.assertEqual(attachment.get("accept"), ".pdf,.jpg,.jpeg,.png,.doc,.docx")
                self.assertContains(response, 'data-max-files="3"')
                self.assertContains(response, 'data-max-size="5242880"')
                self.assertContains(response, static("js/date_time_picker.js"), count=1)

    def test_invalid_posts_retain_values_errors_and_do_not_save(self):
        for unscheduled, url in self.routes():
            with self.subTest(unscheduled=unscheduled):
                payload = self.payload(unscheduled, actual_end_time="08:00")
                counts = (ServiceLog.objects.count(), Shift.objects.count())
                response = self.client.post(url, payload)
                _, form = self.form_tree(response)
                self.assertContains(response, "Actual end time must be after actual start time.")
                bound_form = response.context["form"]
                for name, value in payload.items():
                    self.assertEqual(str(bound_form[name].value()), str(value), name)
                    self.assertInHTML(str(bound_form[name].as_hidden() if name in
                                      ("actual_start_time", "actual_end_time", "service_date")
                                      else bound_form[name]), str(form))
                self.assertEqual((ServiceLog.objects.count(), Shift.objects.count()), counts)
                self.shift.refresh_from_db()
                self.assertEqual(self.shift.status, Shift.Status.CONFIRMED)
                self.assertIsNone(self.shift.completed_at)

    def test_unscheduled_reason_still_required_without_creating_records(self):
        counts = (ServiceLog.objects.count(), Shift.objects.count())
        response = self.client.post(self.routes()[1][1], self.payload(True, unscheduled_reason=""))
        self.assertContains(response, "Unscheduled reason is required.")
        self.assertEqual((ServiceLog.objects.count(), Shift.objects.count()), counts)

    def test_unscheduled_participants_remain_assignment_and_status_restricted(self):
        unassigned = Participant.objects.create(first_name="B02", last_name="Unassigned",
                                               status=Participant.Status.ACTIVE)
        self.participant.status = Participant.Status.INACTIVE
        self.participant.save(update_fields=["status"])
        response = self.client.get(self.routes()[1][1])
        self.assertEqual(list(response.context["form"].fields["participant"].queryset), [])
        for participant in (unassigned, self.participant):
            with self.subTest(participant=participant.pk):
                counts = (ServiceLog.objects.count(), Shift.objects.count())
                response = self.client.post(self.routes()[1][1], self.payload(True, participant=participant.pk))
                self.assertContains(response, "Select a valid choice")
                self.assertEqual((ServiceLog.objects.count(), Shift.objects.count()), counts)

    def test_form_permissions_remain_worker_only_for_get_and_post(self):
        for user, status in ((None, 302), (self.admin, 403)):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for unscheduled, url in self.routes():
                for method in ("get", "post"):
                    with self.subTest(user=user, url=url, method=method):
                        response = getattr(self.client, method)(url, self.payload(unscheduled) if method == "post" else {})
                        self.assertEqual(response.status_code, status)
                        if user is None:
                            self.assertTrue(response.url.startswith(reverse("login") + "?next="))
        self.assertEqual(ServiceLog.objects.count(), 1)
        self.assertEqual(Shift.objects.count(), 2)

    def test_rostered_ownership_and_status_permissions_are_preserved(self):
        other_worker = SupportWorker.objects.create(
            user=self.admin, first_name="B02", last_name="Other worker",
            email="b02-other@example.invalid", status=SupportWorker.Status.ACTIVE,
        )
        for overrides in ({"worker": other_worker}, {"status": Shift.Status.DRAFT}):
            with self.subTest(overrides=overrides):
                shift = Shift.objects.get(pk=self.shift.pk)
                for name, value in overrides.items():
                    setattr(shift, name, value)
                shift.save(update_fields=list(overrides))
                url = reverse("worker_service_log_create", args=[shift.pk])
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, self.payload()).status_code, 404)
                Shift.objects.filter(pk=shift.pk).update(worker=self.worker, status=Shift.Status.CONFIRMED)
        self.assertEqual(ServiceLog.objects.count(), 1)

    def test_rostered_and_unscheduled_submission_fixture_readback(self):
        for unscheduled, url in self.routes():
            with self.subTest(unscheduled=unscheduled):
                before = ServiceLog.objects.count()
                shifts_before = Shift.objects.count()
                response = self.client.post(url, self.payload(unscheduled))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(ServiceLog.objects.count(), before + 1)
                log = ServiceLog.objects.exclude(pk=self.log.pk).get(source=(
                    ServiceLog.Source.UNSCHEDULED if unscheduled else ServiceLog.Source.SCHEDULED))
                log.refresh_from_db()
                self.assertRedirects(response, reverse("worker_service_log_detail", args=[log.pk]))
                self.assertEqual(log.status, ServiceLog.Status.SUBMITTED)
                self.assertEqual(log.participant, self.participant)
                self.assertEqual(log.worker, self.worker)
                self.assertEqual(log.support_item, self.shift.support_item)
                self.assertEqual(log.actual_start_time, time(9, 15))
                self.assertEqual(log.actual_end_time, time(12, 15))
                self.assertEqual(log.break_minutes, 15)
                self.assertEqual(log.actual_hours, Decimal("2.75"))
                self.assertEqual(log.kilometres, Decimal("4.50"))
                self.assertEqual(log.case_notes, self.payload()["case_notes"])
                self.assertEqual(log.worker_notes, self.payload()["worker_notes"])
                shift = Shift.objects.get(pk=log.shift_id)
                self.assertEqual(shift.status, Shift.Status.COMPLETED)
                self.assertIsNotNone(shift.completed_at)
                self.assertEqual(Shift.objects.count(), shifts_before + int(unscheduled))
                if unscheduled:
                    self.assertEqual(log.unscheduled_reason, self.payload(True)["unscheduled_reason"])
                    self.assertEqual(log.service_date, date(2026, 10, 13))
                    self.assertEqual(shift.source, Shift.Source.UNSCHEDULED)
                    self.assertEqual(shift.created_by, self.worker_user)
                    self.assertEqual(shift.service_type, Shift.ServiceType.PERSONAL_CARE)
                else:
                    self.assertEqual(shift.pk, self.shift.pk)
                    self.assertEqual(log.service_date, self.shift.service_date)
