from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from core import tests_r1_shell as shell
from service_logs.models import ServiceLog


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class R1AdminLogDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        shell.R1ShellIsolationTests.setUpTestData.__func__(cls)

    def page(self):
        self.client.force_login(self.admin)
        return self.client.get(reverse("service_log_detail", args=[self.log.pk]))

    def test_scoped_styles_and_fact_order(self):
        response = self.page()
        self.assertContains(response, "r1-admin-log-detail")
        for name in ("r1_admin_logs.css", "r1_admin_log_detail.css"):
            self.assertContains(response, name, count=1)
        html = response.content.decode()
        labels = ["Actual time", "Actual hours", "Kilometres", "Break"]
        positions = [html.index(f"<dt>{label}</dt>") for label in labels]
        self.assertEqual(positions, sorted(positions))

    def test_complete_notes_and_original_information_are_retained(self):
        self.log.case_notes = "CaseFirstLine\n" + "LongCase" * 80
        self.log.worker_notes = "WorkerFirstLine\n" + "LongWorker" * 80
        self.log.source = ServiceLog.Source.UNSCHEDULED
        self.log.unscheduled_reason = "Fictional reason kept in full"
        self.log.save()
        response = self.page()
        for text in (self.log.case_notes, self.log.worker_notes, self.log.unscheduled_reason,
                     "Shift ID", "Service type", "Support item", "Submitted",
                     "No attachments.", "No files were submitted with this service log."):
            self.assertContains(response, text)

    def test_review_contract_remains_native_and_status_bound(self):
        response = self.page()
        for route in ("service_log_approve", "service_log_reject"):
            self.assertContains(response, f'action="{reverse(route, args=[self.log.pk])}"')
        self.assertContains(response, 'type="text" name="rejection_reason" required')
        self.assertContains(response, 'class="service-log-reject-disclosure"')
        for status in (ServiceLog.Status.APPROVED, ServiceLog.Status.REJECTED, ServiceLog.Status.INVOICED):
            self.log.status = status
            self.log.save(update_fields=["status"])
            response = self.page()
            for route in ("service_log_approve", "service_log_reject"):
                self.assertNotContains(response, f'action="{reverse(route, args=[self.log.pk])}"')

    def test_shared_history_is_not_reimplemented_and_styles_are_namespaced(self):
        template = (Path(settings.BASE_DIR) / "templates/service_logs/service_log_detail.html").read_text(encoding="utf-8")
        self.assertIn('"invoices/billing_adjustment_history.html" with billing_adjustments=service_log.billing_adjustments.all only', template)
        css = Path(settings.BASE_DIR) / "static/css/r1_admin_log_detail.css"
        self.assertTrue(css.exists())
        self.assertIn(".r1-admin-log-detail .invoice-billing-history", css.read_text(encoding="utf-8"))

    def test_required_reason_has_local_visual_help_without_new_validation_script(self):
        response = self.page()
        self.assertContains(response, 'aria-describedby="r1-log-reject-error"')
        self.assertContains(response, 'id="r1-log-reject-error"')
        self.assertContains(response, 'Rejection reason is required.')

    def test_attachment_empty_state_has_scoped_padding_and_explicit_type_rhythm(self):
        css = (Path(settings.BASE_DIR) / "static/css/r1_admin_log_detail.css").read_text(encoding="utf-8")
        selector = ".r1-admin-log-detail .service-log-attachment-grid > .empty-state"
        for suffix, declarations in [
            ("", ["padding: 16px", "display: grid", "gap: 4px"]),
            (" > strong", ["margin: 0", "font-size: 14px", "line-height: 20px", "font-weight: 500"]),
            (" > p", ["margin: 0", "font-size: 13px", "line-height: 20px", "font-weight: 400"]),
        ]:
            rule = selector + suffix + " {"
            self.assertIn(rule, css)
            body = css.split(rule, 1)[1].split("}", 1)[0]
            for declaration in declarations:
                self.assertIn(declaration, body)
        response = self.page()
        self.assertContains(response, "No attachments.")
        self.assertContains(response, "No files were submitted with this service log.")
