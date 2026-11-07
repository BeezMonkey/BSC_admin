const assert = require('node:assert/strict');
const { readFileSync, existsSync } = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const weeklyPath = path.resolve(__dirname, '../../static/js/weekly_billing.js');
const weeklySource = existsSync(weeklyPath) ? readFileSync(weeklyPath, 'utf8') : '';
const adapterSource = readFileSync(path.resolve(__dirname, '../../static/js/r1_admin_invoice_filters.js'), 'utf8');

class MockEvent {
  constructor(type, options = {}) { Object.assign(this, { type, defaultPrevented: false }, options); }
  preventDefault() { this.defaultPrevented = true; }
}
function target(properties = {}) {
  const listeners = new Map();
  return Object.assign({
    addEventListener(type, listener) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(listener);
    },
    dispatchEvent(event) {
      event.target ||= this;
      for (const listener of listeners.get(event.type) || []) listener(event);
      return !event.defaultPrevented;
    },
    fire(type, options = {}) { const event = new MockEvent(type, options); this.dispatchEvent(event); return event; },
  }, properties);
}
// Stub fixed selectors and browser validation only; the shared calendar is left
// behind its initialization/proxy-change contract, with real adapter events.
function setup({ desktop = true, page = 'weekly', period = 'this_week', start = '', end = '', boundError = false } = {}) {
  const document = target({ activeElement: null });
  function control(properties = {}) {
    const attrs = {};
    return target(Object.assign({
      value: '', hidden: false, disabled: false, textContent: '', attrs,
      setAttribute(name, value) { attrs[name] = String(value); },
      getAttribute(name) { return attrs[name] ?? null; },
      removeAttribute(name) { delete attrs[name]; },
      focus() { document.activeElement = this; },
      click() { this.fire('click'); },
    }, properties));
  }
  function dateRoot(name, value, invalid) {
    const native = control({ name, value, tabIndex: 0, customError: '',
      setCustomValidity(message) { this.customError = message; },
    });
    Object.defineProperties(native, {
      validity: { get: () => ({ valid: !native.customError }) },
      validationMessage: { get: () => native.customError },
    });
    if (invalid) native.setAttribute('aria-invalid', 'true');
    const proxy = control();
    const trigger = control({ hidden: true });
    trigger.setAttribute('aria-expanded', 'false');
    const display = control();
    const day = control();
    const panel = control({ hidden: true, contains: node => node === panel || node === day });
    panel.querySelector = selector => selector.startsWith('.calendar-day') ? day : null;
    const error = control({ hidden: true });
    const serverError = invalid ? control({ textContent: 'The end date must be on or after the start date.' }) : null;
    const label = control();
    const classes = new Set();
    const selectors = {
      'input[type=date]': native, '[data-invoice-date-proxy]': proxy,
      '[data-picker-trigger]': trigger, '[data-picker-display]': display,
      '[data-picker-popover]': panel, '[data-invoice-date-error]': error,
      '[data-invoice-date-server-error]': serverError, label,
    };
    const root = {
      dataset: {}, querySelector: selector => selectors[selector] || null,
      classList: { toggle(name, enabled) { if (enabled) classes.add(name); else classes.delete(name); }, contains: name => classes.has(name) },
    };
    return { root, native, proxy, trigger, display, panel, day, error, serverError, label };
  }
  const dates = [dateRoot('start', start, false), dateRoot('end', end, boundError)];
  const range = control({ value: period });
  let submissions = 0;
  const form = target({
    elements: { period: range, start: dates[0].native, end: dates[1].native },
    querySelectorAll(selector) { assert.equal(selector, '[data-invoice-date]'); return dates.map(date => date.root); },
    querySelector(selector) {
      assert.ok([':invalid', 'input:invalid, select:invalid, textarea:invalid'].includes(selector));
      const invalid = dates.map(date => date.native).find(native => !native.validity.valid) || null;
      // A real fieldset also matches :invalid and precedes its date controls.
      if (selector === ':invalid' && invalid && page === 'weekly') return { tagName: 'FIELDSET' };
      return invalid;
    },
    reportValidity() {
      let valid = true;
      for (const { native } of dates) if (!native.validity.valid) { native.fire('invalid'); valid = false; }
      return valid;
    },
    submit() { submissions++; }, requestSubmit() { submissions++; },
  });
  dates.forEach(date => date.root.parentElement = form);
  document.querySelector = selector => {
    if (selector === '[data-weekly-billing-filters]') return page === 'weekly' ? form : null;
    if (selector.includes('.weekly-billing') && page === 'weekly') return form;
    if (selector.includes('.r1-admin-invoice-list') && page === 'invoice') return form;
    return null;
  };
  const media = target({ matches: desktop });
  let initializations = 0;
  const window = {
    matchMedia(query) { assert.equal(query, '(min-width: 761px) and (hover: hover) and (pointer: fine)'); return media; },
    initDateTimePickers() {
      for (const date of dates) {
        if (!date.root.dataset.dateTimePicker || date.root.initialized) continue;
        date.root.initialized = true;
        initializations++;
        date.trigger.addEventListener('click', () => {
          date.panel.hidden = date.trigger.getAttribute('aria-expanded') === 'true';
          date.trigger.setAttribute('aria-expanded', String(!date.panel.hidden));
        });
      }
    },
  };
  const context = { window, document, Event: MockEvent, setTimeout };
  vm.runInNewContext(adapterSource, context);
  if (page === 'weekly') vm.runInNewContext(weeklySource, context);
  return { form, range, start: dates[0], end: dates[1], document,
    initializations: () => initializations, submissions: () => submissions,
    setDesktop(matches) { media.matches = matches; media.fire('change'); },
  };
}

test('editing either named date selects Custom without submitting', () => {
  const h = setup();
  h.start.native.value = '2026-11-02'; h.start.native.fire('input');
  assert.equal(h.range.value, 'custom');
  h.range.value = 'last_week';
  h.end.native.value = '2026-11-08'; h.end.native.fire('change');
  assert.equal(h.range.value, 'custom');
  assert.equal(h.submissions(), 0);
});
test('selecting a preset clears dates, stale validity and enhanced display without losing focus', () => {
  const h = setup({ period: 'custom', start: '2026-11-08', end: '2026-11-02' });
  assert.equal(h.end.native.validity.valid, false);
  h.range.focus(); h.range.value = 'this_week'; h.range.fire('change');
  for (const date of [h.start, h.end]) {
    assert.equal(date.native.value, ''); assert.equal(date.native.validity.valid, true);
    assert.equal(date.proxy.value, ''); assert.equal(date.display.textContent, 'dd/mm/yyyy');
    assert.equal(date.trigger.getAttribute('aria-invalid'), 'false');
  }
  assert.equal(h.document.activeElement, h.range);
  assert.equal(h.form.fire('submit').defaultPrevented, false);
  assert.equal(h.submissions(), 0);
});
test('Custom stays pristine on selection, then requires both dates on submit and focuses visible trigger', () => {
  const h = setup(); h.range.value = 'custom'; h.range.fire('change');
  assert.equal(h.start.trigger.getAttribute('aria-invalid'), 'false');
  assert.equal(h.end.trigger.getAttribute('aria-invalid'), 'false');
  assert.equal(h.form.fire('submit').defaultPrevented, true);
  assert.equal(h.start.native.validity.valid, false); assert.equal(h.end.native.validity.valid, false);
  assert.equal(h.document.activeElement, h.start.trigger);
  assert.equal(h.start.error.hidden, false);
});
test('reversed Custom dates fail; correcting them synchronizes validity and keeps focus', () => {
  const h = setup({ period: 'custom', start: '2026-11-08', end: '2026-11-02' });
  assert.equal(h.form.fire('submit').defaultPrevented, true);
  assert.equal(h.end.trigger.getAttribute('aria-invalid'), 'true');
  assert.equal(h.document.activeElement, h.end.trigger);
  h.end.native.focus(); h.end.native.value = '2026-11-08'; h.end.native.fire('input');
  assert.equal(h.end.native.validity.valid, true);
  assert.equal(h.end.trigger.getAttribute('aria-invalid'), 'false');
  assert.equal(h.document.activeElement, h.end.native);
  assert.equal(h.form.fire('submit').defaultPrevented, false);
});
test('empty presets do not acquire false validation errors', () => {
  const h = setup();
  assert.equal(h.form.fire('submit').defaultPrevented, false);
  assert.equal(h.start.native.validity.valid, true); assert.equal(h.end.native.validity.valid, true);
  assert.equal(h.submissions(), 0);
});
test('calendar proxy changes roundtrip through native fields and choose Custom', () => {
  const h = setup();
  assert.equal(h.initializations(), 2);
  h.start.proxy.value = '2026-11-02'; h.start.proxy.fire('change');
  assert.equal(h.start.native.value, '2026-11-02'); assert.equal(h.range.value, 'custom');
  assert.equal(h.start.display.textContent, '02/11/2026');
  assert.equal(h.document.activeElement, h.start.trigger); assert.equal(h.start.proxy.name, undefined);
});
test('adapter keeps the invoice page working and native dates on touch', () => {
  const invoice = setup({ page: 'invoice', start: '2026-11-02' });
  assert.equal(invoice.initializations(), 2);
  assert.equal(invoice.start.display.textContent, '02/11/2026');
  const mobile = setup({ desktop: false });
  assert.equal(mobile.initializations(), 0); assert.equal(mobile.start.trigger.hidden, true);
  assert.equal(mobile.start.native.tabIndex, 0);
  assert.equal(mobile.start.native.fire('invalid').defaultPrevented, false);
});
test('breakpoint changes close the calendar and preserve one initialization per field', () => {
  const h = setup(); h.start.trigger.click();
  assert.equal(h.start.panel.hidden, false); h.setDesktop(false);
  assert.equal(h.start.panel.hidden, true); assert.equal(h.start.trigger.hidden, true);
  assert.equal(h.start.native.tabIndex, 0); h.setDesktop(true);
  assert.equal(h.initializations(), 2); assert.equal(h.start.trigger.hidden, false);
});
test('bound server errors remain marked until the date changes', () => {
  const h = setup({ period: 'custom', start: '2026-11-08', end: '2026-11-02', boundError: true });
  assert.equal(h.end.trigger.getAttribute('aria-invalid'), 'true');
  h.end.native.value = '2026-11-09'; h.end.native.fire('input');
  assert.equal(h.end.trigger.getAttribute('aria-invalid'), 'false');
  assert.equal(h.end.serverError.hidden, true);
  assert.equal(h.end.serverError.textContent, "", "Hidden aria-describedby errors must not keep announcing a corrected error");
});

test('correcting Start clears the obsolete bound End range error for the pair', () => {
  const h = setup({ period: 'custom', start: '2026-11-08', end: '2026-11-02', boundError: true });
  assert.equal(h.end.trigger.getAttribute('aria-invalid'), 'true');
  h.start.native.value = '2026-11-01'; h.start.native.fire('input');
  assert.equal(h.end.native.validity.valid, true);
  assert.equal(h.end.trigger.getAttribute('aria-invalid'), 'false');
  assert.equal(h.end.serverError.hidden, true);
  assert.equal(h.end.serverError.textContent, '');
  assert.equal(h.form.fire('submit').defaultPrevented, false);
});
test('initial resynchronization preserves bound errors until a user edit', () => {
  const h = setup({ period: 'custom', start: '2026-11-01', end: '2026-11-02', boundError: true });
  assert.equal(h.end.native.validity.valid, true);
  assert.equal(h.end.trigger.getAttribute('aria-invalid'), 'true');
  assert.equal(h.end.serverError.hidden, false);
  assert.notEqual(h.end.serverError.textContent, '');
});
