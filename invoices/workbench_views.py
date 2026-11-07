from accounts.decorators import admin_required
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from participants.models import Participant
from scheduling.models import ParticipantCancellation, Shift
from scheduling.cancellation_review import CancellationReviewConflict
from service_logs.review import ServiceLogReviewConflict
from service_logs.models import ServiceLog

from .billing import BillingRecordsChanged
from .workbench_actions import InvalidBillingDetails, build_preview, create_weekly_draft

from .workbench_forms import WeeklyBillingActionForm, WeeklyBillingPeriodForm
from .workbench_queries import build_weekly_workbench


@transaction.atomic
def _review(request, participant, period, action):
    """Recheck period/participant scope under the same locks as the decision."""
    is_log = action in ('approve', 'return')
    model = ServiceLog if is_log else ParticipantCancellation
    source_id = int(request.POST['source_id'])
    shift_id = model.objects.filter(pk=source_id).values_list('shift_id', flat=True).first()
    if shift_id is None:
        raise InvalidBillingDetails('This source is no longer available.')
    try:
        Shift.objects.select_for_update(of=('self',)).get(pk=shift_id)
        source = model.objects.select_for_update(of=('self',)).select_related('shift').get(
            pk=source_id, shift_id=shift_id)
    except (Shift.DoesNotExist, model.DoesNotExist) as exc:
        conflict = ServiceLogReviewConflict if is_log else CancellationReviewConflict
        raise conflict('This source changed before review. Refresh the workbench.') from exc
    owner = source.participant_id if is_log else source.shift.participant_id
    day = source.service_date if is_log else source.shift.service_date
    if owner != participant.pk or not period['start'] <= day <= period['end']:
        raise InvalidBillingDetails('This source is outside this participant or period.')
    if is_log:
        from service_logs.review import review_service_log
        review_service_log(actor=request.user, service_log_id=source.pk,
            decision='approve' if action == 'approve' else 'reject', reason=request.POST.get('reason', ''))
    else:
        from scheduling.cancellation_review import review_participant_cancellation
        review_participant_cancellation(actor=request.user, cancellation_id=source.pk,
            decision=action.removeprefix('cancel_'), admin_note=request.POST.get('admin_note', ''))


@admin_required
@require_http_methods(['GET', 'POST'])
def weekly_billing(request):
    form = WeeklyBillingPeriodForm(request.POST if request.method == 'POST' else request.GET)
    period = None
    workbench = None
    preview = None
    participant = None
    message = ''
    status = 200
    invoice = None
    action = request.POST.get('action', '') if request.method == 'POST' else ''
    if form.is_valid():
        period = form.period
        if request.method == 'POST':
            try:
                action_form = WeeklyBillingActionForm(request.POST)
                if not action_form.is_valid():
                    raise InvalidBillingDetails('Choose a valid participant, source and workbench action.')
                participant_id = action_form.cleaned_data['participant_id']
                participant = Participant.objects.get(pk=participant_id)
                if action in ('approve', 'return'):
                    _review(request, participant, period, action)
                    message = 'Log approved.' if action == 'approve' else 'Log returned to worker.'
                elif action in ('cancel_approve', 'cancel_waive', 'cancel_reject'):
                    _review(request, participant, period, action)
                    message = 'Cancellation reviewed.'
                elif action == 'preview':
                    preview = build_preview(actor=request.user, session_key=request.session.session_key,
                        participant=participant, start=period['start'], end=period['end'])
                elif action == 'create':
                    data = request.POST.copy()
                    selected_token = data.get('preview_token_' + data.get('period_mode', 'workbench'))
                    if selected_token:
                        data['preview_token'] = selected_token
                    invoice = create_weekly_draft(actor=request.user, session_key=request.session.session_key,
                        participant=participant, start=period['start'], end=period['end'], data=data,
                        results=request.session.get('weekly_billing_results', {}))
                    results = request.session.get('weekly_billing_results', {})
                    # This is a recovery index, never authority for eligibility or amounts.
                    from hashlib import sha256
                    results[sha256(data.get('preview_token', '').encode()).hexdigest()] = invoice.pk
                    request.session['weekly_billing_results'] = dict(list(results.items())[-24:])
                    message = (f'Draft {invoice.invoice_number} is ready to review. It has not been issued.'
                        if invoice.status == invoice.Status.DRAFT else
                        f'{invoice.invoice_number} already exists ({invoice.get_status_display()}). Open the saved invoice to review it.')
                else:
                    raise InvalidBillingDetails('Choose a supported workbench action.')
            except (BillingRecordsChanged, ServiceLogReviewConflict, CancellationReviewConflict) as exc:
                message, status = str(exc), 409
            except (InvalidBillingDetails, ValueError) as exc:
                message, status = str(exc), 400
            except Participant.DoesNotExist:
                message, status = 'Choose a participant in this period.', 400
            if action == 'create' and invoice is None and participant is not None:
                try:
                    preview = build_preview(actor=request.user, session_key=request.session.session_key,
                        participant=participant, start=period['start'], end=period['end'], data=request.POST,
                        tokens={'workbench': request.POST.get('preview_token_workbench', request.POST.get('preview_token', '')),
                                'actual': request.POST.get('preview_token_actual', request.POST.get('preview_token', ''))})
                    preview['stale'] = status == 409
                except BillingRecordsChanged:
                    preview = None
        workbench = build_weekly_workbench(period['start'], period['end'])
        for row in workbench['participant_rows']:
            if preview and row['participant'].pk == preview['participant'].pk:
                row['preview'] = preview
    elif request.method == 'POST':
        message, status = 'Choose a valid billing period before continuing.', 400
    context = {
        'period_form': form, 'period': period, 'workbench': workbench,
        'billing_preview': preview, 'action_message': message, 'action_error': status != 200,
        'action_participant_id': participant.pk if participant else None,
        'created_invoice': invoice,
        'travel_unit_price': preview['travel_unit_price'] if preview else 0,
    }
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'html': render_to_string('invoices/weekly_billing.html', context, request=request),
                             'message': message, 'action': action,
                             'participant_id': context['action_participant_id'],
                             'invoice_id': invoice.pk if invoice else None}, status=status)
    return render(request, 'invoices/weekly_billing.html', context, status=status)
