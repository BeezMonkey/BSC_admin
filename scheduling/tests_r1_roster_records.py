from datetime import date, time
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from participants.models import Participant
from scheduling.forms import RecurringShiftForm
from scheduling.models import Shift, SupportItem
from scheduling.tests_r1_roster import ControlParser
from workers.models import SupportWorker


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class R1RosterRecordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username='record-ui-admin')
        UserProfile.objects.create(user=cls.admin, role='admin')
        cls.person = Participant.objects.create(first_name='Fictional', last_name='Participant')
        worker_user=get_user_model().objects.create_user(username='record-ui-worker')
        UserProfile.objects.create(user=worker_user,role=UserProfile.Role.SUPPORT_WORKER)
        cls.worker = SupportWorker.objects.create(first_name='Fictional', last_name='Worker',user=worker_user)
        cls.item = SupportItem.objects.create(item_number='R1-RECORD-UI', name='Fictional support', price_limit=Decimal('100'))
        cls.shift = Shift.objects.create(participant=cls.person, worker=cls.worker,
            service_date=date(2027, 1, 4), start_time=time(9), end_time=time(12),
            planned_hours=Decimal('3'), support_item=cls.item, service_type='community_access',
            status='draft', created_by=cls.admin)

    def setUp(self):
        self.client.force_login(self.admin)

    def get(self, name, shift=False, **params):
        return self.client.get(reverse(name, args=[self.shift.pk] if shift else []), params)

    def recurring_data(self):
        return {'participant':self.person.pk, 'worker':self.worker.pk, 'support_item':self.item.pk,
            'service_type':'community_access', 'frequency':'weekly', 'start_date':'2027-02-01',
            'end_date':'2027-02-08', 'start_time':'09:17', 'end_time':'12:31', 'break_minutes':'0'}

    def test_standalone_pages_opt_in_with_focus_last_and_original_menu(self):
        for name, shift in (('shift_detail',True),('shift_create',False),('shift_edit',True),
                            ('recurring_shift_create',False),('planner_billing_detail',True)):
            with self.subTest(name=name):
                response=self.get(name,shift)
                self.assertContains(response,'r1-ui r1-people-form r1-roster-record',count=1)
                paths=['css/admin.css','css/r1_tokens.css','css/r1_admin_people_forms.css',
                       'css/r1_roster_records.css','css/form_focus.css']
                text=response.content.decode()
                for path in paths:
                    self.assertContains(response,static(path),count=1)
                self.assertEqual([text.index(static(p)) for p in paths],sorted(text.index(static(p)) for p in paths))
                self.assertContains(response,'aria-label="Admin navigation"',count=2)
                self.assertContains(response,'class="admin-mobile-header"')
                self.assertNotContains(response,'r1_shell.css')
                self.assertNotContains(response,'preview-guard.js')

    def test_quick_create_and_edit_scope_keep_original_actions_and_fields(self):
        for name, shift in (('shift_create',False),('shift_edit',True)):
            response=self.get(name,shift,modal='1',service_date='2027-02-01')
            self.assertContains(response,'r1-ui r1-people-form r1-roster-record',count=1)
            self.assertContains(response,'js-shift-modal-form')
            self.assertContains(response,'data-shift-modal-close',count=2)
            self.assertContains(response,'name="modal" value="1"')
            nodes=ControlParser(response.content.decode()).nodes
            names={a.get('name') for tag,a in nodes if tag in ('input','select','textarea')}
            self.assertTrue({'participant','worker','status','service_date','start_time','end_time',
                'break_minutes','support_item','service_type','location','address','instructions','admin_notes'}<=names)
            self.assertContains(response,'5-minute intervals',count=2)

    def test_planner_loads_record_styles_but_keeps_original_scripts_and_roots(self):
        response=self.get('roster_planner',billing='1')
        self.assertContains(response,static('css/r1_roster_records.css'),count=1)
        self.assertContains(response,'class="planner-billing-drawer r1-ui r1-people-form r1-roster-record"')
        self.assertNotContains(response,'class="planner-billing-drawer r1-ui r1-people-form r1-roster-record" open')
        for name in ('shift_modal.js','planner_billing.js','date_time_picker.js','support_item_picker.js'):
            self.assertContains(response,static('js/'+name),count=1)
        self.assertEqual(ControlParser(response.content.decode()).dialog_roots,[False,False])

    def test_recurring_empty_options_are_descriptions_not_new_values(self):
        form=RecurringShiftForm()
        for name,caption in (('participant','Select participant'),('worker','Select worker'),('support_item','Select support item')):
            self.assertEqual(form.fields[name].empty_label,caption)
            self.assertEqual(next(iter(form.fields[name].choices)),('',caption))
            self.assertTrue(form.fields[name].required)

    def test_recurring_empty_time_hints_keep_original_native_controls(self):
        response=self.get('recurring_shift_create')
        self.assertContains(response,'Select start time')
        self.assertContains(response,'Select end time')
        self.assertContains(response,static('js/r1_recurring_time_hints.js'),count=1)
        nodes=ControlParser(response.content.decode()).nodes
        for name in ('start_time','end_time'):
            fields=[a for tag,a in nodes if tag=='input' and a.get('name')==name]
            self.assertEqual(len(fields),1)
            self.assertEqual(fields[0]['type'],'time')
            self.assertIn('required',fields[0])
            for attr in ('min','max','step','pattern'):
                self.assertNotIn(attr,fields[0])

    def test_recurring_existing_minutes_values_and_preview_confirm_inputs_unchanged(self):
        response=self.get('recurring_shift_create',**self.recurring_data())
        self.assertContains(response,'value="09:17"')
        self.assertContains(response,'value="12:31"')
        self.assertContains(response,'Create Non-conflicting Draft Shifts')
        self.assertContains(response,'type="hidden" name="confirm" value="1"')
        self.assertEqual(len(response.context['preview']),2)
        self.assertEqual(Shift.objects.count(),1)
        self.assertEqual(response.context['form'].cleaned_data['start_time'],time(9,17))

    def test_recurring_original_error_messages_and_empty_values_survive(self):
        response=self.get('recurring_shift_create',participant='')
        self.assertContains(response,'Select participant')
        self.assertContains(response,'Select start time')
        self.assertContains(response,'This field is required.')
        self.assertEqual(Shift.objects.count(),1)

    def test_original_detail_fields_and_conditional_post_actions_remain(self):
        response=self.get('shift_detail',True)
        for text in ('Workflow Status','Shift Details','Location and Notes','Planned hours',
                     'Instructions','Admin notes','Publish','Cancel Shift'):
            self.assertContains(response,text)
        self.assertContains(response,reverse('shift_publish',args=[self.shift.pk]))
        self.assertContains(response,reverse('shift_cancel',args=[self.shift.pk]))
        self.assertContains(response,'name="cancellation_reason"')
        self.shift.refresh_from_db()
        self.assertEqual(self.shift.status,'draft')

    def test_anonymous_sw_sc_permissions_not_changed(self):
        routes=[reverse(n,args=[self.shift.pk] if needs else []) for n,needs in
            (('shift_detail',True),('shift_create',False),('shift_edit',True),
             ('recurring_shift_create',False),('planner_billing_detail',True))]
        for role in (UserProfile.Role.SUPPORT_WORKER,UserProfile.Role.SUPPORT_COORDINATOR):
            user=get_user_model().objects.create_user(username='record-'+role)
            UserProfile.objects.create(user=user,role=role)
            self.client.force_login(user)
            for route in routes:
                self.assertEqual(self.client.get(route).status_code,403)
        self.client.logout()
        for route in routes:
            self.assertEqual(self.client.get(route).status_code,302)

    def test_record_css_preserves_closed_drawer_and_excludes_navigation(self):
        path=Path(__file__).resolve().parents[1]/'static/css/r1_roster_records.css'
        self.assertTrue(path.is_file())
        css=path.read_text()
        self.assertIn('.planner-billing-drawer[open]',css)
        for token in ('r1-roster-record','min-height: 44px','recurring-time-hint',':focus-within'):
            self.assertIn(token,css)
        for token in (':root','.sidebar','.admin-mobile-header','.planner-shift-tile'):
            self.assertNotIn(token,css)

    def test_time_hint_helper_only_updates_empty_display_state(self):
        path=Path(__file__).resolve().parents[1]/'static/js/r1_recurring_time_hints.js'
        self.assertTrue(path.is_file())
        script=path.read_text()
        self.assertIn("classList.toggle('is-empty', !input.value)",script)
        for forbidden in ('fetch(','.submit(','.requestSubmit(','.value =','localStorage','setCustomValidity'):
            self.assertNotIn(forbidden,script)
