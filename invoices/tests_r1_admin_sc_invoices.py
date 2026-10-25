"""B08.2 presentation contracts; business rules stay covered by the invoice suites."""
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.templatetags.static import static
from django.urls import reverse

from accounts.models import UserProfile
from coordinators.models import CoordinationLog, SupportCoordinator
from invoices.models import Invoice, InvoiceLine
from invoices.tests_r1_admin_invoice_detail import DetailMarkup
from participants.models import Participant
from scheduling.models import SupportItem


class R1AdminSCInvoiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for role in ['admin', 'super_admin', 'accountant', 'support_worker', 'support_coordinator']:
            user = get_user_model().objects.create_user(username='b082_'+role)
            UserProfile.objects.create(user=user, role=role)
            cls.users[role] = user
        cls.coordinator = SupportCoordinator.objects.create(user=cls.users['support_coordinator'], first_name='Jordan', last_name='Ellis')
        cls.people = [Participant.objects.create(first_name=name, last_name='Fictional') for name in ['Mia', 'Ethan']]
        cls.item = SupportItem.objects.create(item_number='QA-B082', name='Fictional SC support', unit=SupportItem.Unit.HOUR, price_limit=Decimal('100'))
        cls.logs = [CoordinationLog.objects.create(participant=person, coordinator=cls.coordinator,
            service_date=date(2026, 10, 5), actual_hours=Decimal('1.25'), status='approved', case_notes='Fictional complete case notes.') for person in cls.people]
        cls.records = {}
        for status in Invoice.Status.values:
            invoice = Invoice.objects.create(participant=cls.people[0], created_by=cls.users['admin'],
                period_start=date(2026,10,1), period_end=date(2026,10,12), invoice_type='support_coordination', status=status)
            source = CoordinationLog.objects.create(participant=cls.people[0], coordinator=cls.coordinator,
                service_date=date(2026,10,6), actual_hours=Decimal('1.25'), status='invoiced')
            InvoiceLine.objects.create(invoice=invoice, coordination_log=source, line_type='support_coordination', support_item_number='SAVED-SC', description='Saved snapshot, not recalculated',
                unit='H', quantity=Decimal('1.50'), unit_price=Decimal('80'), line_total=Decimal('120'))
            cls.records[status] = invoice

    def get_page(self, name, data=None, role='admin', args=None):
        self.client.force_login(self.users[role])
        return self.client.get(reverse(name, args=args), data or {})

    def test_admin_and_superadmin_sc_list_opt_in_and_preserve_sc_scope(self):
        for role in ['admin','super_admin']:
            response = self.get_page('support_coordination_invoice_list', {'status':'draft'}, role)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'r1-admin-sc-invoices')
            self.assertContains(response, static('css/r1_admin_sc_invoices.css'), count=1)
            self.assertContains(response, 'Coordination / SC Invoices')
            self.assertContains(response, 'Showing draft invoices.')
            self.assertContains(response, self.records['draft'].invoice_number)
            self.assertNotContains(response, self.records['paid'].invoice_number)

    def test_create_reuses_r1_dates_without_renaming_or_relaxing_fields(self):
        response = self.get_page('support_coordination_invoice_create')
        self.assertContains(response, 'r1-admin-sc-preview')
        self.assertContains(response, static('css/r1_admin_sc_invoices.css'), count=1)
        self.assertContains(response, 'data-invoice-filters')
        markup = DetailMarkup(response.content.decode())
        for name in ['period_start','period_end']:
            fields = markup.find('input', type='date', name=name)
            self.assertEqual(len(fields), 1)
            self.assertIn('required', fields[0])
        for name in ['participant','support_item']:
            self.assertEqual(len(markup.find('select', name=name)), 1)
        self.assertContains(response, static('js/r1_admin_invoice_create.js'), count=1)

    def test_required_errors_follow_fields_and_keep_original_messages(self):
        response = self.get_page('support_coordination_invoice_create', {'participant':'','period_start':'','period_end':'','support_item':''})
        self.assertEqual(response.status_code,200)
        html = response.content.decode()
        for name in ['participant','support_item','period_start','period_end']:
            self.assertLess(html.index('name="'+name+'"'), html.index('id="id_'+name+'_error"'))
        self.assertContains(response, 'This field is required.', count=4)

    def test_date_error_and_stale_selection_keep_existing_errors(self):
        response = self.get_page('support_coordination_invoice_create', {'participant':self.people[0].pk,
            'support_item':self.item.pk, 'period_start':'2026-10-12','period_end':'2026-10-01'})
        self.assertTrue(response.context['form'].errors)
        self.assertContains(response, 'r1-admin-sc-preview')
        stale = self.get_page('support_coordination_invoice_create', {'coordination_log_ids':'999999'})
        self.assertContains(stale, 'Selected coordination logs are no longer available for invoicing.')

    def test_multi_participant_groups_retain_post_targets_and_selected_ids(self):
        response = self.get_page('support_coordination_invoice_create', {'coordination_log_ids':[log.pk for log in self.logs]})
        self.assertContains(response, 'class="invoice-selected-group"', count=2)
        self.assertContains(response, 'sc-source-table', count=2)
        markup = DetailMarkup(response.content.decode())
        forms = [(attrs, nodes) for attrs, nodes in markup.forms if attrs.get('method')=='post' and not attrs.get('action')]
        self.assertEqual(len(forms),2)
        by_person = {next(a['value'] for tag,a in nodes if a.get('name')=='participant'):nodes for attrs,nodes in forms}
        for log in self.logs:
            nodes = by_person[str(log.participant_id)]
            self.assertIn(('input', {'type':'hidden','name':'coordination_log_ids','value':str(log.pk)}), nodes)
        for title in ['Date','Coordinator','Coordination type','Hours','Notes']:
            self.assertContains(response, 'data-label="'+title+'"', count=2)

    def test_detail_status_rules_snapshot_and_download_targets_preserved(self):
        for role in ['admin','super_admin']:
            for status, invoice in self.records.items():
                response = self.get_page('invoice_detail', role=role, args=[invoice.pk])
                self.assertTemplateUsed(response, 'invoices/partials/r1_invoice_detail.html')
                self.assertContains(response, 'Coordination / SC Invoices / '+invoice.invoice_number)
                self.assertContains(response, 'Saved snapshot, not recalculated')
                self.assertContains(response, '$120.00')
                self.assertContains(response, reverse('invoice_csv',args=[invoice.pk]))
                self.assertContains(response, reverse('invoice_pdf',args=[invoice.pk]))
                for action, present in [('invoice_mark_issued',status=='draft'),('invoice_mark_paid',status=='issued'),
                    ('invoice_cancel',status in ['draft','issued']),('invoice_delete',status=='draft')]:
                    target = reverse(action,args=[invoice.pk])
                    if present:self.assertContains(response, 'action="'+target+'"')
                    else:self.assertNotContains(response, 'action="'+target+'"')

    def test_other_roles_cannot_access_sc_finance_pages(self):
        for role in ['accountant','support_worker','support_coordinator']:
            for route, args in [('support_coordination_invoice_list',None),('support_coordination_invoice_create',None),
                ('invoice_detail',[self.records['draft'].pk])]:
                self.assertEqual(self.get_page(route,role=role,args=args).status_code,403)

    def test_css_explicitly_scopes_v02_notice_and_alignment(self):
        css = (Path(settings.BASE_DIR)/'static/css/r1_admin_sc_invoices.css').read_text(encoding='utf-8')
        for value in ['.r1-admin-sc-invoices','grid-template-rows:20px 40px auto','grid-template-rows:20px 44px auto',
            'border-radius:6px','font-size:14px','background:var(--r1-blue-soft)']:
            self.assertIn(value,css)

    def test_mobile_source_cells_release_inherited_fixed_height(self):
        css = (Path(settings.BASE_DIR)/'static/css/r1_admin_sc_invoices.css').read_text(encoding='utf-8')
        mobile = css.split('@media(max-width:760px)',1)[1]
        rule = mobile.split('.sc-source-table td {',1)[1].split('}',1)[0]
        self.assertIn('height:auto',rule)

    def test_invalid_select_border_overrides_the_sc_control_border(self):
        css = (Path(settings.BASE_DIR)/'static/css/r1_admin_sc_invoices.css').read_text(encoding='utf-8')
        self.assertIn('.app-shell.r1-admin-sc-invoices.r1-admin-sc-preview :is(label,.invoice-filter-date):has(.errorlist)',css)
