"""Approved detail-only layout contracts; business behavior remains covered by existing tests."""
from datetime import date, time
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.templatetags.static import static
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from core.models import AuditLog
from documents.tests_r1_ui import Page
from invoices.models import Invoice, InvoiceLine
from scheduling.models import SupportItem
from .models import CoordinationLog, CoordinationLogChange
from .tests import create_coordinator, create_participant


class AdminCoordinationDetailV03Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username='detail-v03-admin')
        UserProfile.objects.create(user=cls.admin, role='admin')
        cls.sc = create_coordinator('detail-v03-sc')
        cls.person = create_participant()
        cls.log = CoordinationLog.objects.create(participant=cls.person, coordinator=cls.sc,
            service_date=date(2026, 10, 12), actual_hours=Decimal('1.25'),
            case_notes='Complete case notes.\nSecond line <script>unsafe</script>', status='submitted')

    def setUp(self):
        self.client.force_login(self.admin)
        self.detail = reverse('coordination_log_detail', args=[self.log.pk])

    def pick(self, root, cls):
        nodes = [node for node in root.find() if node.has_class(cls)]
        self.assertEqual(len(nodes), 1, 'Expected one '+cls)
        return nodes[0]

    def invoice(self):
        item = SupportItem.objects.create(item_number='DETAIL-V03', name='Fictional item', unit='H', price_limit=Decimal('100'))
        invoice = Invoice.objects.create(participant=self.person, period_start=self.log.service_date,
            period_end=self.log.service_date, created_by=self.admin, invoice_type='support_coordination')
        InvoiceLine.objects.create_from_coordination_log(invoice, self.log, item)
        return invoice

    def test_new_detail_assets_and_scope_do_not_leak_to_other_routes(self):
        response = self.client.get(self.detail)
        for path in ['css/r1_admin_log_detail.css','css/r1_admin_coordination_detail.css']:
            self.assertContains(response, static(path), count=1)
        self.assertContains(response, 'r1-admin-log-detail')
        self.invoice()
        for url in [reverse('coordination_log_list'), reverse('coordination_log_correction', args=[self.log.pk]),
                    '/service-logs/', '/documents/', '/invoices/']:
            self.assertNotContains(self.client.get(url), 'r1_admin_coordination_detail.css')

    def test_main_facts_and_notes_use_record_with_separate_review_rail(self):
        root = Page(self.client.get(self.detail)).root
        layout = self.pick(root,'r1-log-layout')
        record, rail = self.pick(layout,'r1-log-record'), self.pick(layout,'r1-log-rail')
        for label in ['Coordinator','Service date','Service duration','Coordination type','Case notes']:
            self.assertIn(label,[node.text for node in record.find('dt')])
        self.assertEqual([node.text for node in rail.find('dt')],['Status','Submitted'])
        self.assertFalse([node for node in record.find() if node.has_class('card')])
        self.assertEqual([node.text for node in self.pick(record,'r1-log-facts').find('dt')], ['Service duration','Coordination type'])

    def test_submitted_by_uses_existing_coordinator_and_is_escaped_for_all_statuses(self):
        self.sc.first_name = '<SC>'
        self.sc.save()
        for status in ['submitted','approved','rejected','invoiced']:
            self.log.status = status
            self.log.save()
            response = self.client.get(self.detail)
            panel = self.pick(Page(response).root,'r1-log-status')
            caption = self.pick(panel,'r1-log-caption')
            self.assertEqual(caption.text,'Submitted by '+self.sc.display_name)
            self.assertContains(response, 'Submitted by &lt;SC&gt;')
            self.assertNotContains(response, 'Submitted by <SC>')
            self.assertNotEqual(caption.text, 'Submitted by '+self.admin.username)

    def test_review_forms_keep_post_csrf_revision_token_and_required_reason(self):
        response = self.client.get(self.detail)
        panel = self.pick(Page(response).root,'r1-log-status')
        for name in ['coordination_log_approve','coordination_log_reject']:
            forms = panel.find('form',action=reverse(name,args=[self.log.pk]))
            self.assertEqual(len(forms),1)
            self.assertEqual(forms[0].attrs['method'],'post')
            self.assertTrue(forms[0].find('input',name='csrfmiddlewaretoken'))
            self.assertEqual(forms[0].find('input',name='revision_token')[0].attrs['value'],response.context['revision_token'])
        self.assertIn('required',panel.find('input',name='rejection_reason')[0].attrs)

    def test_review_conditions_and_correction_entry_remain_original(self):
        for status in ['approved','rejected','invoiced']:
            self.log.status = status
            self.log.save()
            panel = self.pick(Page(self.client.get(self.detail)).root,'r1-log-status')
            self.assertFalse(panel.find('input',name='rejection_reason'))
            self.assertFalse(panel.find('button'))
        self.log.status = 'submitted'
        self.log.save()
        self.invoice()
        response = self.client.get(self.detail)
        self.assertNotContains(response,'name="rejection_reason"')
        self.assertContains(response,reverse('coordination_log_correction',args=[self.log.pk]))

    def test_legacy_notes_rejection_reason_and_review_activity_are_retained(self):
        self.log.start_time,self.log.end_time,self.log.break_minutes = time(9),time(10,30),15
        self.log.coordinator_notes = 'Complete legacy coordinator notes.\nAnother line.'
        self.log.rejection_reason = 'Full rejection reason.\nRetained explanation.'
        self.log.reviewed_by,self.log.reviewed_at = self.admin,timezone.now()
        self.log.save()
        response = self.client.get(self.detail)
        root = Page(response).root
        record,rail = self.pick(root,'r1-log-record'),self.pick(root,'r1-log-rail')
        for value in ['Previously recorded time','Recorded break','15 minutes','Complete legacy coordinator notes.']:
            self.assertIn(value,record.text)
        self.assertIn('Full rejection reason.',rail.text)
        self.assertEqual([node.text for node in self.pick(rail,'r1-log-activity-list').find('dt')],['Submitted','Reviewed by','Reviewed at'])
        self.assertContains(response,'Second line &lt;script&gt;unsafe&lt;/script&gt;')

    def test_full_history_remains_in_main_record_with_original_script(self):
        before = 'Original complete history. '*100
        CoordinationLogChange.objects.create(log=self.log,actor=self.admin,kind='billing_review',reason='Full reason',details='Full explanation',
            before={'case_notes':before,'status':'approved'},after={'case_notes':self.log.case_notes,'status':'submitted'})
        response = self.client.get(self.detail)
        record = self.pick(Page(response).root,'r1-log-record')
        history = self.pick(record,'sc-log-history')
        for value in ['Change history','Before','After','Review details','Show full text','Full explanation','Invoice review required.']:
            self.assertIn(value,history.text)
        self.assertContains(response,before)
        self.assertContains(response,static('js/sc_log_history.js'),count=1)

    def test_get_keeps_original_safe_return_and_does_not_write_records(self):
        counts = (AuditLog.objects.count(),CoordinationLogChange.objects.count(),list(CoordinationLog.objects.values()))
        response = self.client.get(self.detail+'?next=%2Fcoordination-logs%2F%3Fstatus%3Dsubmitted')
        self.assertContains(response,'href="/coordination-logs/?status=submitted"')
        self.assertEqual(counts,(AuditLog.objects.count(),CoordinationLogChange.objects.count(),list(CoordinationLog.objects.values())))


class AdminCoordinationDetailV03StyleTests(SimpleTestCase):
    def test_detail_css_scoping_breakpoints_and_original_visual_tokens(self):
        path = Path(settings.BASE_DIR)/'static/css/r1_admin_coordination_detail.css'
        self.assertTrue(path.is_file(),'Detail-only CSS has not been implemented')
        css = path.read_text()
        for value in ['.r1-admin-log-detail','280px','240px','max-width:1000px','max-width:760px','max-width:350px',
                      'var(--r1-border)','var(--r1-muted)','var(--r1-warning-soft)','grid-template-columns:minmax(0,1fr)']:
            self.assertIn(value,css)
        self.assertNotIn(':root',css)
        self.assertNotIn('font-size:32px',css)
        self.assertNotIn('width:1440px',css)
