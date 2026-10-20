"""B06.3 presentation boundary and unchanged metadata/deletion contracts."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from core.models import AuditLog
from documents.forms import DocumentMetadataForm
from documents.models import Document
from documents.storage import StorageOperationError
from documents.tests_r1_ui import Page
from participants.models import Participant
from workers.models import SupportWorker


class FileMaintenanceR1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username='b063_fictional_admin')
        UserProfile.objects.create(user=cls.admin, role='admin')
        cls.worker_user = get_user_model().objects.create_user(username='b063_fictional_worker')
        UserProfile.objects.create(user=cls.worker_user, role='support_worker', is_active_worker=True)
        cls.worker = SupportWorker.objects.create(user=cls.worker_user, first_name='Fictional', last_name='Worker')
        cls.participant = Participant.objects.create(first_name='Fictional', last_name='Participant')

    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        override = override_settings(MEDIA_ROOT=self.media.name,
            STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
                      'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
        override.enable()
        self.addCleanup(override.disable)
        self.client.force_login(self.admin)
        self.doc = Document.objects.create(title='Fictional support plan', category='compliance',
            participant=self.participant, uploaded_by=self.admin, review_status='approved',
            original_filename='fictional-original.pdf',
            file=SimpleUploadedFile('fictional.pdf', b'%PDF-1.4 Fictional only'),
            issue_date=date(2026, 10, 13), expiry_date=date(2027, 10, 13), notes='Fictional notes')
        self.edit = reverse('document_edit', args=[self.doc.pk])
        self.delete = reverse('document_delete', args=[self.doc.pk])
        self.back = reverse('participant_document_files', args=[self.participant.pk])

    def payload(self, **changes):
        return {'title': 'Fictional updated plan', 'category': 'general', 'review_status': 'pending_review',
                'issue_date': '2026-10-13', 'expiry_date': '2027-10-13', 'notes': 'Fictional updated notes',
                'next': self.back, **changes}

    def form(self, response, class_name):
        self.assertEqual(response.status_code, 200)
        return next(n for n in Page(response).root.find('form') if n.has_class(class_name))

    def test_both_pages_opt_into_maintenance_scope_only(self):
        for route in (self.edit, self.delete):
            response = self.client.get(route)
            self.assertContains(response, 'r1-admin-document-maintenance')
            self.assertContains(response, 'css/r1_admin_document_maintenance.css')
            self.assertNotContains(response, 'r1-admin-upload')
            self.assertNotContains(response, 'css/r1_admin_documents.css')

    def test_edit_preserves_exact_native_form_fields_and_actions(self):
        response = self.client.get(self.edit, {'next': self.back})
        form = self.form(response, 'document-metadata-form')
        names = {n.attrs['name'] for n in form.find() if n.attrs.get('name')}
        self.assertEqual(names, {'csrfmiddlewaretoken', 'next', 'title', 'category', 'review_status',
                                 'issue_date', 'expiry_date', 'notes'})
        self.assertEqual(form.attrs['method'], 'post')
        self.assertIn('novalidate', form.attrs)
        self.assertEqual(form.find('input', name='next')[0].attrs['value'], self.back)
        for name in ('issue_date', 'expiry_date'):
            self.assertEqual(form.find('input', name=name)[0].attrs['type'], 'date')
        self.assertFalse(form.find('input', type='file'))
        for text in ('without replacing the private CrazyDomains file.', 'Original filename',
                     'CrazyDomains secure file name', self.doc.file.name, self.doc.filename,
                     'Owner', self.participant.display_name, 'Filing details', 'Notes'):
            self.assertContains(response, text)

    def test_invalid_expiry_retains_bound_values_and_inline_error_without_saving(self):
        before = Document.objects.values().get(pk=self.doc.pk)
        response = self.client.post(self.edit, self.payload(expiry_date='2026-10-12'))
        form = self.form(response, 'document-metadata-form')
        self.assertContains(response, 'Expiry date must be after issue date.')
        self.assertTrue(form.find('span', id='id_expiry_date_error'))
        self.assertEqual(form.find('input', name='title')[0].attrs['value'], 'Fictional updated plan')
        self.assertEqual(form.find('input', name='expiry_date')[0].attrs['value'], '2026-10-12')
        self.assertContains(response, 'Fictional updated notes')
        self.assertEqual(Document.objects.values().get(pk=self.doc.pk), before)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_equal_dates_and_optional_dates_keep_existing_validation(self):
        for value in ('2026-10-13', ''):
            form = DocumentMetadataForm(self.payload(expiry_date=value), instance=self.doc,
                                        document_owner='participants')
            self.assertTrue(form.is_valid(), form.errors)

    def test_metadata_save_keeps_private_file_and_safe_return(self):
        name = self.doc.file.name
        content = Path(self.doc.file.path).read_bytes()
        response = self.client.post(self.edit, self.payload())
        self.assertRedirects(response, self.back)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.file.name, name)
        self.assertEqual(Path(self.doc.file.path).read_bytes(), content)
        self.assertEqual(self.doc.original_filename, 'fictional-original.pdf')
        self.assertEqual(self.doc.notes, 'Fictional updated notes')
        response = self.client.post(self.edit, self.payload(next='https://example.invalid/unsafe'))
        self.assertNotIn('example.invalid', response['Location'])

    def test_delete_confirmation_preserves_all_context_warning_and_post(self):
        response = self.client.get(self.delete, {'next': self.back})
        form = self.form(response, 'document-delete-actions')
        self.assertEqual(form.attrs['method'], 'post')
        self.assertEqual({n.attrs['name'] for n in form.find() if n.attrs.get('name')},
                         {'csrfmiddlewaretoken', 'next'})
        self.assertTrue(form.find('input', name='next', value=self.back))
        button = form.find('button', type='submit')[0]
        self.assertTrue(button.has_class('danger-outline'))
        for text in ('Title', self.doc.title, 'Original filename', self.doc.filename,
                     'CrazyDomains secure file name', self.doc.file.name, 'Owner', 'Folder',
                     'NDIS Forms', 'Status', 'Approved', 'Uploaded by', 'Uploaded',
                     'This action cannot be undone.',
                     'The document record will stay in Admin if the private file cannot be removed.'):
            self.assertContains(response, text)

    def test_storage_failure_uses_error_scope_and_keeps_record_file_and_return(self):
        before = Document.objects.values().get(pk=self.doc.pk)
        with patch.object(self.doc.file.storage, 'delete', side_effect=StorageOperationError('Fictional failure')):
            response = self.client.post(self.delete, {'next': self.back})
        form = self.form(response, 'document-delete-actions')
        self.assertContains(response, 'Could not delete document from private storage. Please try again later or contact admin.')
        self.assertContains(response, 'message error')
        self.assertContains(response, 'r1-admin-document-maintenance')
        self.assertEqual(form.find('input', name='next')[0].attrs['value'], self.back)
        self.assertEqual(Document.objects.values().get(pk=self.doc.pk), before)
        self.assertTrue(Path(self.doc.file.path).exists())
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_delete_success_retains_existing_storage_audit_redirect_contract(self):
        file = Path(self.doc.file.path)
        pk = self.doc.pk
        response = self.client.post(self.delete, {'next': self.back})
        self.assertRedirects(response, self.back)
        self.assertFalse(file.exists())
        self.assertFalse(Document.objects.filter(pk=pk).exists())
        self.assertEqual(AuditLog.objects.filter(action=AuditLog.Action.DOCUMENT_DELETED,
                                                object_id=str(pk)).count(), 1)

    def test_gets_do_not_mutate_and_both_posts_enforce_csrf_and_admin(self):
        before = Document.objects.values().get(pk=self.doc.pk)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.admin)
        for route in (self.edit, self.delete):
            self.client.get(route)
            self.assertEqual(strict.post(route, self.payload()).status_code, 403)
        self.assertEqual(Document.objects.values().get(pk=self.doc.pk), before)
        self.assertEqual(AuditLog.objects.count(), 0)
        self.client.force_login(self.worker_user)
        for route in (self.edit, self.delete):
            self.assertEqual(self.client.get(route).status_code, 403)
            self.assertEqual(self.client.post(route, self.payload()).status_code, 403)

    def test_other_pages_never_acquire_maintenance_scope(self):
        for route in (reverse('document_create'), self.doc.get_absolute_url(), self.back,
                      reverse('document_list')):
            response = self.client.get(route)
            self.assertNotContains(response, 'r1-admin-document-maintenance')
            self.assertNotContains(response, 'css/r1_admin_document_maintenance.css')

    def test_local_sheet_and_calendar_keep_confirmed_tokens_native_fallback(self):
        sheet = Path(settings.BASE_DIR) / 'static/css/r1_admin_document_maintenance.css'
        self.assertTrue(sheet.exists())
        css = sheet.read_text(encoding='utf-8')
        for text in ('--r1-accent', '--r1-danger', '--r1-warning-soft', '872px', '44px',
                     'appearance: base-select', 'font-size: 13px', 'var(--r1-blue-soft)'):
            self.assertIn(text, css)
        self.assertNotIn(':root', css)
        response = self.client.get(self.edit)
        self.assertContains(response, 'js/date_time_picker.js')
        self.assertContains(response, 'js/r1_document_maintenance.js')
        self.assertContains(response, 'data-maintenance-date')
        self.assertContains(response, 'data-picker-trigger hidden')

    def test_worker_owner_and_all_status_labels_remain_correct(self):
        self.doc.participant = None
        self.doc.worker = self.worker
        for status, label in Document.ReviewStatus.choices:
            self.doc.review_status = status
            self.doc.save()
            response = self.client.get(self.delete)
            self.assertContains(response, self.worker.display_name)
            self.assertContains(response, label)
            self.assertContains(response, f'document-status-{status}')

    def test_notes_height_override_matches_the_control_rule_specificity(self):
        css = (Path(settings.BASE_DIR) / 'static/css/r1_admin_document_maintenance.css').read_text(encoding='utf-8')
        self.assertIn('.app-shell.r1-ui.r1-admin-document-maintenance .document-metadata-form .field textarea { min-height: 88px;', css)
