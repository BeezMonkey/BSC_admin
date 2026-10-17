const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const filename = path.resolve(__dirname, "../../static/js/r1_admin_invoice_create.js");
const source = readFileSync(filename, "utf8");

class MockEvent {
  constructor(type, options = {}) {
    Object.assign(this, { type, bubbles: false, defaultPrevented: false }, options);
  }
  preventDefault() { this.defaultPrevented = true; }
}

function target(properties = {}) {
  const listeners = new Map();
  return Object.assign({
    events: [],
    addEventListener(type, listener) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(listener);
    },
    dispatchEvent(event) {
      event.target ||= this;
      this.events.push(event);
      for (const listener of listeners.get(event.type) || []) listener(event);
      return !event.defaultPrevented;
    },
    fire(type, options = {}) {
      const event = new MockEvent(type, options);
      this.dispatchEvent(event);
      return event;
    },
  }, properties);
}

// Only the adapter's fixed selectors/events are stubbed. The shared calendar
// engine is represented by its initialization/toggle contract, not reimplemented.
function setup({ desktop = true, boundInvalid = false, value = "", engine = true } = {}) {
  const document = target({ activeElement: null });
  function control(properties = {}) {
    const attrs = {};
    return Object.assign(target(), {
      attrs, hidden: false, disabled: false, value: "", textContent: "",
      setAttribute(name, value) { attrs[name] = String(value); },
      getAttribute(name) { return Object.hasOwn(attrs, name) ? attrs[name] : null; },
      focus() { document.activeElement = this; },
      click() { this.fire("click"); },
    }, properties);
  }
  const native = control({ name: "period_start", type: "date", required: true, value, tabIndex: 0 });
  Object.defineProperties(native, {
    validity: { get: () => ({ valid: native.disabled || !native.required || native.value !== "" }) },
    validationMessage: { get: () => native.validity.valid ? "" : "Please fill out this field." },
  });
  const proxy = control({ type: "hidden" });
  const trigger = control({ hidden: true });
  trigger.setAttribute("aria-expanded", "false");
  trigger.setAttribute("aria-describedby", "id_period_start-client-error" + (boundInvalid ? " id_period_start_error" : ""));
  if (boundInvalid) trigger.setAttribute("aria-invalid", "true");
  const display = control();
  const day = control();
  const panel = control({ hidden: true });
  panel.querySelector = selector => selector.startsWith(".calendar-day") ? day : null;
  panel.contains = node => node === panel || node === day;
  const error = control({ hidden: true });
  const label = control();
  const classes = new Set();
  const selectors = {
    "input[type=date]": native,
    "[data-invoice-date-proxy]": proxy,
    "[data-picker-trigger]": trigger,
    "[data-picker-display]": display,
    "[data-picker-popover]": panel,
    "[data-invoice-date-error]": error,
    label,
  };
  const root = {
    dataset: {},
    classList: {
      toggle(name, enabled) { if (enabled) classes.add(name); else classes.delete(name); },
      contains: name => classes.has(name),
    },
    querySelector(selector) {
      assert.ok(Object.hasOwn(selectors, selector), `Unexpected root selector: ${selector}`);
      return selectors[selector];
    },
  };
  const form = target({
    querySelectorAll(selector) {
      assert.equal(selector, "[data-invoice-date]");
      return [root];
    },
    querySelector(selector) {
      assert.equal(selector, ":invalid");
      return native.validity.valid ? null : native;
    },
  });
  root.parentElement = form;
  document.querySelector = selector => {
    assert.equal(selector, ".r1-admin-invoice-create .invoice-preview-filter");
    return form;
  };
  const media = target({ matches: desktop });
  let initializations = 0;
  const window = {
    matchMedia(query) {
      assert.equal(query, "(min-width: 761px) and (hover: hover) and (pointer: fine)");
      return media;
    },
  };
  if (engine) window.initDateTimePickers = scope => {
    assert.equal(scope, form);
    initializations += 1;
    trigger.addEventListener("click", () => {
      panel.hidden = trigger.getAttribute("aria-expanded") === "true";
      trigger.setAttribute("aria-expanded", String(!panel.hidden));
    });
  };
  vm.runInNewContext(source, { window, document, Event: MockEvent, setTimeout }, { filename });
  return {
    native, proxy, trigger, display, panel, day, error, label, root, form, document,
    initializations: () => initializations,
    setDesktop(matches) { media.matches = matches; media.fire("change"); },
  };
}

test("pristine empty required dates are not marked aria-invalid before validation", () => {
  const h = setup();
  assert.equal(h.native.validity.valid, false, "The named required field must still enforce native validation");
  assert.equal(h.trigger.getAttribute("aria-invalid"), "false");
  assert.equal(h.error.hidden, true);
  assert.equal(h.error.textContent, "");
  assert.equal(h.document.activeElement, null);
});

test("a desktop invalid attempt exposes the native message and focuses the visible trigger", () => {
  const h = setup();
  const event = h.native.fire("invalid");
  assert.equal(event.defaultPrevented, true);
  assert.equal(h.trigger.getAttribute("aria-invalid"), "true");
  assert.equal(h.error.hidden, false);
  assert.equal(h.error.textContent, h.native.validationMessage);
  assert.equal(h.document.activeElement, h.trigger);
});

test("correcting a client-invalid date clears its invalid state and message", () => {
  const h = setup();
  h.native.fire("invalid");
  h.native.value = "2026-10-17";
  h.native.fire("input");
  assert.equal(h.trigger.getAttribute("aria-invalid"), "false");
  assert.equal(h.error.hidden, true);
  assert.equal(h.error.textContent, "");
  assert.equal(h.proxy.value, "2026-10-17");
  assert.equal(h.display.textContent, "17/10/2026");
});

test("a server-bound date error retains aria-invalid and its error association", () => {
  const h = setup({ boundInvalid: true, value: "2026-10-17" });
  assert.equal(h.native.validity.valid, true);
  assert.equal(h.trigger.getAttribute("aria-invalid"), "true");
  assert.match(h.trigger.getAttribute("aria-describedby"), /\bid_period_start_error\b/);
  h.native.fire("change");
  assert.equal(h.trigger.getAttribute("aria-invalid"), "true");
});

test("calendar proxy roundtrips through the sole named native date and emits input/change", () => {
  const h = setup({ value: "2026-10-01" });
  assert.equal(h.proxy.value, "2026-10-01");
  assert.equal(h.proxy.name, undefined);
  h.proxy.value = "2026-10-24";
  h.proxy.fire("change");
  assert.equal(h.native.value, "2026-10-24");
  assert.equal(h.native.name, "period_start");
  assert.equal(h.native.required, true);
  assert.equal(h.native.disabled, false);
  assert.deepEqual(h.native.events.map(event => [event.type, event.bubbles]), [["input", true], ["change", true]]);
  assert.equal(h.display.textContent, "24/10/2026");
  assert.equal(h.document.activeElement, h.trigger);
});

test("touch fallback retains native focusability and browser validation without initializing a calendar", () => {
  const h = setup({ desktop: false });
  assert.equal(h.initializations(), 0);
  assert.equal(h.native.tabIndex, 0);
  assert.equal(h.native.getAttribute("aria-hidden"), "false");
  assert.equal(h.native.name, "period_start");
  assert.equal(h.native.required, true);
  assert.equal(h.trigger.hidden, true);
  assert.equal(h.root.classList.contains("is-enhanced"), false);
  assert.equal(h.native.fire("invalid").defaultPrevented, false);
  assert.equal(h.error.hidden, true);
  assert.equal(h.document.activeElement, null);
});

test("switching to touch closes the open calendar and restores the native field without duplicate initialization", () => {
  const h = setup({ value: "2026-10-17" });
  h.trigger.click();
  assert.equal(h.panel.hidden, false);
  assert.equal(h.document.activeElement, h.day);
  h.setDesktop(false);
  assert.equal(h.panel.hidden, true);
  assert.equal(h.trigger.hidden, true);
  assert.equal(h.native.tabIndex, 0);
  assert.equal(h.native.getAttribute("aria-hidden"), "false");
  h.setDesktop(true);
  assert.equal(h.initializations(), 1);
  assert.equal(h.native.tabIndex, -1);
  assert.equal(h.trigger.hidden, false);
});

test("a missing shared picker engine leaves the native date untouched", () => {
  const h = setup({ engine: false, value: "2026-10-17" });
  assert.equal(h.native.value, "2026-10-17");
  assert.equal(h.native.tabIndex, 0);
  assert.equal(h.native.getAttribute("aria-hidden"), null);
  assert.equal(h.native.disabled, false);
  assert.equal(h.native.required, true);
  assert.equal(h.trigger.hidden, true);
  assert.equal(h.root.classList.contains("is-enhanced"), false);
});
