"""B06.2 scoped upload presentation and preserved native submission contracts."""
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
from documents.models import Document
from documents.storage import StorageOperationError
from documents.tests_r1_ui import Page
from participants.models import Participant
from workers.models import SupportWorker


class UploadR1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username='b062_fictional_admin')
        UserProfile.objects.create(user=cls.admin, role='admin')
        cls.worker_user = get_user_model().objects.create_user(username='b062_fictional_worker')
        UserProfile.objects.create(user=cls.worker_user, role='support_worker', is_active_worker=True)
        cls.worker = SupportWorker.objects.create(user=cls.worker_user, first_name='Fictional', last_name='Worker')
        cls.participant = Participant.objects.create(first_name='Fictional', last_name='Participant')

    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.media.name,
            STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
                      'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}},
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', ADMIN_NOTIFICATION_EMAILS=[])
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.client.force_login(self.admin)

    def form(self, response):
        self.assertEqual(response.status_code, 200)
        page = Page(response).root
        return page, next(f for f in page.find('form') if f.attrs.get('enctype') == 'multipart/form-data')

    def payload(self, **changes):
        return {'title': 'Fictional upload title', 'category': 'general', 'participant': self.participant.pk,
                'notes': 'Fictional notes retained.', 'file': SimpleUploadedFile('fictional.pdf', b'%PDF-1.4\n'),
                **changes}

    def test_full_upload_has_dedicated_r1_shell_not_list_scope(self):
        response = self.client.get(reverse('document_create'))
        page, form = self.form(response)
        self.assertTrue(any(n.has_class('r1-admin-upload') for n in page.find()))
        self.assertFalse(any(n.has_class('r1-admin-documents') for n in page.find()))
        self.assertContains(response, 'css/r1_admin_upload.css')
        self.assertNotContains(response, 'css/r1_admin_documents.css')
        self.assertTrue(form.has_class('r1-upload-form'))

    def test_full_upload_native_fields_and_csrf_preserved(self):
        response = self.client.get(reverse('document_create'))
        _, form = self.form(response)
        self.assertEqual(form.attrs['method'], 'post')
        self.assertIn('novalidate', form.attrs)
        names = {n.attrs['name'] for n in form.find() if 'name' in n.attrs}
        self.assertEqual(names, {'csrfmiddlewaretoken', 'title', 'category', 'file', 'participant',
                                 'worker', 'invoice', 'service_log', 'notes'})
        self.assertContains(response, 'Select at least one linked record.')
        self.assertContains(response, 'Maximum 10 MB')
        self.assertEqual(len(form.find('input', type='file')), 1)

    def test_person_upload_keeps_context_hidden_links_and_safe_next(self):
        for owner in ('participant', 'worker'):
            person = getattr(self, owner)
            next_url = reverse(f'{owner}_document_files', args=[person.pk])
            response = self.client.get(reverse('document_create'), {owner: person.pk, 'next': next_url})
            _, form = self.form(response)
            self.assertNotContains(response, '<h2>Linked Records</h2>')
            self.assertContains(response, person.display_name)
            self.assertTrue(form.find('a', href=next_url))
            for field in ('participant', 'worker', 'invoice', 'service_log', 'required_document_type'):
                self.assertEqual(form.find('input', name=field)[0].attrs['type'], 'hidden')
            self.assertEqual(form.find('input', name=owner)[0].attrs['value'], str(person.pk))
            self.assertEqual(form.find('input', name='next')[0].attrs['value'], next_url)

    def test_dialog_scoped_for_both_owners_with_existing_hooks(self):
        for owner in ('participant', 'worker'):
            person = getattr(self, owner)
            route = reverse(f'{owner}_document_files', args=[person.pk])
            response = self.client.get(route)
            page = Page(response).root
            dialog = page.find('dialog', id='document-upload-dialog')[0]
            self.assertTrue(dialog.has_class('r1-ui'))
            self.assertTrue(dialog.has_class('r1-upload-dialog'))
            form = dialog.find('form')[0]
            self.assertEqual(form.attrs['method'], 'post')
            self.assertEqual(form.attrs['action'], reverse('document_create'))
            self.assertEqual(form.attrs['enctype'], 'multipart/form-data')
            self.assertTrue(form.find('input', name='csrfmiddlewaretoken'))
            self.assertEqual(form.find('input', name=owner)[0].attrs['value'], str(person.pk))
            self.assertEqual(form.find('input', name='next')[0].attrs['value'], route)
            self.assertEqual([n.text for n in dialog.find('button', **{'data-document-upload-close': None})],
                             ['Close', 'Cancel'])
            self.assertContains(response, 'Maximum 10 MB')
            self.assertContains(response, 'css/r1_admin_upload.css')
            self.assertTrue(page.find('a', **{'data-document-upload-open': None}))

    def test_validation_errors_preserve_bound_values_without_creating_records(self):
        response = self.client.post(reverse('document_create'), self.payload(participant='',
            file=SimpleUploadedFile('fictional.exe', b'not allowed')))
        _, form = self.form(response)
        self.assertTrue(form.has_class('r1-upload-form'))
        for text in ('Select at least one linked record.', 'Unsupported file type.',
                     'Choose the file again before uploading.', 'Fictional notes retained.'):
            self.assertContains(response, text)
        self.assertEqual(form.find('input', name='title')[0].attrs['value'], 'Fictional upload title')
        self.assertEqual(Document.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_storage_failure_preserves_person_context_values_and_original_message(self):
        route = reverse('participant_document_files', args=[self.participant.pk])
        with patch('documents.views.Document.save', side_effect=StorageOperationError('Fictional storage unavailable.')):
            response = self.client.post(reverse('document_create'), self.payload(next=route))
        _, form = self.form(response)
        self.assertTrue(form.has_class('r1-upload-form'))
        self.assertContains(response, 'Fictional storage unavailable.')
        self.assertContains(response, 'Choose the file again before uploading.')
        self.assertContains(response, 'Fictional notes retained.')
        self.assertNotContains(response, '<h2>Linked Records</h2>')
        self.assertEqual(form.find('input', name='next')[0].attrs['value'], route)
        self.assertEqual(form.find('input', name='title')[0].attrs['value'], 'Fictional upload title')
        self.assertEqual(Document.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_upload_remains_native_post_and_safe_return(self):
        route = reverse('participant_document_files', args=[self.participant.pk])
        response = self.client.post(reverse('document_create'), self.payload(next=route))
        self.assertRedirects(response, route)
        doc = Document.objects.get()
        self.assertEqual(doc.original_filename, 'fictional.pdf')
        self.assertEqual(doc.notes, 'Fictional notes retained.')
        self.assertEqual(doc.uploaded_by, self.admin)
        response = self.client.post(reverse('document_create'), self.payload(next='https://example.invalid/unsafe'))
        self.assertNotIn('example.invalid', response['Location'])

    def test_upload_csrf_and_worker_permissions_stay_enforced(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.admin)
        self.assertEqual(strict.post(reverse('document_create'), self.payload()).status_code, 403)
        self.client.force_login(self.worker_user)
        self.assertEqual(self.client.get(reverse('document_create')).status_code, 403)
        self.assertEqual(self.client.post(reverse('document_create'), self.payload()).status_code, 403)

    def test_other_pages_do_not_acquire_upload_shell(self):
        doc = Document.objects.create(title='Fictional untouched', category='general',
            participant=self.participant, uploaded_by=self.admin, file='fictional.pdf')
        for route in (reverse('document_edit', args=[doc.pk]), reverse('document_delete', args=[doc.pk]),
                      doc.get_absolute_url(), reverse('document_list')):
            response = self.client.get(route)
            self.assertNotContains(response, 'r1-admin-upload')
            self.assertNotContains(response, 'css/r1_admin_upload.css')
        self.client.force_login(self.worker_user)
        response = self.client.get(reverse('worker_document_upload'))
        self.assertNotContains(response, 'r1-admin-upload')
        self.assertNotContains(response, 'css/r1_admin_upload.css')

    def test_scoped_sheet_exists_and_uses_existing_tokens(self):
        css_path = Path(settings.BASE_DIR) / 'static/css/r1_admin_upload.css'
        self.assertTrue(css_path.exists(), 'Expected dedicated B06.2 scoped stylesheet')
        css = css_path.read_text(encoding='utf-8')
        for scope in ('.r1-admin-upload', '.r1-upload-dialog'):
            self.assertIn(scope, css)
        for token in ('--r1-accent', '--r1-text', '--r1-muted', '--r1-strong-border', '--r1-danger'):
            self.assertIn(token, css)
        self.assertNotIn(':root', css)
        self.assertIn('600px', css)
        self.assertIn('872px', css)
        self.assertIn('44px', css)
        self.assertIn('overflow-y: auto', css)
