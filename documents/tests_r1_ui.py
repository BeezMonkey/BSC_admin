"""Presentation-only Admin documents contracts; no production data or storage."""
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from core.models import AuditLog
from documents.models import Document
from participants.models import Participant
from workers.models import SupportWorker


class Element:
    def __init__(self, tag, attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    @property
    def text(self):
        return ' '.join(' '.join(child.text if isinstance(child, Element) else child
                                 for child in self.children).split())

    def has_class(self, name):
        return name in self.attrs.get('class', '').split()

    def find(self, tag=None, **attrs):
        found = []
        for child in self.children:
            if isinstance(child, Element):
                if (tag is None or child.tag == tag) and all(
                        key in child.attrs and child.attrs[key] == value for key, value in attrs.items()):
                    found.append(child)
                found.extend(child.find(tag, **attrs))
        return found


class Page(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
            'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, response):
        super().__init__(convert_charrefs=True)
        self.root = self.current = Element('root')
        self.feed(response.content.decode())

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in self.VOID:
            self.current = node

    def handle_endtag(self, tag):
        node = self.current
        while node.parent:
            if node.tag == tag:
                self.current = node.parent
                return
            node = node.parent

    def handle_data(self, data):
        self.current.children.append(data)


class ParserContractTests(SimpleTestCase):
    def test_find_missing_boolean_attribute(self):
        page = Page(HttpResponse('<a href="/unrelated/">Unrelated</a>'
                                 '<button type="submit">Upload</button>')).root
        self.assertEqual(page.find('a', **{'data-document-upload-open': None}), [])
        self.assertEqual(page.find('button', **{'data-document-upload-close': None}), [])

    def test_find_present_boolean_attribute(self):
        page = Page(HttpResponse('<a href="/unrelated/">Unrelated</a>'
                                 '<a data-document-upload-open href="/upload/">Open</a>'
                                 '<button>Submit</button>'
                                 '<button data-document-upload-close>Close</button>')).root
        self.assertEqual([node.text for node in page.find('a', **{'data-document-upload-open': None})], ['Open'])
        self.assertEqual([node.text for node in page.find('button', **{'data-document-upload-close': None})], ['Close'])

    def test_find_valued_attribute_keeps_exact_matching(self):
        page = Page(HttpResponse('<a href="/first/">First</a><a href="/second/">Second</a>'
                                 '<a data-document-upload-open="explicit">Valued</a>')).root
        self.assertEqual([node.text for node in page.find('a', href='/second/')], ['Second'])
        self.assertEqual(page.find('a', href='/missing/'), [])
        self.assertEqual([node.text for node in page.find('a', **{'data-document-upload-open': 'explicit'})], ['Valued'])


class AdminDocumentsR1Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media = TemporaryDirectory()
        cls.addClassCleanup(cls.media.cleanup)
        cls.storage = override_settings(
            MEDIA_ROOT=cls.media.name,
            STORAGES={
                'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
                'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
            },
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
            ADMIN_NOTIFICATION_EMAILS=[],
        )
        cls.storage.enable()
        cls.addClassCleanup(cls.storage.disable)
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for role in UserProfile.Role.values:
            user = get_user_model().objects.create_user(username=f'fictional_{role}')
            UserProfile.objects.create(user=user, role=role,
                is_active_worker=role == UserProfile.Role.SUPPORT_WORKER)
            cls.users[role] = user
        cls.participant = Participant.objects.create(first_name='Fictional', last_name='Participant',
            ndis_number='QA-ONLY-001', email='participant@example.invalid', phone='0400000001')
        cls.worker = SupportWorker.objects.create(user=cls.users['support_worker'],
            first_name='Fictional', last_name='Worker', email='worker@example.invalid', phone='0400000002')
        cls.empty = Participant.objects.create(first_name='Fictional Empty', last_name='Folder')
        cls.docs = {}
        for owner, person in [('participant', cls.participant), ('worker', cls.worker)]:
            for status, ext in [('pending_review', 'pdf'), ('approved', 'png'), ('rejected', 'docx')]:
                name = f'{owner}_original_' + 'unbroken_long_filename_' * 6 + f'{status}.{ext}'
                cls.docs[owner, status] = Document.objects.create(
                    title=f'Fictional {owner} {status}', category='compliance',
                    required_document_type='police_check', review_status=status,
                    issue_date=date(2026, 1, 2), expiry_date=date.today() + timedelta(days=10),
                    notes='Fictional metadata retained verbatim.', original_filename=name,
                    file=SimpleUploadedFile(f'private.{ext}', b'fictional-local-only'),
                    uploaded_by=cls.users['admin'], **{owner: person})

    def setUp(self):
        self.client.force_login(self.users['admin'])

    def page(self, route, data=None):
        response = self.client.get(route, data or {})
        self.assertEqual(response.status_code, 200)
        return response, Page(response).root

    def person_route(self, owner):
        person = self.worker if owner == 'worker' else self.participant
        return reverse(f'{owner}_document_files', args=[person.pk])

    def assert_r1(self, page):
        self.assertTrue(any(node.has_class('r1-admin-documents') for node in page.find()),
                        'Expected scoped r1-admin-documents shell')
        self.assertTrue(any(urlsplit(node.attrs.get('href', '')).path.endswith(
            '/css/r1_admin_documents.css') for node in page.find('link', rel='stylesheet')),
            'Expected scoped css/r1_admin_documents.css stylesheet')

    def test_r1_shell_and_sheet_on_directory_both_people_and_detail(self):
        for route in [reverse('document_list'), self.person_route('participant'),
                      self.person_route('worker'), self.docs['worker', 'pending_review'].get_absolute_url()]:
            with self.subTest(route=route):
                self.assert_r1(self.page(route)[1])

    def test_admin_and_superadmin_only(self):
        doc = self.docs['worker', 'pending_review']
        routes = [reverse('document_list'), self.person_route('participant'), self.person_route('worker'),
                  doc.get_absolute_url(), reverse('document_preview', args=[doc.pk])]
        for role, user in self.users.items():
            self.client.force_login(user)
            for route in routes:
                with self.subTest(role=role, route=route):
                    self.assertEqual(self.client.get(route).status_code,
                                     200 if role in ('admin', 'super_admin') else 403)
            if role not in ('admin', 'super_admin'):
                self.assertEqual(self.client.post(reverse('document_review', args=[doc.pk]),
                    {'review_status': 'approved'}).status_code, 403)
        self.client.logout()
        for route in routes:
            self.assertEqual(self.client.get(route).status_code, 302)
        doc.refresh_from_db()
        self.assertEqual(doc.review_status, 'pending_review')

    def test_directory_columns_copy_filter_controls_and_actions(self):
        for owner in ('participants', 'workers'):
            with self.subTest(owner=owner):
                response, page = self.page(reverse('document_list'), {'owner': owner})
                self.assertEqual([th.text for th in page.find('th')],
                    ['Person', 'Contact', 'Type', 'Files', 'Pending', 'Expiring soon', 'Last uploaded', 'Actions'])
                for text in ['Manage files stored in CrazyDomains by person, folder, and original filename.',
                             'Total files', 'Pending review', 'Expiring soon', 'Person folders',
                             'Participants', 'Support Workers', 'Search', 'Reset', 'Open files', 'Upload']:
                    self.assertContains(response, text)
                forms = [form for form in page.find('form') if form.attrs.get('method', 'get').lower() == 'get']
                self.assertEqual(len(forms), 1)
                fields = {node.attrs.get('name'): node for node in forms[0].find() if node.attrs.get('name')}
                self.assertTrue({'owner', 'q', 'review_status', 'category', 'coverage'} <= fields.keys())
                self.assertEqual(fields['owner'].attrs['value'], owner)
                self.assertEqual({option.attrs['value'] for option in fields['coverage'].find('option')},
                                 {'', 'has_documents', 'no_documents'})
                expected_owner = 'worker' if owner == 'workers' else 'participant'
                self.assertTrue(page.find('a', href=self.person_route(expected_owner)))
                uploads = [a for a in page.find('a') if urlsplit(a.attrs.get('href', '')).path == reverse('document_create')]
                self.assertTrue(any(expected_owner in parse_qs(urlsplit(a.attrs['href']).query) for a in uploads))
                self.assertContains(response, self.worker.phone if owner == 'workers' else self.participant.phone)
                self.assertContains(response, self.worker.email if owner == 'workers' else self.participant.ndis_number)

    def test_directory_filters_sort_and_empty_copy_preserved(self):
        route = reverse('document_list')
        response, page = self.page(route, {'q': 'no-such-fictional-person'})
        for text in ['No people match the current document filters.',
                     'Clear filters to review the full document directory.', 'Clear filters']:
            self.assertContains(response, text)
        self.assertFalse(response.context['person_items'])
        response, _ = self.page(route, {'coverage': 'no_documents'})
        self.assertEqual([item['person'].pk for item in response.context['person_items']], [self.empty.pk])
        response, _ = self.page(route, {'q': self.participant.ndis_number,
            'category': 'compliance', 'review_status': 'pending_review', 'coverage': 'has_documents', 'sort': 'documents'})
        self.assertEqual([item['person'].pk for item in response.context['person_items']], [self.participant.pk])
        self.assertEqual(response.context['summary']['total_documents'], 6)

    def test_person_columns_all_statuses_original_long_names_and_actions(self):
        for owner in ('participant', 'worker'):
            excluded = [Document.objects.create(
                title=f'Excluded {category} {owner}', category=category,
                original_filename=f'excluded_{category}_{owner}.pdf',
                file=f'fictional/excluded_{category}_{owner}.pdf',
                uploaded_by=self.users['admin'], **{owner: getattr(self, owner)})
                for category in ('invoice', 'service_log')]
            response, page = self.page(self.person_route(owner))
            self.assertTrue(all(Document.objects.filter(pk=doc.pk).exists() for doc in excluded))
            self.assertEqual({doc.pk for doc in response.context['documents']},
                             {self.docs[owner, status].pk for status in Document.ReviewStatus.values})
            for doc in excluded:
                self.assertNotContains(response, doc.filename)
            self.assertEqual([th.text for th in page.find('th')],
                ['File', 'Folder', 'Uploaded', 'Status', 'Expiry', 'Uploaded by', 'Actions'])
            self.assertContains(response, 'Files are grouped for CrazyDomains storage while original filenames remain visible for Admin.')
            self.assertContains(response, 'Files shown by original filename while secure storage names stay private.')
            for status in Document.ReviewStatus.values:
                doc = self.docs[owner, status]
                self.assertContains(response, doc.filename)
                self.assertContains(response, doc.get_review_status_display())
                self.assertNotContains(response, doc.file.name)
                self.assertTrue(page.find('a', href=doc.get_absolute_url()))
                self.assertTrue(page.find('a', href=reverse('document_download', args=[doc.pk])))
                self.assertTrue(any(urlsplit(a.attrs.get('href', '')).path == reverse('document_delete', args=[doc.pk])
                                    for a in page.find('a')))
            self.assertNotContains(response, 'Excluded invoice')
            self.assertNotContains(response, 'Excluded service_log')
            response, _ = self.page(self.person_route(owner), {'review_status': 'rejected', 'category': 'compliance', 'q': 'original'})
            self.assertEqual(list(response.context['documents']), [self.docs[owner, 'rejected']])

    def test_person_empty_folder_copy_and_filter_fields(self):
        response, page = self.page(reverse('participant_document_files', args=[self.empty.pk]))
        self.assertContains(response, 'No files in this folder yet.')
        self.assertContains(response, 'Uploaded files for this person and folder will appear here.')
        filters = [f for f in page.find('form') if f.attrs.get('method', 'get').lower() == 'get']
        self.assertEqual(len(filters), 1)
        self.assertTrue(filters[0].find('input', name='q'))
        self.assertTrue(filters[0].find('select', name='review_status'))

    def test_person_actions_heading_group_and_uploaded_by_classes(self):
        for owner in ('participant', 'worker'):
            with self.subTest(owner=owner):
                _, page = self.page(self.person_route(owner))
                heading = page.find('th')[-1]
                self.assertEqual(heading.text, 'Actions')
                self.assertTrue(heading.has_class('actions-heading'))
                rows = page.find('tbody')[0].find('tr')
                self.assertEqual(len(rows), 3)
                for row in rows:
                    cells = row.find('td')
                    self.assertTrue(cells[-1].has_class('actions'))
                    self.assertTrue(cells[-1].has_class('document-actions'))
                    groups = [node for node in cells[-1].find('div')
                              if node.has_class('document-action-group')]
                    self.assertEqual(len(groups), 1)
                    self.assertEqual(len(groups[0].find('a')), 3)
                    self.assertTrue(cells[5].has_class('r1-document-uploaded-by'))
                    self.assertEqual(cells[5].text, str(self.users['admin']))

    def test_person_file_cell_shows_one_original_name_without_status_or_subline(self):
        for owner in ('participant', 'worker'):
            _, page = self.page(self.person_route(owner))
            for status in Document.ReviewStatus.values:
                doc = self.docs[owner, status]
                with self.subTest(owner=owner, status=status):
                    cell = next(cell for cell in page.find('td')
                        if cell.has_class('document-file-cell')
                        and cell.find('a', href=doc.get_absolute_url()))
                    self.assertEqual(cell.text, doc.filename)
                    self.assertEqual(cell.find('small'), [])
                    self.assertEqual(len(cell.find('a')), 1)
                    self.assertEqual(cell.find('a')[0].attrs.get('title'), doc.title)

    def test_review_feedback_has_state_tag_without_changing_success_semantics(self):
        from django.contrib.messages import SUCCESS, get_messages
        doc = self.docs['worker', 'pending_review']
        for status in ('approved', 'rejected'):
            with self.subTest(status=status):
                response = self.client.post(reverse('document_review', args=[doc.pk]),
                    {'review_status': status}, follow=True)
                feedback = list(get_messages(response.wsgi_request))
                self.assertEqual(len(feedback), 1)
                self.assertEqual(feedback[0].level, SUCCESS)
                self.assertEqual(str(feedback[0]), f'Document marked {status}.')
                self.assertIn(f'document-review-{status}', feedback[0].tags.split())
                doc.refresh_from_db()
                self.assertEqual(doc.review_status, status)

    def test_file_name_and_feedback_styles_use_existing_r1_palette(self):
        css = (Path(settings.BASE_DIR) / 'static/css/r1_admin_documents.css').read_text(encoding='utf-8')
        name_rule = re.search(r'\.r1-admin-documents \.document-file-cell a\s*\{([^{}]*)\}', css).group(1)
        for declaration in ('color: var(--r1-text);', 'font-weight: 600;', 'text-decoration: none;'):
            self.assertIn(declaration, name_rule)
        self.assertRegex(css, r'\.r1-admin-documents \.document-manager-table tbody tr:hover\s*\{\s*background: #fbfcfd;\s*\}')
        self.assertRegex(css, r'\.r1-admin-documents \.message\.document-review-rejected\s*\{[^{}]*color: var\(--r1-danger\);[^{}]*background: #faeef0;')

    def test_person_primary_actions_keep_labels_urls_and_preview_hooks(self):
        for owner in ('participant', 'worker'):
            _, page = self.page(self.person_route(owner))
            for status in Document.ReviewStatus.values:
                doc = self.docs[owner, status]
                with self.subTest(owner=owner, status=status):
                    download = page.find('a', href=reverse('document_download', args=[doc.pk]))[0]
                    group = download.parent
                    self.assertTrue(group.has_class('document-action-group'))
                    primary = group.find('a')[0]
                    self.assertEqual(primary.text, 'Preview' if doc.is_previewable else 'View')
                    self.assertEqual(primary.attrs['href'],
                        reverse('document_preview', args=[doc.pk]) if doc.is_previewable
                        else doc.get_absolute_url())
                    self.assertTrue(primary.has_class('button'))
                    self.assertTrue(primary.has_class('secondary'))
                    self.assertFalse(primary.has_class('r1-document-icon-action'))
                    if doc.is_previewable:
                        self.assertIn('data-document-preview-open', primary.attrs)
                        self.assertEqual(primary.attrs['data-preview-title'], doc.title)
                        self.assertEqual(primary.attrs['data-preview-filename'], doc.filename)
                        self.assertEqual(primary.attrs['data-preview-download-url'],
                                         reverse('document_download', args=[doc.pk]))

    def assert_decorative_action_icon(self, link, action):
        icons = link.find('img') + link.find('svg') + [
            span for span in link.find('span') if span.has_class('r1-document-action-icon')]
        self.assertEqual(len(icons), 1)
        icon = icons[0]
        self.assertEqual(icon.attrs.get('aria-hidden'), 'true')
        if icon.tag == 'img':
            self.assertEqual(icon.attrs.get('alt'), '')
            self.assertTrue(icon.attrs.get('src'))
        elif icon.tag == 'svg':
            self.assertEqual(icon.attrs.get('focusable'), 'false')
        else:
            self.assertIn(action, ('download', 'delete'))
            self.assertTrue(icon.has_class(f'r1-document-icon-{action}'))
            self.assertEqual(icon.children, [])
            stylesheet = Path(settings.BASE_DIR) / 'static/css/r1_admin_documents.css'
            css = stylesheet.read_text(encoding='utf-8')
            self.assertRegex(css,
                r'\.r1-admin-documents\s+\.r1-document-action-icon\s*\{[^{}]*'
                r'\bmask:\s*var\(--r1-document-icon\)[^{}]*\}')
            for declaration in ('width: 16px;', 'height: 16px;', 'background-color: currentColor;'):
                self.assertRegex(css,
                    r'\.r1-admin-documents\s+\.r1-document-action-icon\s*\{[^{}]*'
                    + re.escape(declaration) + r'[^{}]*\}')
            relative_asset = f'../img/r1/icons/document-{action}.svg'
            self.assertRegex(css,
                r'\.r1-admin-documents\s+\.r1-document-icon-' + action
                + r'\s*\{\s*--r1-document-icon:\s*url\([\'"]?'
                + re.escape(relative_asset) + r'[\'"]?\);\s*\}')
            asset = (stylesheet.parent / relative_asset).resolve()
            self.assertTrue(asset.is_file(), f'Expected vendored {action} SVG')
            svg = ElementTree.parse(asset).getroot()
            self.assertEqual(svg.tag, '{http://www.w3.org/2000/svg}svg')
            self.assertEqual(svg.attrib.get('viewBox'), '0 0 24 24')
            paths = svg.findall('.//{http://www.w3.org/2000/svg}path')
            self.assertTrue(paths, 'Expected nonempty Lucide SVG geometry')
            self.assertTrue(all(path.attrib.get('d', '').strip() for path in paths))

    def test_person_download_delete_are_accessible_icon_only_links(self):
        for owner in ('participant', 'worker'):
            response, page = self.page(self.person_route(owner))
            for status in Document.ReviewStatus.values:
                doc = self.docs[owner, status]
                for action, style, label in [('download', 'secondary', 'Download file'),
                                             ('delete', 'danger-outline', 'Delete file')]:
                    with self.subTest(owner=owner, status=status, action=action):
                        route = reverse(f'document_{action}', args=[doc.pk])
                        links = [link for link in page.find('a')
                                 if urlsplit(link.attrs.get('href', '')).path == route]
                        self.assertEqual(len(links), 1)
                        link = links[0]
                        self.assertEqual(parse_qs(urlsplit(link.attrs['href']).query),
                            {'next': [response.context['current_list_url']]} if action == 'delete' else {})
                        self.assertTrue(link.has_class('button'))
                        self.assertTrue(link.has_class(style))
                        self.assertTrue(link.has_class('r1-document-icon-action'))
                        self.assertEqual(link.attrs.get('aria-label'), label)
                        self.assertEqual(link.attrs.get('title'), label)
                        self.assertEqual(link.text, '')
                        self.assert_decorative_action_icon(link, action)

    def test_preview_only_pdf_and_images_on_lists_and_detail(self):
        for owner in ('participant', 'worker'):
            _, listing = self.page(self.person_route(owner))
            for status in Document.ReviewStatus.values:
                doc = self.docs[owner, status]
                _, detail = self.page(doc.get_absolute_url())
                for page in (listing, detail):
                    links = page.find('a', href=reverse('document_preview', args=[doc.pk]))
                    self.assertEqual(len(links), int(doc.is_previewable))
                    if links:
                        self.assertIn('data-document-preview-open', links[0].attrs)
                        self.assertEqual(links[0].attrs['data-preview-filename'], doc.filename)
                        self.assertEqual(links[0].attrs['data-preview-download-url'], reverse('document_download', args=[doc.pk]))
                preview = self.client.get(reverse('document_preview', args=[doc.pk]))
                self.assertEqual(preview.status_code, 200 if doc.is_previewable else 404)
                if doc.is_previewable:
                    self.assertEqual(preview['Content-Type'], doc.preview_content_type)
                    self.assertEqual(preview['X-Frame-Options'], 'SAMEORIGIN')
                    self.assertIn('inline;', preview['Content-Disposition'])

    def test_detail_metadata_dl_preserves_every_field(self):
        for owner in ('participant', 'worker'):
            doc = self.docs[owner, 'pending_review']
            response, page = self.page(doc.get_absolute_url())
            metadata = [dl for dl in page.find('dl') if dl.has_class('r1-document-metadata')]
            self.assertEqual(len(metadata), 2, 'Expected file and linked-record metadata lists')
            self.assertEqual([dt.text for dl in metadata for dt in dl.find('dt')],
                ['File', 'Status', 'Folder', 'Required type', 'Issue date', 'Expiry date',
                 'Participant', 'Worker', 'Uploaded by'])
            values = [dd.text for dl in metadata for dd in dl.find('dd')]
            self.assertEqual(len(values), 9)
            metadata_text = ' '.join(dl.text for dl in metadata)
            for value in [doc.filename, 'Pending review', 'Police Check', '02/01/2026',
                          doc.expiry_date.strftime('%d/%m/%Y'), str(getattr(doc, owner)),
                          str(doc.uploaded_by)]:
                self.assertIn(value, metadata_text)
            self.assertIn('Compliance' if owner == 'worker' else 'NDIS Forms', metadata_text)
            notes = [node for node in page.find('p') if node.has_class('r1-document-notes')]
            self.assertEqual(len(notes), 1)
            self.assertEqual(''.join(notes[0].children), doc.notes)
            self.assertContains(response, 'Back to files')

    def test_blank_metadata_and_storage_basename_fallback_are_retained(self):
        for owner in ('participant', 'worker', None):
            with self.subTest(owner=owner):
                doc = Document.objects.create(title=f'Fictional blank metadata {owner}',
                    category='general', review_status='approved',
                    required_document_type='', issue_date=None, expiry_date=None,
                    notes='', original_filename='', file='fictional/blank-fallback.pdf',
                    uploaded_by=self.users['admin'],
                    **({owner: getattr(self, owner)} if owner else {}))
                _, page = self.page(doc.get_absolute_url())
                metadata = [dl for dl in page.find('dl') if dl.has_class('r1-document-metadata')]
                self.assertEqual(len(metadata), 2)
                labels = [dt.text for dl in metadata for dt in dl.find('dt')]
                values = [dd.text for dl in metadata for dd in dl.find('dd')]
                self.assertEqual(len(labels), len(values))
                self.assertEqual(dict(zip(labels, values)), {
                    'File': 'blank-fallback.pdf', 'Status': 'Approved', 'Folder': 'Others',
                    'Required type': 'Not provided', 'Issue date': '-', 'Expiry date': '-',
                    'Participant': str(self.participant) if owner == 'participant' else '-',
                    'Worker': str(self.worker) if owner == 'worker' else '-',
                    'Uploaded by': str(self.users['admin']),
                })
                notes = [node for node in page.find('p') if node.has_class('r1-document-notes')]
                self.assertEqual(len(notes), 1)
                self.assertEqual(notes[0].text, '-')
                if owner:
                    response, listing = self.page(self.person_route(owner))
                    self.assertContains(response, 'blank-fallback.pdf')
                    link = listing.find('a', href=doc.get_absolute_url())[0]
                    row = link.parent
                    while row.tag != 'tr':
                        row = row.parent
                    self.assertEqual(row.find('td')[4].text, 'Not provided')

    def test_detail_record_has_three_labelled_sections_and_separate_notes(self):
        for owner in ('participant', 'worker'):
            doc = self.docs[owner, 'pending_review']
            notes = 'Fictional notes: <retain> & preserve.\nSecond line,  two spaces.'
            Document.objects.filter(pk=doc.pk).update(notes=notes)
            with self.subTest(owner=owner):
                _, page = self.page(doc.get_absolute_url())
                records = [node for node in page.find('section')
                           if node.has_class('r1-document-record')]
                self.assertEqual(len(records), 1)
                sections = [node for node in records[0].children
                            if isinstance(node, Element) and node.tag == 'section']
                self.assertEqual(len(sections), 3)
                expected = [
                    ('r1-file-information', 'File information',
                     ['File', 'Status', 'Folder', 'Required type', 'Issue date', 'Expiry date']),
                    ('r1-linked-records', 'Linked records', ['Participant', 'Worker', 'Uploaded by']),
                    ('r1-file-notes', 'Notes', []),
                ]
                for section, (heading_id, title, labels) in zip(sections, expected):
                    self.assertEqual(section.attrs.get('aria-labelledby'), heading_id)
                    headings = section.find('h2')
                    self.assertEqual(len(headings), 1)
                    self.assertEqual(headings[0].attrs.get('id'), heading_id)
                    self.assertEqual(headings[0].text, title)
                    lists = section.find('dl')
                    self.assertEqual(len(lists), int(bool(labels)))
                    if labels:
                        self.assertTrue(lists[0].has_class('r1-document-metadata'))
                        self.assertEqual([dt.text for dt in lists[0].find('dt')], labels)
                        self.assertEqual(len(lists[0].find('dd')), len(labels))
                paragraphs = sections[2].find('p')
                self.assertEqual(len(paragraphs), 1)
                self.assertTrue(paragraphs[0].has_class('r1-document-notes'))
                self.assertEqual(''.join(paragraphs[0].children), notes)

    def test_detail_header_status_repeats_metadata_status(self):
        for owner in ('participant', 'worker'):
            for status in Document.ReviewStatus.values:
                doc = self.docs[owner, status]
                with self.subTest(owner=owner, status=status):
                    _, page = self.page(doc.get_absolute_url())
                    headers = [node for node in page.find('div')
                               if node.has_class('r1-document-detail-header')]
                    self.assertEqual(len(headers), 1)
                    pills = [node for node in headers[0].find('span')
                             if node.has_class('r1-document-header-status')]
                    self.assertEqual(len(pills), 1)
                    self.assertTrue(pills[0].has_class('status-pill'))
                    self.assertTrue(pills[0].has_class(f'status-{status}'))
                    self.assertEqual(pills[0].text, doc.get_review_status_display())
                    metadata = [dl for dl in page.find('dl') if dl.has_class('r1-document-metadata')]
                    status_values = [dd for dl in metadata for dt, dd in
                                     zip(dl.find('dt'), dl.find('dd')) if dt.text == 'Status']
                    self.assertEqual(len(status_values), 1)
                    self.assertEqual(status_values[0].text, doc.get_review_status_display())

    def test_detail_top_actions_keep_text_order_urls_and_preview_hooks(self):
        for owner in ('participant', 'worker'):
            for status in Document.ReviewStatus.values:
                doc = self.docs[owner, status]
                with self.subTest(owner=owner, status=status):
                    response, page = self.page(doc.get_absolute_url())
                    groups = [node for node in page.find('div')
                              if node.has_class('document-detail-actions')]
                    self.assertEqual(len(groups), 1)
                    back = response.context['document_owner_url']
                    expected = [('Back to files', back, {})]
                    if doc.is_previewable:
                        expected.append(('Preview', reverse('document_preview', args=[doc.pk]), {}))
                    expected.extend([
                        ('Download', reverse('document_download', args=[doc.pk]), {}),
                        ('Edit', reverse('document_edit', args=[doc.pk]), {'next': [back]}),
                        ('Delete', reverse('document_delete', args=[doc.pk]), {'next': [back]}),
                    ])
                    links = groups[0].find('a')
                    self.assertEqual([(link.text, urlsplit(link.attrs['href']).path,
                                       parse_qs(urlsplit(link.attrs['href']).query))
                                      for link in links], expected)
                    for link in links:
                        self.assertTrue(link.has_class('button'))
                        self.assertTrue(link.has_class('danger-outline' if link.text == 'Delete' else 'secondary'))
                        self.assertFalse(link.has_class('r1-document-icon-action'))
                    if doc.is_previewable:
                        preview = links[1]
                        self.assertIn('data-document-preview-open', preview.attrs)
                        self.assertEqual(preview.attrs['data-preview-title'], doc.title)
                        self.assertEqual(preview.attrs['data-preview-filename'], doc.filename)
                        self.assertEqual(preview.attrs['data-preview-download-url'],
                                         reverse('document_download', args=[doc.pk]))

    def review_forms(self, page, doc):
        return [form for form in page.find('form') if form.attrs.get('action') == reverse('document_review', args=[doc.pk])]

    def test_pending_review_separate_approve_post_and_optional_reject_note(self):
        doc = self.docs['worker', 'pending_review']
        _, page = self.page(doc.get_absolute_url())
        sections = [node for node in page.find('section') if node.has_class('r1-document-review')]
        forms = self.review_forms(page, doc)
        self.assertEqual(len(forms), 2)
        indexed = {form.find('input', name='review_status')[0].attrs['value']: form for form in forms}
        self.assertEqual(set(indexed), {'approved', 'rejected'})
        for form in forms:
            self.assertEqual(form.attrs.get('method', '').lower(), 'post')
            self.assertTrue(form.find('input', name='csrfmiddlewaretoken'))
        self.assertFalse(indexed['approved'].find(name='review_note'))
        notes = indexed['rejected'].find(name='review_note')
        self.assertEqual(len(notes), 1)
        self.assertIn(notes[0].tag, ('input', 'textarea'))
        self.assertNotIn('required', notes[0].attrs)
        self.assertIn('Approve', indexed['approved'].text)
        self.assertIn('Reject', indexed['rejected'].text)
        self.assertEqual(len(sections), 1, 'Expected scoped r1-document-review section')
        self.assertEqual(len(self.review_forms(sections[0], doc)), 2)

    def test_review_post_contract_approve_without_note_reject_blank_or_note(self):
        doc = self.docs['worker', 'pending_review']
        route = reverse('document_review', args=[doc.pk])
        self.assertEqual(self.client.get(route).status_code, 405)
        for payload, expected in [({'review_status': 'approved'}, doc.notes),
                                  ({'review_status': 'rejected', 'review_note': ''}, doc.notes),
                                  ({'review_status': 'rejected', 'review_note': ' Fictional reason '},
                                   doc.notes + '\n\nReview note: Fictional reason')]:
            with self.subTest(payload=payload):
                Document.objects.filter(pk=doc.pk).update(review_status='pending_review', notes=doc.notes)
                response = self.client.post(route, payload)
                self.assertRedirects(response, doc.get_absolute_url())
                actual = Document.objects.get(pk=doc.pk)
                self.assertEqual(actual.review_status, payload['review_status'])
                self.assertEqual(actual.notes, expected)
        self.assertEqual(AuditLog.objects.filter(action=AuditLog.Action.DOCUMENT_APPROVED).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action=AuditLog.Action.DOCUMENT_REJECTED).count(), 2)

    def test_no_review_section_or_post_forms_after_review(self):
        for status in ('approved', 'rejected'):
            doc = self.docs['worker', status]
            _, page = self.page(doc.get_absolute_url())
            self.assertFalse(any(node.has_class('r1-document-review') for node in page.find()))
            self.assertFalse(self.review_forms(page, doc))

    def test_upload_dialog_preserves_fields_hooks_and_is_outside_r1_ancestors(self):
        for owner in ('worker', 'participant'):
            response, page = self.page(self.person_route(owner))
            dialogs = page.find('dialog', id='document-upload-dialog')
            self.assertEqual(len(dialogs), 1)
            dialog = dialogs[0]
            self.assertIn('document-upload-dialog', dialog.attrs['class'])
            ancestor = dialog.parent
            while ancestor:
                classes = ancestor.attrs.get('class', '').split()
                self.assertFalse(any(c == 'r1-ui' or c.startswith('r1-admin-') for c in classes),
                                 'Out-of-scope upload dialog must be outside R1 shell')
                ancestor = ancestor.parent
            form = dialog.find('form')[0]
            self.assertEqual(form.attrs.get('action'), reverse('document_create'))
            self.assertEqual(form.attrs.get('method'), 'post')
            self.assertEqual(form.attrs.get('enctype'), 'multipart/form-data')
            fields = {node.attrs['name']: node for node in form.find() if node.attrs.get('name')}
            self.assertEqual(set(fields), {'csrfmiddlewaretoken', 'next', 'required_document_type',
                                         owner, 'title', 'category', 'file', 'notes'})
            self.assertEqual(fields[owner].attrs['value'], str(getattr(self, owner).pk))
            self.assertEqual(fields['next'].attrs['value'], self.person_route(owner))
            for field in ('title', 'category', 'file'):
                self.assertIn('required', fields[field].attrs)
            close_buttons = dialog.find('button', **{'data-document-upload-close': None})
            open_links = page.find('a', **{'data-document-upload-open': None})
            self.assertEqual(len(close_buttons), 2)
            self.assertEqual(len(open_links), 1)
            self.assertIn('data-document-upload-close', close_buttons[0].attrs)
            self.assertEqual(close_buttons[0].attrs['type'], 'button')
            self.assertEqual(close_buttons[0].attrs['aria-label'], 'Close upload dialog')
            self.assertIn('data-document-upload-open', open_links[0].attrs)
            self.assertEqual(open_links[0].attrs['href'], response.context['upload_url'])
            self.assertIn('data-upload-category', open_links[0].attrs)
            self.assertEqual(open_links[0].attrs['data-upload-category'], response.context['upload_category_value'])
            for field, hook in [('title', 'data-document-upload-title'),
                                ('category', 'data-document-upload-category'),
                                ('next', 'data-document-upload-next'),
                                ('required_document_type', 'data-document-upload-required-type')]:
                self.assertIn(hook, fields[field].attrs)

    def test_excluded_upload_edit_delete_and_sw_pages_have_no_documents_r1_scope(self):
        doc = self.docs['worker', 'pending_review']
        routes = [reverse('document_create'), reverse('document_create') + f'?worker={self.worker.pk}',
                  reverse('document_edit', args=[doc.pk]), reverse('document_delete', args=[doc.pk])]
        for role, pages in [('admin', routes), ('support_worker', [reverse('worker_document_list'),
            reverse('worker_document_upload'), reverse('worker_document_detail', args=[doc.pk])])]:
            self.client.force_login(self.users[role])
            for route in pages:
                response, page = self.page(route)
                self.assertFalse(any(node.has_class('r1-admin-documents') for node in page.find()))
                self.assertNotContains(response, 'css/r1_admin_documents.css')

    def test_scoped_stylesheet_exists_without_global_document_upload_rules(self):
        stylesheet = Path(settings.BASE_DIR) / 'static/css/r1_admin_documents.css'
        self.assertTrue(stylesheet.is_file(), 'Expected new scoped documents sheet')
        css = stylesheet.read_text(encoding='utf-8')
        self.assertIn('.r1-admin-documents', css)
        self.assertNotIn('.document-upload-dialog', css,
                         'Out-of-scope upload dialog must retain existing presentation')
