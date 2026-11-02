from pathlib import Path
from django.conf import settings
from django.test import TestCase
from documents.tests_r1_ui import Page
from invoices import tests_r1_admin_invoice_detail as detail_contracts


class LegacyInvoiceOverflowTests(TestCase):
    create_user_with_role = detail_contracts.R1AdminInvoiceDetailTests.create_user_with_role
    create_service_log = detail_contracts.R1AdminInvoiceDetailTests.create_service_log
    setUp = detail_contracts.R1AdminInvoiceDetailTests.setUp
    detail = detail_contracts.R1AdminInvoiceDetailTests.detail

    def test_accountant_lines_have_one_named_focusable_scroll_region(self):
        for state, invoice in self.records.items():
            with self.subTest(state=state):
                response = self.detail(invoice, self.accountant_user)
                regions = [n for n in Page(response).root.find('div') if n.has_class('legacy-invoice-lines-scroll')]
                self.assertEqual(len(regions), 1)
                region = regions[0]
                self.assertEqual(region.attrs.get('role'), 'region')
                self.assertEqual(region.attrs.get('aria-label'), 'Invoice lines')
                self.assertEqual(region.attrs.get('tabindex'), '0')
                self.assertEqual(len(region.find('table')), 1)
                self.assertEqual([n.text for n in region.find('th')], ['Item', 'Description', 'Unit', 'Quantity', 'Unit price', 'Total'])
                for value in ('SNAP-SERVICE', 'Saved billing support item', '2.25', '$72.10', '$162.23'):
                    self.assertIn(value, region.text)
                self.assertFalse(response.context['r1_invoice_detail'])

    def test_admin_r1_details_keep_their_existing_region_without_legacy_wrapper(self):
        for user in (self.admin_user, self.super_admin):
            for records in (self.records, self.sc_records):
                for invoice in records.values():
                    response = self.detail(invoice, user)
                    self.assertNotContains(response, 'legacy-invoice-lines-scroll')
                    self.assertTemplateUsed(response, 'invoices/partials/r1_invoice_detail.html')
                    self.assertContains(response, 'aria-label="Invoice lines"')

    def test_scroll_css_is_scoped_to_legacy_region(self):
        css = (Path(settings.BASE_DIR) / 'static/css/invoice_billing.css').read_text(encoding='utf-8')
        selector = '.legacy-invoice-lines-scroll {'
        self.assertIn(selector, css)
        body = css.split(selector, 1)[1].split('}', 1)[0]
        for declaration in ('max-width: 100%', 'min-width: 0', 'overflow-x: auto'):
            self.assertIn(declaration, body)
