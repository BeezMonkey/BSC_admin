const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const file = path.resolve(__dirname, '../../static/js/planner_billing.js');

function setup() {
  const elements = {};
  let focused;
  function element() {
    return { dataset: {}, listeners: {}, attrs: {}, disabled: false, hidden: false, isConnected: true,
      textContent: '', innerHTML: '', scrollTop: 0, open: false,
      addEventListener(name, fn) { this.listeners[name] = fn; },
      fire(name, extra = {}) { return this.listeners[name]?.({ target: this, preventDefault() {}, ...extra }); },
      setAttribute(name, value) { this.attrs[name] = value; },
      removeAttribute(name) { delete this.attrs[name]; },
      focus() { focused = this; },
      showModal() { this.open = true; },
      close() { this.open = false; this.fire('close'); },
      getBoundingClientRect() { return { left: 500, right: 1000, top: 0, bottom: 800 }; },
      querySelector(selector) { return elements[selector]; },
      closest(selector) { return selector === '[data-planner-billing-url]' && this.dataset.plannerBillingUrl ? this : null; },
    };
  }
  for (const key of ['#planner-filter-form', '#planner-billing-toggle', '#planner-billing-filter', '#planner-billing-drawer',
    '[data-planner-billing-content]', '[data-planner-billing-context]', '[data-planner-billing-position]',
    '[data-planner-billing-close]', '[data-planner-billing-prev]', '[data-planner-billing-next]']) elements[key] = element();
  const classes = new Set();
  const document = { listeners: {}, body: { classList: { add: x => classes.add(x), remove: x => classes.delete(x) } },
    querySelector: s => elements[s], querySelectorAll: () => triggers,
    addEventListener(name, fn) { this.listeners[name] = fn; },
  };
  const triggers = [1, 2].map(id => Object.assign(element(), { href: `/roster/planner/${id}/billing/`, dataset: {
    plannerBillingUrl: `/roster/planner/${id}/billing/?partial=1`, plannerBillingId: String(id), plannerBillingContext: `Shift #${id}`,
  } }));
  const requests = [];
  const fetch = (url, options) => new Promise((resolve, reject) => requests.push({ url, options, resolve, reject }));
  const window = { location: { href: '' } };
  const source = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
  vm.runInNewContext(source, { document, window, fetch, AbortController });
  const open = (n = 0) => document.listeners.click?.({ target: triggers[n], preventDefault() {}, button: 0 });
  const respond = (i, html = '<section>Loaded</section>', overrides = {}) => requests[i].resolve({
    ok: true, redirected: false, status: 200, headers: { get: name => name === 'X-Planner-Billing' ? '1' : 'text/html' },
    text: async () => html, ...overrides,
  });
  const tick = () => new Promise(resolve => setImmediate(resolve));
  return { elements, triggers, requests, open, respond, tick, classes, get focused() { return focused; } };
}

test('opens a modal with loading state and fetches uncached read-only data', async () => {
  const x = setup(); x.open();
  assert.equal(x.elements['#planner-billing-drawer'].open, true);
  assert.equal(x.requests.length, 1);
  assert.equal(x.requests[0].options.cache, 'no-store');
  assert.match(x.elements['[data-planner-billing-content]'].innerHTML, /Loading/);
  x.respond(0); await x.tick();
  assert.match(x.elements['[data-planner-billing-content]'].innerHTML, /Loaded/);
});
test('late previous-shift response cannot overwrite the current shift', async () => {
  const x = setup(); x.open(); x.elements['[data-planner-billing-next]'].fire('click');
  assert.equal(x.requests.length, 2);
  assert.equal(x.requests[0].options.signal.aborted, true);
  x.respond(1, 'Shift two'); await x.tick(); x.respond(0, 'Shift one'); await x.tick();
  assert.equal(x.elements['[data-planner-billing-content]'].innerHTML, 'Shift two');
});
test('closing aborts a request and restores the original card focus', async () => {
  const x = setup(); x.open(); x.elements['[data-planner-billing-close]'].fire('click');
  assert.equal(x.requests[0].options.signal.aborted, true);
  assert.equal(x.elements['#planner-billing-drawer'].open, false);
  assert.equal(x.focused, x.triggers[0]);
  x.respond(0, 'Too late'); await x.tick();
  assert.doesNotMatch(x.elements['[data-planner-billing-content]'].innerHTML, /Too late/);
  assert.equal(x.classes.size, 0);
});
test('redirected login and non-partial response are not injected', async () => {
  for (const override of [{ redirected: true }, { headers: { get: () => null } }]) {
    const x = setup(); x.open(); x.respond(0, '<form>Password</form>', override); await x.tick();
    const html = x.elements['[data-planner-billing-content]'].innerHTML;
    assert.doesNotMatch(html, /Password/); assert.match(html, /Retry/);
  }
});
test('network failure displays an error, never Not invoiced', async () => {
  const x = setup(); x.open(); x.requests[0].reject(new Error('offline')); await x.tick();
  const html = x.elements['[data-planner-billing-content]'].innerHTML;
  assert.match(html, /Unable to load/); assert.doesNotMatch(html, /Not invoiced/);
});
test('next and previous stay within visible shift list', () => {
  const x = setup(); x.open();
  assert.equal(x.elements['[data-planner-billing-prev]'].disabled, true);
  x.elements['[data-planner-billing-next]'].fire('click');
  assert.equal(x.elements['[data-planner-billing-next]'].disabled, true);
  assert.equal(x.elements['[data-planner-billing-position]'].textContent, '2 of 2 shifts');
});

test('retry fetches the same shift and replaces the error on success', async () => {
  const x = setup(); x.open();
  x.requests[0].reject(new Error('offline')); await x.tick();
  x.elements['[data-planner-billing-content]'].fire('click', {
    target: { closest: selector => selector === '[data-planner-billing-retry]' },
  });
  assert.equal(x.requests.length, 2);
  assert.equal(x.requests[1].url, x.requests[0].url);
  assert.equal(x.focused, x.elements['[data-planner-billing-close]']);
  x.respond(1, 'Recovered'); await x.tick();
  assert.equal(x.elements['[data-planner-billing-content]'].innerHTML, 'Recovered');
});

test('toggle and billing filter submit the existing planner filter form', () => {
  const x = setup(); let submissions = 0;
  x.elements['#planner-filter-form'].requestSubmit = () => { submissions += 1; };
  const toggle = x.elements['#planner-billing-toggle'];
  const filter = x.elements['#planner-billing-filter'];
  toggle.checked = true; toggle.fire('change');
  assert.equal(filter.disabled, false);
  filter.fire('change');
  toggle.checked = false; toggle.fire('change');
  assert.equal(filter.disabled, true);
  assert.equal(submissions, 3);
});
