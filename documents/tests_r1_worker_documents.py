"""SW R2 presentation contracts with isolated storage and unchanged business rules."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from documents.models import Document
from documents.storage import StorageOperationError
from documents.tests_r1_ui import Page
from workers.models import SupportWorker


class WorkerDocumentsR2Tests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.media.name,
            STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
                      'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}},
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', ADMIN_NOTIFICATION_EMAILS=[])
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.user = get_user_model().objects.create_user(username='fictional_sw_r2')
        UserProfile.objects.create(user=self.user, role='support_worker', is_active_worker=True)
        self.worker = SupportWorker.objects.create(user=self.user, first_name='Fictional', last_name='Worker')
        self.client.force_login(self.user)

    def form_page(self, response):
        self.assertEqual(response.status_code, 200)
        root = Page(response).root
        return root, next(f for f in root.find('form') if f.attrs.get('enctype') == 'multipart/form-data')

    def payload(self, **values):
        return {'title': 'Fictional membership', 'issue_date': '2026-10-01',
                'expiry_date': '2027-10-01', 'notes': 'Fictional retained notes.',
                'file': SimpleUploadedFile('fictional.pdf', b'%PDF-1.4\n', content_type='application/pdf'), **values}

    def test_list_opts_into_own_shell_with_grouped_rows_and_preserved_actions(self):
        doc = Document.objects.create(worker=self.worker, uploaded_by=self.user, file='fictional.pdf',
            title='Fictional police', required_document_type='police_check', review_status='rejected',
            expiry_date=date(2027, 10, 20), category='compliance')
        response = self.client.get(reverse('worker_document_list'))
        self.assertContains(response, 'css/r1_worker_documents.css')
        self.assertNotContains(response, 'css/r1_admin_documents.css')
        root = Page(response).root
        groups = [n for n in root.find() if n.has_class('sw-document-required')]
        self.assertEqual(len(groups), 1)
        self.assertContains(response, 'Expires 20/10/2027')
        actions = [n for n in root.find() if n.has_class('sw-document-actions')]
        self.assertEqual(len(actions), 6)
        self.assertEqual([a.text for a in actions[0].find('a')], ['View', 'Upload again'])
        self.assertTrue(actions[0].find('a', href=reverse('worker_document_detail', args=[doc.pk])))
        self.assertEqual(actions[0].find('a')[-1].attrs['href'], reverse('worker_document_upload') + '?type=police_check')

    def test_other_rows_group_filename_status_and_detail_link(self):
        doc = Document.objects.create(worker=self.worker, uploaded_by=self.user, file='fictional.docx',
            original_filename='fictional-original.docx', title='Fictional membership', category='compliance',
            review_status='pending_review')
        response = self.client.get(reverse('worker_document_list'))
        root = Page(response).root
        group = next(n for n in root.find() if n.has_class('sw-document-other-list'))
        link = group.find('a', href=reverse('worker_document_detail', args=[doc.pk]))[0]
        for text in ('Fictional membership', 'fictional-original.docx', 'Pending review', 'Compliance'):
            self.assertIn(text, link.text)

    def test_upload_preserves_native_form_fields_and_editable_date_controls(self):
        for required in (False, True):
            response = self.client.get(reverse('worker_document_upload'), {'type': 'police_check'} if required else {})
            _, form = self.form_page(response)
            self.assertTrue(form.has_class('sw-document-form'))
            self.assertEqual(form.attrs['method'], 'post')
            self.assertIn('novalidate', form.attrs)
            names = {n.attrs['name'] for n in form.find() if 'name' in n.attrs}
            self.assertEqual(names, {'csrfmiddlewaretoken', 'issue_date', 'expiry_date', 'file', 'notes',
                                    'required_document_type' if required else 'title'})
            for field in ('issue_date', 'expiry_date'):
                native = form.find('input', name=field)[0]
                self.assertEqual(native.attrs['type'], 'date')
                self.assertNotIn('readonly', native.attrs)
            self.assertEqual(len(form.find('input', **{'data-maintenance-date-proxy': None})), 2)
            self.assertEqual(len(form.find('p', **{'data-sw-selected-file': None})), 1)
            self.assertContains(response, 'js/r1_worker_documents.js')
            self.assertContains(response, 'PDF, JPG, PNG, DOC, or DOCX up to 10 MB.')
            self.assertContains(response, 'Submit for Review')

    def test_invalid_dates_and_storage_error_keep_values_and_errors_in_new_scope(self):
        response = self.client.post(reverse('worker_document_upload'), self.payload(expiry_date='2026-09-01'))
        _, form = self.form_page(response)
        self.assertTrue(form.has_class('sw-document-form'))
        self.assertContains(response, 'Expiry date must be after issue date.')
        self.assertContains(response, 'Fictional retained notes.')
        self.assertEqual(form.find('input', name='issue_date')[0].attrs['value'], '2026-10-01')
        self.assertEqual(Document.objects.count(), 0)
        with patch('documents.views.Document.save', side_effect=StorageOperationError('Fictional storage failure.')):
            response = self.client.post(reverse('worker_document_upload'), self.payload())
        _, form = self.form_page(response)
        self.assertTrue(form.has_class('sw-document-form'))
        self.assertContains(response, 'Fictional storage failure.')
        self.assertContains(response, 'Fictional retained notes.')
        self.assertEqual(Document.objects.count(), 0)

    def test_upload_still_creates_pending_own_document_and_redirects(self):
        response = self.client.post(reverse('worker_document_upload'), self.payload())
        self.assertRedirects(response, reverse('worker_document_list'))
        doc = Document.objects.get()
        self.assertEqual(doc.worker, self.worker)
        self.assertEqual(doc.uploaded_by, self.user)
        self.assertEqual(doc.review_status, 'pending_review')
        self.assertEqual(doc.original_filename, 'fictional.pdf')

    def test_worker_detail_does_not_opt_into_new_scope(self):
        doc = Document.objects.create(worker=self.worker, uploaded_by=self.user, file='fictional.pdf', title='Fictional detail')
        response = self.client.get(reverse('worker_document_detail', args=[doc.pk]))
        self.assertNotContains(response, 'css/r1_worker_documents.css')
        self.assertNotContains(response, 'js/r1_worker_documents.js')

    def test_native_file_control_keeps_approved_inner_frame(self):
        css = (Path(settings.BASE_DIR) / 'static/css/r1_worker_documents.css').read_text()
        selector = '.app-shell.r1-ui .sw-documents .sw-document-file input[type=file]'
        self.assertIn(selector, css)
        rule = css.split(selector, 1)[1].split('}', 1)[0]
        for declaration in ('border:1px solid var(--r1-strong-border)', 'background:var(--r1-surface)',
                            'padding:9px 12px', 'height:auto', 'min-height:56px'):
            self.assertIn(declaration, rule)

    def test_global_notifications_inherit_confirmed_r1_document_styles(self):
        css = (Path(settings.BASE_DIR) / 'static/css/r1_worker_documents.css').read_text()
        base = css.split('.r1-worker-documents .message {', 1)[-1].split('}', 1)[0]
        for declaration in ('padding:12px 16px', 'font-size:14px', 'line-height:20px',
                            'box-shadow:none', 'border-radius:6px'):
            self.assertIn(declaration, base)
        for state, color, background in (
            ('error', '--r1-danger', '#faeef0'), ('success', '--r1-success', '#edf5f0'),
            ('warning', '--r1-warning', 'var(--r1-warning-soft)'),
            ('info', '--r1-accent', 'var(--r1-blue-soft)'),
        ):
            selector = f'.r1-worker-documents .message.{state} {{'
            self.assertIn(selector, css)
            rule = css.split(selector, 1)[1].split('}', 1)[0]
            self.assertIn(f'color:var({color})', rule)
            self.assertIn(f'border-left-color:var({color})', rule)
            self.assertIn(f'background:{background}', rule)

    def test_storage_failure_does_not_report_a_missing_file(self):
        message = 'Could not upload document to private storage. Please try again later or contact admin.'
        with patch('documents.views.Document.save', side_effect=StorageOperationError(message)):
            response = self.client.post(reverse('worker_document_upload'), self.payload())
        self.assertContains(response, message)
        self.assertNotContains(response, 'This field is required.')
        self.assertFalse(response.context['form'].errors)
        self.assertEqual(Document.objects.count(), 0)
