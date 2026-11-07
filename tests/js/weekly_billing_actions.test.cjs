const assert = require('node:assert/strict');
const { readFileSync, existsSync } = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const filename = path.resolve(__dirname, '../../static/js/weekly_billing_actions.js');
function api() {
  const context = { window: {}, document: { querySelector: () => null } };
  vm.runInNewContext(existsSync(filename) ? readFileSync(filename, 'utf8') : '', context, { filename });
  assert.ok(context.window.WeeklyBillingActions, 'same-page billing actions must expose their lifecycle');
  return context.window.WeeklyBillingActions;
}
test('only return and cancellation rejection require a review reason', () => {
  const a = api();
  for (const action of ['return', 'cancel_reject']) assert.equal(a.requiresReason(action), true);
  for (const action of ['approve', 'cancel_approve', 'cancel_waive']) assert.equal(a.requiresReason(action), false);
});
test('period choice selects its own signed preview token without changing adjustment inputs', () => {
  const a = api();
  const controls = {
    period_mode: { value: 'actual' }, preview_token: { value: '' },
    preview_token_workbench: { value: 'selected-period' }, preview_token_actual: { value: 'source-period' },
    'adjustment-4-kilometres': { value: '12.50' },
  };
  a.selectToken({ elements: controls });
  assert.equal(controls.preview_token.value, 'source-period');
  controls.period_mode.value = 'workbench';
  a.selectToken({ elements: controls });
  assert.equal(controls.preview_token.value, 'selected-period');
  assert.equal(controls['adjustment-4-kilometres'].value, '12.50');
});
test('stale retained previews disable creation and expose explicit refresh guidance', () => {
  const a = api(); const create = { disabled: false }; const warning = { hidden: true };
  const preview = { dataset: {}, querySelector: selector => selector === '[data-wb-create]' ? create : warning };
  a.markStale(preview);
  assert.equal(preview.dataset.stale, 'true'); assert.equal(create.disabled, true); assert.equal(warning.hidden, false);
});
test('weekly page reuses original billing rows and exactly one shared drawer', () => {
  const main = readFileSync(path.resolve(__dirname, '../../templates/invoices/weekly_billing.html'), 'utf8');
  const preview = readFileSync(path.resolve(__dirname, '../../templates/invoices/workbench/participant.html'), 'utf8');
  assert.equal((main.match(/include "invoices\/invoice_adjustment_drawer.html"/g) || []).length, 1);
  assert.match(preview, /include "invoices\/invoice_billing_row.html"/);
  assert.doesNotMatch(main, /r1-admin-invoice-create|css\/r1_admin_invoice_create.css/);
  assert.match(preview, /preview_token_workbench/); assert.match(preview, /preview_token_actual/);
});

// Tree-backed ownership for the coordinator's partial replacement boundary.
function node(tag = 'div', dataset = {}, properties = {}) {
  const n = { tag, dataset, children: [], parentElement: null, value: '', name: '', type: '', id: '', open: false,
    attrs: {}, listeners: {}, classList: { toggle() {} },
    setAttribute(key, value) { this.attrs[key] = value; }, getAttribute(key) { return this.attrs[key] ?? null; },
    addEventListener(type, callback) { this.listeners[type] = callback; },
    append(child) { if (child.parentElement) child.parentElement.children.splice(child.parentElement.children.indexOf(child), 1); child.parentElement = this; this.children.push(child); return child; },
    replaceWith(replacement) { const parent = this.parentElement; if (replacement.parentElement) replacement.parentElement.children.splice(replacement.parentElement.children.indexOf(replacement), 1); parent.children[parent.children.indexOf(this)] = replacement; replacement.parentElement = parent; this.parentElement = null; },
    contains(child) { return child === this || this.children.some(item => item.contains(child)); },
    matches(selector) {
      const parts = selector.split(/\s+/); const last = parts.pop();
      if (parts.length) { if (!this.matches(last)) return false; for (let parent = this.parentElement; parent; parent = parent.parentElement) if (parent.matches(parts.join(' '))) return true; return false; }
      const match = selector.match(/^([a-z]+)?(?:\[([\w-]+)(?:="?([^"\]]+)"?)?\])?$/);
      assert.ok(match, 'Mock selector: ' + selector);
      if (match[1] && this.tag !== match[1]) return false;
      if (!match[2]) return true;
      const key = match[2];
      const value = key.startsWith('data-') ? this.dataset[key.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] : this[key] || this.attrs[key];
      return match[3] === undefined ? value !== undefined : String(value) === match[3];
    },
    querySelectorAll(selector) { const selectors = selector.split(',').map(value => value.trim()); const results = []; const visit = parent => parent.children.forEach(child => { if (selectors.some(s => child.matches(s))) results.push(child); visit(child); }); visit(this); return results; },
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; },
    closest(selector) { for (let item = this; item; item = item.parentElement) if (item.matches(selector)) return item; return null; },
  };
  return Object.assign(n, properties);
}
function controller(root, incoming, overrides = {}) {
  const destroyed = [];
  const document = { querySelector: () => root, addEventListener() {} };
  const window = { addEventListener() {}, confirm: () => true, location: { href: 'https://qa.example.invalid/billing/weekly/' }, scrollX: 3, scrollY: 410, scrollTo(x, y) { this.position = [x, y]; },
    InvoiceBilling: { initWithin() {}, destroyWithin(scope) { destroyed.push(scope); }, hasUnappliedChanges: () => false, isOpen: () => false } };
  const context = { document, window, DOMParser: class { parseFromString() { return incoming; } },
    FormData: class { constructor(form) { this.values = new Map(form.querySelectorAll('input[name], select[name], textarea[name]').map(input => [input.name, input.value])); } set(name, value) { this.values.set(name, value); } }, ...overrides };
  vm.runInNewContext(readFileSync(filename, 'utf8'), context, { filename });
  return { api: window.WeeklyBillingActions, window, destroyed };
}
function participant(parent, key = 'before') {
  const p = parent.append(node('details', { wbParticipant: '7', sourceKey: key }, { id: 'participant-7', open: true }));
  const slot = p.append(node('div', { wbPreviewSlot: '' }));
  const refresh = slot.append(node('form', { wbAction: '', wbRefresh: '' }, { elements: {} }));
  const button = refresh.append(node('button', {}, { type: 'submit', disabled: false }));
  return { p, slot, refresh, button };
}
test('a failed create remains dirty even before another edit', () => {
  const root = node('div', { weeklyBilling: '' });
  root.append(node('form', { wbAction: '', wbUnsaved: 'true' }, { elements: {} }));
  assert.equal(controller(root).api.hasChanges(), true);
});
test('partial refresh preserves other participant inputs and enables a newly eligible preview', () => {
  const root = node('div', { weeklyBilling: '' }); const previous = root.append(node('div', { wbResults: '' }));
  const old = participant(previous); old.button.disabled = true;
  const incoming = node(); const next = incoming.append(node('div', { wbResults: '' })); const fresh = participant(next, 'after');
  const h = controller(root, incoming);
  h.api.refresh({ html: '<server response>', participant_id: 7, action: 'approve' }, 200);
  assert.equal(fresh.p.querySelector('[data-wb-refresh]').querySelector('button').disabled, false);
  assert.deepEqual(h.window.position, [3, 410]); assert.equal(fresh.p.open, true);
});
test('partial refresh keeps exact input nodes, marks changed source previews stale, and tears down only discarded rows', () => {
  const root = node('div', { weeklyBilling: '' }); const previous = root.append(node('div', { wbResults: '' }));
  const old = participant(previous);
  const preview = old.slot.append(node('section', { wbPreview: '' }));
  const form = preview.append(node('form', { wbAction: '', wbCreateForm: '' }, { elements: {} }));
  const claim = form.append(node('input', {}, { name: 'travel-4-amount', value: '23.50' }));
  const create = form.append(node('button', { wbCreate: '' }, { disabled: false }));
  const warning = preview.append(node('p', { wbStale: '' }, { hidden: true }));
  const incoming = node(); const next = incoming.append(node('div', { wbResults: '' })); const fresh = participant(next, 'after');
  fresh.button.textContent = 'Preview approved sources'; fresh.button.disabled = true;
  const h = controller(root, incoming);
  h.api.refresh({ html: '<server response>', participant_id: 99, action: 'approve' }, 200);
  assert.equal(fresh.p.querySelector('input'), claim); assert.equal(claim.value, '23.50');
  const refreshButton = fresh.p.querySelector('[data-wb-refresh]').querySelector('button');
  assert.equal(refreshButton.textContent, 'Refresh preview'); assert.equal(refreshButton.disabled, false);
  assert.equal(create.disabled, true); assert.equal(warning.hidden, false);
  assert.equal(h.destroyed.length, 1); assert.equal(h.destroyed[0].contains(claim), false);
});
test('network failure retains edits, restores submit controls, and suppresses repeated requests while pending', async () => {
  const root = node('div', { weeklyBilling: '' }); const results = root.append(node('div', { wbResults: '' }));
  const feedback = results.append(node('p', { wbFeedback: '' })); const p = participant(results);
  const preview = p.slot.append(node('section', { wbPreview: '', stale: 'false' }));
  const form = preview.append(node('form', { wbAction: '', wbCreateForm: '', participantName: 'QA participant' }, { elements: { action: { value: 'create' } }, reportValidity: () => true }));
  const claim = form.append(node('input', {}, { name: 'travel-4-amount', value: '23.50' }));
  const button = form.append(node('button', { wbCreate: '' }, { type: 'submit', disabled: false, isConnected: true }));
  let requests = 0; let reject;
  controller(root, undefined, { fetch: () => { requests++; return new Promise((resolve, fail) => { reject = fail; }); } });
  claim.value = '25.00';
  const event = () => ({ target: form, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } });
  const first = root.listeners.submit(event());
  await root.listeners.submit(event());
  assert.equal(requests, 1); assert.equal(button.disabled, true);
  reject(new Error('Network unavailable. Please retry.'));
  await first;
  assert.equal(claim.value, '25.00'); assert.equal(button.disabled, false); assert.match(feedback.textContent, /retry/);
});
test('an unsent review note stays dirty after an unrelated partial refresh', () => {
  const root = node('div', { weeklyBilling: '' }); const previous = root.append(node('div', { wbResults: '' }));
  const oldForm = previous.append(node('form', { wbAction: '', wbReview: '' }, { elements: {} }));
  const note = oldForm.append(node('textarea', { wbReason: '' }, { name: 'reason', id: 'review-reason-7' }));
  const incoming = node(); const next = incoming.append(node('div', { wbResults: '' }));
  const nextForm = next.append(node('form', { wbAction: '', wbReview: '' }, { elements: {} }));
  const nextNote = nextForm.append(node('textarea', { wbReason: '' }, { name: 'reason', id: 'review-reason-7' }));
  const h = controller(root, incoming);
  note.value = 'Check this time with the worker'; assert.equal(h.api.hasChanges(), true);
  h.api.refresh({ html: '<server response>', participant_id: 99, action: 'preview' }, 200);
  assert.equal(nextNote.value, 'Check this time with the worker');
  assert.equal(h.api.hasChanges(), true);
});
for (const [action, tag] of [['preview', 'button'], ['create', 'input']]) {
  test(`${action} posts to the current endpoint when named action controls shadow form.action`, async () => {
    const root = node('div', { weeklyBilling: '' }); const previous = root.append(node('div', { wbResults: '' }));
    previous.append(node('p', { wbFeedback: '' })); const old = participant(previous);
    const form = old.refresh;
    form.reportValidity = () => true;
    const namedAction = form.append(node(tag, {}, { name: 'action', value: action, type: tag === 'input' ? 'hidden' : 'submit' }));
    // HTMLFormElement named access exposes this control instead of the native URL property.
    form.action = namedAction; form.elements.action = namedAction;
    const incoming = node(); const next = incoming.append(node('div', { wbResults: '' })); const fresh = participant(next);
    if (action === 'preview') fresh.slot.append(node('section', { wbPreview: '' }));
    let submittedUrl;
    const h = controller(root, incoming, { fetch: async (url, options) => {
      submittedUrl = url;
      assert.equal(options.body.values.get('action'), action);
      return { status: 200, headers: { get: () => 'application/json' }, json: async () => ({ html: '<server response>', action, participant_id: 7 }) };
    } });
    await root.listeners.submit({ target: form, submitter: tag === 'button' ? namedAction : undefined, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } });
    assert.equal(form.getAttribute('action'), null);
    assert.equal(submittedUrl, h.window.location.href);
    if (action === 'preview') assert.ok(root.querySelector('[data-wb-preview]'));
  });
}
test('an HTML response gives retry guidance while retaining inputs and restoring the preview button', async () => {
  const root = node('div', { weeklyBilling: '' }); const previous = root.append(node('div', { wbResults: '' }));
  const feedback = previous.append(node('p', { wbFeedback: '' })); const old = participant(previous);
  old.refresh.reportValidity = () => true;
  const button = old.button; button.name = 'action'; button.value = 'preview'; button.isConnected = true;
  old.refresh.elements.action = button;
  const input = old.refresh.append(node('input', {}, { name: 'participant_id', value: '7' }));
  controller(root, undefined, { fetch: async () => ({ status: 404, headers: { get: () => 'text/html; charset=utf-8' },
    json: async () => { throw new SyntaxError('Unexpected token <, <!doctype html> is not valid JSON'); } }) });
  await root.listeners.submit({ target: old.refresh, submitter: button, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } });
  assert.equal(input.value, '7'); assert.equal(button.disabled, false);
  assert.match(feedback.textContent, /retry/i); assert.match(feedback.textContent, /retained/i);
  assert.doesNotMatch(feedback.textContent, /Unexpected token|doctype|SyntaxError/);
});
