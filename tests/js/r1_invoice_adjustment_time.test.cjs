const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const filename = path.resolve(__dirname, "../../static/js/r1_invoice_adjustment_time.js");
const source = readFileSync(filename, "utf8");

class MockEvent {
  constructor(type, options = {}) {
    Object.assign(this, { type, bubbles: false, defaultPrevented: false }, options);
  }
  preventDefault() { this.defaultPrevented = true; }
  stopPropagation() { this.propagationStopped = true; }
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
      if (event.bubbles && !event.propagationStopped) this.parentElement?.dispatchEvent(event);
      return !event.defaultPrevented;
    },
    fire(type, options = {}) {
      const event = new MockEvent(type, options);
      this.dispatchEvent(event);
      return event;
    },
  }, properties);
}

// Stub only the adapter's fixed DOM surface; billing rules and browser layout
// are not simulated. Run the real adapter and inspect its generated controls.
function setup({ desktop = true, supported = true, value = "09:17", boundInvalid = false,
  describedBy = null, tabIndex = null, ariaHidden = null } = {}) {
  const document = target({ activeElement: null, documentElement: { clientWidth: 1280 } });
  const created = [];
  function element(tagName, properties = {}) {
    const attrs = {};
    const classes = new Set();
    const node = Object.assign(target(), {
      tagName, attrs, children: [], dataset: {}, style: {}, options: [],
      hidden: false, disabled: false, value: "", textContent: "",
      classList: {
        add(name) { classes.add(name); },
        toggle(name, enabled) { if (enabled) classes.add(name); else classes.delete(name); },
        contains: name => classes.has(name),
      },
      setAttribute(name, value) { attrs[name] = String(value); },
      getAttribute(name) { return Object.hasOwn(attrs, name) ? attrs[name] : null; },
      removeAttribute(name) { delete attrs[name]; },
      append(...children) {
        for (const child of children) { child.parentElement = this; this.children.push(child); }
      },
      add(option) { this.options.push(option); },
      contains(node) { return node === this || this.children.some(child => child.contains(node)); },
      focus() { document.activeElement = this; this.fire("focus"); },
      click() { this.fire("click"); },
      getClientRects() { return this.hidden ? [] : [this.getBoundingClientRect()]; },
      getBoundingClientRect() { return { left: 700, right: 980, top: 200, bottom: 240, width: 272, height: 160 }; },
    }, properties);
    Object.defineProperties(node, {
      name: { get: () => attrs.name || "", set: value => { attrs.name = String(value); } },
      tabIndex: {
        get: () => attrs.tabindex === undefined ? 0 : Number(attrs.tabindex),
        set: value => { attrs.tabindex = String(value); },
      },
      form: { get() {
        let parent = this.parentElement;
        while (parent && parent.tagName !== "form") parent = parent.parentElement;
        return parent || null;
      } },
    });
    return node;
  }
  const shell = element("main");
  const form = element("form");
  const drawer = element("dialog", { open: true });
  if (supported) drawer.showModal = () => {};
  const root = element("div");
  const label = element("label", { textContent: "Actual start:" });
  const native = element("input", { type: "time", required: true, value });
  native.name = "log-7-actual_start_time";
  if (tabIndex !== null) native.setAttribute("tabindex", tabIndex);
  if (ariaHidden !== null) native.setAttribute("aria-hidden", ariaHidden);
  if (describedBy !== null) native.setAttribute("aria-describedby", describedBy);
  if (boundInvalid) native.setAttribute("aria-invalid", "true");
  Object.defineProperty(native, "validity", {
    get: () => ({ valid: native.disabled || !native.required || native.value !== "" }),
  });
  shell.append(form);
  form.append(drawer);
  drawer.append(root);
  root.append(label, native);
  root.querySelector = selector => {
    assert.equal(selector, "label");
    return label;
  };
  form.querySelector = selector => {
    assert.equal(selector, ":invalid");
    return native.validity.valid ? null : native;
  };
  drawer.querySelector = selector => {
    assert.ok(["header", "footer"].includes(selector), `Unexpected drawer selector: ${selector}`);
    return { getBoundingClientRect: () => ({ bottom: 100, top: 700 }) };
  };
  shell.querySelector = selector => {
    assert.equal(selector, "[data-billing-drawer]");
    return drawer;
  };
  shell.querySelectorAll = selector => {
    assert.equal(selector, "[data-billing-time-fields] input[type=time]");
    return [native];
  };
  document.querySelector = selector => {
    assert.equal(selector, ".r1-admin-invoice-create");
    return shell;
  };
  document.createElement = tagName => {
    const node = element(tagName);
    created.push(node);
    return node;
  };
  const media = target({ matches: desktop });
  const window = target({
    innerHeight: 800,
    matchMedia(query) {
      assert.equal(query, "(min-width: 761px) and (hover: hover) and (pointer: fine)");
      return media;
    },
  });
  vm.runInNewContext(source, {
    window, document, Event: MockEvent, setTimeout,
    Option: function (text, value) { Object.assign(this, { text, value }); },
    MutationObserver: class { observe() {} },
  }, { filename });
  const byClass = className => created.find(node => node.className === className);
  return {
    native, root, label, form, drawer, shell, document, created,
    trigger: byClass("r1-invoice-time-trigger"), panel: byClass("r1-invoice-time-panel"),
    apply: byClass("r1-invoice-time-apply"), cancel: byClass("r1-invoice-time-cancel"),
    parts: Object.fromEntries(created.filter(node => node.dataset.r1TimePart)
      .map(node => [node.dataset.r1TimePart, node])),
    setDesktop(matches) { media.matches = matches; media.fire("change"); },
  };
}

test("missing dialog capability leaves the native time completely unenhanced", () => {
  const h = setup({ supported: false });
  assert.equal(h.created.length, 0);
  assert.equal(h.root.classList.contains("r1-invoice-time"), false);
  assert.equal(h.native.getAttribute("aria-hidden"), null);
  assert.equal(h.native.getAttribute("tabindex"), null);
  assert.equal(h.native.value, "09:17");
  assert.equal(h.native.name, "log-7-actual_start_time");
  assert.equal(h.native.required, true);
  assert.equal(h.native.disabled, false);
  assert.equal(h.native.fire("invalid").defaultPrevented, false);
});

test("the visible trigger preserves all bound error descriptions and server invalid state", () => {
  const describedBy = "id_log-7-actual_start_time_error id_log-7-actual_start_time_helptext";
  const h = setup({ boundInvalid: true, describedBy });
  assert.equal(h.native.validity.valid, true);
  assert.equal(h.native.getAttribute("aria-hidden"), "true");
  assert.equal(h.native.getAttribute("aria-describedby"), describedBy);
  assert.equal(h.trigger.getAttribute("aria-describedby"), describedBy);
  assert.equal(h.trigger.getAttribute("aria-invalid"), "true");
  h.native.fire("change", { bubbles: true });
  assert.equal(h.trigger.getAttribute("aria-invalid"), "true");
  assert.equal(h.trigger.getAttribute("aria-describedby"), describedBy);
});

test("the desktop minute picker offers and preserves every minute from 00 through 59", () => {
  const h = setup();
  const minutes = Array.from({ length: 60 }, (_, index) => String(index).padStart(2, "0"));
  assert.deepEqual(h.parts.minute.options.map(option => option.value), minutes);
  assert.deepEqual(h.parts.minute.options.map(option => option.text), minutes);
  for (const minute of minutes) {
    h.trigger.click();
    h.parts.minute.value = minute;
    h.apply.click();
    assert.equal(h.native.value, `09:${minute}`);
    assert.equal(h.trigger.textContent, `09:${minute} AM`);
  }
});

test("opening and applying preserves an existing non-five-minute time exactly", () => {
  const h = setup({ value: "09:17" });
  h.trigger.click();
  assert.equal(h.panel.hidden, false);
  assert.equal(h.parts.hour.value, "09");
  assert.equal(h.parts.minute.value, "17");
  assert.equal(h.parts.period.value, "AM");
  h.apply.click();
  assert.equal(h.native.value, "09:17");
  assert.equal(h.trigger.textContent, "09:17 AM");
  assert.equal(h.panel.hidden, true);
});

test("applying an arbitrary minute updates only the named native value with input/change", () => {
  const h = setup();
  h.trigger.click();
  h.parts.hour.value = "11";
  h.parts.minute.value = "43";
  h.parts.period.value = "PM";
  h.apply.click();
  assert.equal(h.native.value, "23:43");
  assert.equal(h.trigger.textContent, "11:43 PM");
  assert.deepEqual(h.native.events.map(event => [event.type, event.bubbles]), [["input", true], ["change", true]]);
  assert.equal(h.trigger.getAttribute("aria-expanded"), "false");
  assert.equal(h.document.activeElement, h.trigger);
});

for (const [value, hour, period, display] of [
  ["00:07", "12", "AM", "12:07 AM"],
  ["12:17", "12", "PM", "12:17 PM"],
]) {
  test(`${value} roundtrips correctly as ${display}`, () => {
    const h = setup({ value });
    assert.equal(h.trigger.textContent, display);
    h.trigger.click();
    assert.equal(h.parts.hour.value, hour);
    assert.equal(h.parts.minute.value, value.slice(3));
    assert.equal(h.parts.period.value, period);
    h.apply.click();
    assert.equal(h.native.value, value);
    assert.equal(h.trigger.textContent, display);
  });
}

test("canceling a pending picker selection does not change native values or emit changes", () => {
  const h = setup();
  h.trigger.click();
  h.parts.minute.value = "49";
  h.cancel.click();
  assert.equal(h.native.value, "09:17");
  assert.deepEqual(h.native.events, []);
  assert.equal(h.panel.hidden, true);
  assert.equal(h.document.activeElement, h.trigger);
  h.trigger.click();
  assert.equal(h.parts.minute.value, "17");
});

test("touch fallback leaves native focus and validation available", () => {
  const h = setup({ desktop: false });
  assert.equal(h.root.classList.contains("is-enhanced"), false);
  assert.equal(h.native.getAttribute("tabindex"), null);
  assert.equal(h.native.getAttribute("aria-hidden"), null);
  assert.equal(h.trigger.hidden, true);
  assert.equal(h.panel.hidden, true);
  h.native.value = "";
  assert.equal(h.native.validity.valid, false);
  assert.equal(h.native.fire("invalid").defaultPrevented, false);
  h.native.focus();
  assert.equal(h.document.activeElement, h.native);
});

test("switching to touch closes the picker and restores original native attributes", () => {
  const h = setup({ tabIndex: "2", ariaHidden: "false" });
  h.trigger.click();
  assert.equal(h.panel.hidden, false);
  assert.equal(h.native.tabIndex, -1);
  h.setDesktop(false);
  assert.equal(h.panel.hidden, true);
  assert.equal(h.trigger.hidden, true);
  assert.equal(h.trigger.getAttribute("aria-expanded"), "false");
  assert.equal(h.native.getAttribute("tabindex"), "2");
  assert.equal(h.native.getAttribute("aria-hidden"), "false");
  assert.equal(h.native.value, "09:17");
  h.setDesktop(true);
  assert.equal(h.native.tabIndex, -1);
  assert.equal(h.trigger.hidden, false);
  assert.equal(h.panel.hidden, true);
});

test("picker controls add no named fields and retain original native form ownership", () => {
  const h = setup();
  h.trigger.click();
  h.apply.click();
  h.setDesktop(false);
  h.setDesktop(true);
  const namedControls = [h.native, ...h.created].filter(node =>
    ["input", "select", "textarea"].includes(node.tagName) && node.name);
  assert.deepEqual(namedControls, [h.native]);
  assert.equal(h.native.name, "log-7-actual_start_time");
  assert.equal(h.native.type, "time");
  assert.equal(h.native.parentElement, h.root);
  assert.equal(h.native.form, h.form);
  assert.equal(h.native.required, true);
  assert.equal(h.native.disabled, false);
  assert.equal(h.native.getAttribute("form"), null);
  for (const node of h.created.filter(node => ["button", "select"].includes(node.tagName))) {
    assert.equal(node.name, "");
    assert.equal(node.getAttribute("name"), null);
    assert.equal(node.form, h.form);
    if (node.tagName === "button") assert.equal(node.type, "button");
  }
});
