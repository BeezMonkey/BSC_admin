"""Approved v03 presentation contracts for both Admin person-file pages."""
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.models import AuditLog
from documents.models import Document
from documents import tests_r1_ui as fixtures


class AdminPersonGroupingTests(TestCase):
    setUpTestData = classmethod(fixtures.AdminDocumentsR1Tests.setUpTestData.__func__)

    def setUp(self):
        self.client.force_login(self.users['admin'])

    def page(self, owner):
        person = self.worker if owner == 'worker' else self.participant
        response = self.client.get(reverse(f'{owner}_document_files', args=[person.pk]))
        self.assertEqual(response.status_code, 200)
        return fixtures.Page(response).root

    def test_return_and_upload_share_header_in_original_button_styles(self):
        for owner, label in [('participant', 'Back to Participant'), ('worker', 'Back to Support Worker')]:
            with self.subTest(owner=owner):
                page = self.page(owner)
                header = next(node for node in page.find('div') if node.has_class('page-header'))
                matches = [node for node in header.find('div') if node.has_class('fup-header-actions')]
                self.assertEqual(len(matches), 1, 'Approved header action row must exist')
                actions = matches[0]
                links = actions.find('a')
                self.assertEqual([link.text for link in links], [label, 'Upload File'])
                self.assertEqual(links[0].attrs['class'], 'button secondary')
                self.assertEqual(links[1].attrs['class'], 'button')
                person = self.worker if owner == 'worker' else self.participant
                self.assertEqual(links[0].attrs['href'], reverse(f'{owner}_detail', args=[person.pk]))
                self.assertIn('data-document-upload-open', links[1].attrs)
                self.assertIn('data-upload-category', links[1].attrs)
                self.assertEqual(parse_qs(urlsplit(links[1].attrs['href']).query)[owner], [str(person.pk)])
                self.assertFalse(any(node.has_class('r1-document-return') for node in page.find()))

    def test_original_folder_information_is_one_summary_not_nested_cards(self):
        for owner, kind, key, value in [('participant', 'Participant', 'NDIS', 'QA-ONLY-001'),
                                        ('worker', 'Support Worker', 'Email', 'worker@example.invalid')]:
            with self.subTest(owner=owner):
                page = self.page(owner)
                matches = [node for node in page.find('div') if node.has_class('fup-document-summary')]
                self.assertEqual(len(matches), 1, 'Approved grouped summary must exist')
                summary = matches[0]
                self.assertEqual([node.attrs.get('class') for node in summary.children if hasattr(node, 'attrs')],
                    ['document-person-hero-main', 'document-person-meta'])
                self.assertFalse(summary.has_class('card'))
                self.assertFalse(any(node.has_class('card') for node in summary.find()))
                self.assertEqual([node.text for node in summary.find('dt')], ['Person type', key, 'Files', 'Review'])
                self.assertEqual([node.text for node in summary.find('dd')], [kind, value, '3 total', '1 pending'])
                self.assertIn('Files are grouped for CrazyDomains storage while original filenames remain visible for Admin.', summary.text)
                self.assertEqual(len(summary.find('h2')), 1)

    def test_empty_values_counts_and_existing_list_still_render(self):
        response = self.client.get(reverse('participant_document_files', args=[self.empty.pk]))
        self.assertEqual(response.status_code, 200)
        page = fixtures.Page(response).root
        matches = [node for node in page.find('div') if node.has_class('fup-document-summary')]
        self.assertEqual(len(matches), 1, 'Approved grouped summary must exist')
        summary = matches[0]
        self.assertEqual([node.text for node in summary.find('dd')], ['Participant', 'Not provided', '0 total', '0 pending'])
        for owner in ['participant', 'worker']:
            page = self.page(owner)
            self.assertEqual([th.text for th in page.find('th')],
                ['File', 'Folder', 'Uploaded', 'Status', 'Expiry', 'Uploaded by', 'Actions'])
            self.assertEqual(len(page.find('a', **{'data-document-preview-open': None})), 2)

    def test_gets_do_not_change_documents_or_audit_records(self):
        before = list(Document.objects.order_by('pk').values())
        audit_count = AuditLog.objects.count()
        self.page('participant')
        self.page('worker')
        self.assertEqual(before, list(Document.objects.order_by('pk').values()))
        self.assertEqual(audit_count, AuditLog.objects.count())


class AdminPersonGroupingStyleTests(SimpleTestCase):
    def test_layout_reuses_tokens_and_mobile_two_column_rules(self):
        css = (Path(settings.BASE_DIR) / 'static/css/r1_admin_documents.css').read_text(encoding='utf-8')
        self.assertIn('.r1-admin-documents .fup-document-summary {', css)
        self.assertIn('.r1-admin-documents .page-header .fup-header-actions {', css)
        self.assertIn('grid-template-columns: minmax(0, 1fr) auto;', css)
        self.assertIn('.fup-document-summary .document-person-meta > div:nth-child(odd)', css)
