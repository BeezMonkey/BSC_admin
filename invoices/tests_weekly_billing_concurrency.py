"""Real PostgreSQL row-lock evidence for weekly decisions and draft intents."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection, connections, transaction
from django.test import TransactionTestCase

from core.models import AuditLog
from invoices import tests_invoices as fixtures
from invoices import tests_weekly_billing as weekly_fixtures
from invoices.models import Invoice, InvoiceSettings
from invoices.workbench_actions import build_preview, create_weekly_draft
from scheduling.cancellation_review import review_participant_cancellation
from scheduling.models import ParticipantCancellation, SupportItem
from service_logs.models import ServiceLog
from service_logs.review import review_service_log
from accounts.models import UserProfile


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL row locks required')
class WeeklyBillingPostgresTests(TransactionTestCase):
    setUp = fixtures.InvoiceGenerationTests.setUp
    create_user_with_role = fixtures.InvoiceGenerationTests.create_user_with_role
    create_service_log = fixtures.InvoiceGenerationTests.create_service_log
    create_shift = weekly_fixtures.WeeklyBillingTests.create_shift
    cancellation = weekly_fixtures.WeeklyBillingTests.cancellation

    def preview(self):
        from datetime import date
        return build_preview(actor=self.admin_user, session_key='weekly-test-session', participant=self.participant,
                             start=date(2026, 6, 1), end=date(2026, 6, 7))

    def create(self, preview):
        from datetime import date
        return create_weekly_draft(actor=get_user_model().objects.get(pk=self.admin_user.pk),
            session_key='weekly-test-session', participant=self.participant,
            start=date(2026, 6, 1), end=date(2026, 6, 7),
            data={'preview_token': preview['tokens']['workbench'], 'period_mode': 'workbench'})

    def competing(self, functions):
        barrier = Barrier(len(functions))
        def invoke(function):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return ('ok', function().pk)
            except ValueError as exc:
                return ('conflict', str(exc))
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(functions)) as pool:
            return list(pool.map(invoke, functions))

    def test_same_intent_simultaneously_recovers_one_invoice(self):
        self.create_service_log()
        InvoiceSettings.load()
        preview = self.preview()
        results = self.competing([lambda: self.create(preview), lambda: self.create(preview)])
        self.assertEqual([result[0] for result in results], ['ok', 'ok'])
        self.assertEqual(results[0][1], results[1][1])
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action=AuditLog.Action.INVOICE_CREATED).count(), 1)

    def test_distinct_intents_for_same_sources_only_create_once(self):
        self.create_service_log()
        InvoiceSettings.load()
        first, second = self.preview(), self.preview()
        results = self.competing([lambda: self.create(first), lambda: self.create(second)])
        self.assertEqual(sorted(result[0] for result in results), ['conflict', 'ok'])
        self.assertEqual(Invoice.objects.count(), 1)

    def test_competing_log_decisions_only_record_one_review(self):
        log = self.create_service_log(status=ServiceLog.Status.SUBMITTED)
        other_admin = self.create_user_with_role('weekly-other-reviewer', UserProfile.Role.ADMIN)
        results = self.competing([
            lambda: review_service_log(actor=self.admin_user, service_log_id=log.pk, decision='approve'),
            lambda: review_service_log(actor=other_admin, service_log_id=log.pk, decision='reject', reason='Check time'),
        ])
        self.assertEqual(sorted(result[0] for result in results), ['conflict', 'ok'])
        self.assertEqual(AuditLog.objects.filter(object_type='ServiceLog', object_id=str(log.pk)).count(), 1)
        log.refresh_from_db()
        expected_actor = self.admin_user if log.status == ServiceLog.Status.APPROVED else other_admin
        self.assertEqual(log.reviewed_by_id, expected_actor.pk)
        self.assertEqual(AuditLog.objects.get(object_type='ServiceLog', object_id=str(log.pk)).actor_id, expected_actor.pk)

    def test_competing_cancellation_decisions_only_record_one_review(self):
        source = self.cancellation(ParticipantCancellation.Status.PENDING)
        other_admin = self.create_user_with_role('weekly-other-cancellation-reviewer', UserProfile.Role.ADMIN)
        results = self.competing([
            lambda: review_participant_cancellation(actor=self.admin_user, cancellation_id=source.pk, decision='approve'),
            lambda: review_participant_cancellation(actor=other_admin, cancellation_id=source.pk, decision='waive'),
        ])
        self.assertEqual(sorted(result[0] for result in results), ['conflict', 'ok'])
        self.assertEqual(AuditLog.objects.filter(object_type='ParticipantCancellation', object_id=str(source.pk)).count(), 1)
        source.refresh_from_db()
        expected_actor = self.admin_user if source.status == ParticipantCancellation.Status.APPROVED else other_admin
        self.assertEqual(source.reviewed_by_id, expected_actor.pk)
        self.assertEqual(AuditLog.objects.get(object_type='ParticipantCancellation', object_id=str(source.pk)).actor_id, expected_actor.pk)

    def test_rate_change_while_create_waits_for_item_lock_requires_refresh(self):
        self.create_service_log()
        InvoiceSettings.load()
        preview = self.preview()
        waiting = Event()
        def create_waiting():
            connections.close_all()
            def observe(execute, sql, params, many, context):
                if 'FOR UPDATE' in sql and 'scheduling_supportitem' in sql:
                    waiting.set()
                return execute(sql, params, many, context)
            try:
                with connection.execute_wrapper(observe):
                    return self.create(preview)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                item = SupportItem.objects.select_for_update().get(pk=self.support_item.pk)
                future = pool.submit(create_waiting)
                self.assertTrue(waiting.wait(timeout=10), 'Create did not reach the catalog lock')
                item.price_limit += 1
                item.save()
            with self.assertRaisesMessage(ValueError, 'billing rates changed'):
                future.result(timeout=10)
        self.assertFalse(Invoice.objects.exists())
