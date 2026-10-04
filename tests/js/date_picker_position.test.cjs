const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = readFileSync(path.resolve(__dirname, "../../static/js/date_time_picker.js"), "utf8");

function target() {
  const listeners = new Map();
  return {
    addEventListener(name, handler) {
      if (!listeners.has(name)) listeners.set(name, []);
      listeners.get(name).push(handler);
    },
    fire(name, event = {}) { for (const handler of listeners.get(name) || []) handler({ type: name, ...event }); },
  };
}

function element() {
  const classes = new Set();
  return Object.assign(target(), {
    children: [], attrs: {}, style: {}, dataset: {}, isConnected: true, nodeType: 1,
    classList: {
      add: name => classes.add(name), remove: name => classes.delete(name),
      contains: name => classes.has(name),
      toggle(name, on) { if (on) classes.add(name); else classes.delete(name); },
    },
    setAttribute(name, value) { this.attrs[name] = value; },
    getAttribute(name) { return this.attrs[name] || null; },
    append(child) { this.children.push(child); },
    replaceChildren() { this.children = []; },
    contains(node) {
      if (node && !node.nodeType) throw new TypeError("contains requires a DOM node");
      return node === this || this.children.some(child => child.contains(node));
    },
    click() { this.fire("click", { target: this }); },
    querySelectorAll() { return this.children; },
    scrollTo() {},
  });
}

function rectangle(left, top, width, height) {
  return { left, top, width, height, right: left + width, bottom: top + height };
}

function fixture({ top = 160, left = 32, type = "date", modal = null } = {}) {
  const input = Object.assign(element(), {
    name: type === "date" ? "service_date" : "start_time", value: "", events: [],
    dispatchEvent(event) { this.events.push(event.type); },
  });
  const trigger = Object.assign(element(), {
    rect: rectangle(left, top, 300, 44),
    getBoundingClientRect() { return this.rect; },
    closest(selector) { return selector === ".shift-modal-body" ? modal : null; },
  });
  const popover = Object.assign(element(), {
    hidden: true, naturalHeight: 288,
    getBoundingClientRect() {
      const limit = parseFloat(this.style.maxHeight);
      return rectangle(parseFloat(this.style.left) || 0, parseFloat(this.style.top) || 0,
        parseFloat(this.style.width) || 292,
        Number.isNaN(limit) ? this.naturalHeight : Math.min(limit, this.naturalHeight));
    },
  });
  const selectors = {
    "input[type='hidden']": input, "[data-picker-trigger]": trigger, "[data-picker-popover]": popover,
  };
  for (const key of ["picker-display", "calendar-title", "calendar-grid", "calendar-previous", "calendar-next", "calendar-today", "calendar-clear", "time-cancel", "time-apply"]) {
    selectors[`[data-${key}]`] = element();
  }
  for (const part of ["hour", "minute", "period"]) selectors[`[data-wheel-part="${part}"]`] = element();
  const picker = Object.assign(element(), {
    dataset: { dateTimePicker: type },
    querySelector: selector => selectors[selector] || null,
    hasAttribute: () => false,
    closest: () => null,
  });
  picker.children = Object.values(selectors);
  popover.parentElement = picker;
  return { picker, input, trigger, popover, controls: selectors };
}

function setup(options = {}) {
  const { width = 390, height = 844, navigation = true } = options;
  const frames = new Map(), observers = [];
  let frameId = 0;
  const h = fixture(options), pickers = [h.picker];
  const window = Object.assign(target(), { innerWidth: width, innerHeight: height });
  window.visualViewport = Object.assign(target(), { offsetTop: 0, offsetLeft: 0, width, height });
  const header = { getBoundingClientRect: () => rectangle(0, 0, width, 64) };
  const nav = { getBoundingClientRect: () => rectangle(0, height - 67, width, 67) };
  const document = Object.assign(target(), {
    readyState: "complete", documentElement: { clientWidth: width },
    createElement: element,
    querySelectorAll: () => pickers.filter(picker => !picker.dataset.pickerInitialized),
    querySelector(selector) {
      if (selector === ".admin-mobile-header") return navigation ? null : header;
      if (!navigation) return null;
      return selector === ".worker-mobile-header" ? header : selector === ".worker-bottom-nav" ? nav : null;
    },
  });
  vm.runInNewContext(source, {
    window, document, Event, setTimeout, clearTimeout,
    getComputedStyle: () => ({ position: "fixed", display: "block", visibility: "visible" }),
    requestAnimationFrame(callback) { frames.set(++frameId, callback); return frameId; },
    cancelAnimationFrame(id) { frames.delete(id); },
    ResizeObserver: class {
      constructor(callback) { this.callback = callback; this.connected = true; observers.push(this); }
      observe() {}
      disconnect() { this.connected = false; }
    },
  });
  function flush() {
    for (let count = 0; frames.size && count < 20; count += 1) {
      const pending = [...frames.values()]; frames.clear();
      for (const callback of pending) callback();
    }
    assert.equal(frames.size, 0, "Placement must settle without an animation loop");
  }
  return Object.assign(h, {
    window, document, observers, flush,
    open() { h.trigger.click(); flush(); },
    resizeContent() { for (const observer of observers) if (observer.connected) observer.callback(); flush(); },
    add(options) {
      const extra = fixture(options); pickers.push(extra.picker);
      window.initDateTimePickers({ querySelectorAll: () => extra.picker.dataset.pickerInitialized ? [] : [extra.picker] });
      return extra;
    },
  });
}

test("shared calendars open 6px below the trigger outside SC forms", () => {
  const h = setup(); h.open();
  assert.equal(h.popover.style.top, "210px");
  assert.equal(h.popover.style.left, "32px");
  assert.equal(h.input.value, "");
  assert.deepEqual(h.input.events, []);
});

test("flips above when below cannot fit", () => {
  const h = setup({ top: 600 }); h.open();
  assert.equal(h.popover.style.top, "306px");
});

test("keeps a right-edge calendar inside the viewport", () => {
  const h = setup({ left: 320 }); h.open();
  assert.equal(h.popover.style.left, "90px");
});

test("tracks page scrolling and ignores calendar-internal scrolling", () => {
  const h = setup(); h.open();
  h.trigger.rect = rectangle(32, 110, 300, 44);
  h.window.fire("scroll", { target: h.popover }); h.flush();
  assert.equal(h.popover.style.top, "210px");
  h.window.fire("scroll"); h.flush();
  assert.equal(h.popover.style.top, "160px");
});

test("closes consistently when the trigger moves behind a fixed header", () => {
  for (const navigation of [true, false]) {
    const h = setup({ navigation }); h.open();
    h.trigger.rect = rectangle(32, 5, 300, 44);
    h.window.fire("scroll"); h.flush();
    assert.equal(h.popover.hidden, true);
    assert.equal(h.trigger.attrs["aria-expanded"], "false");
  }
});

test("constrains height instead of covering fixed bottom navigation", () => {
  const h = setup({ top: 220, height: 450 }); h.open();
  assert.equal(h.popover.style.maxHeight, "142px");
  assert.equal(h.popover.style.top, "72px");
});

test("repositions when month or holiday content increases calendar height", () => {
  const h = setup({ top: 420 }); h.open();
  assert.equal(h.popover.style.top, "470px");
  h.popover.naturalHeight = 350; h.resizeContent();
  assert.equal(h.popover.style.top, "72px");
});

test("honors the visual viewport when the keyboard reduces available space", () => {
  const h = setup({ top: 350 }); h.open();
  h.window.visualViewport.offsetTop = 80; h.window.visualViewport.height = 450;
  h.window.visualViewport.fire("resize"); h.flush();
  assert.equal(h.popover.style.top, "88px");
  assert.equal(h.popover.style.maxHeight, "256px");
  h.window.visualViewport.fire("scroll", { target: h.window.visualViewport }); h.flush();
  assert.equal(h.popover.hidden, false);
});

test("dynamically initialized modal dates stay within the modal scroll body", () => {
  const h = setup();
  const modal = { nodeType: 1, getBoundingClientRect: () => rectangle(20, 100, 350, 500) };
  const extra = h.add({ top: 450, left: 30, modal });
  extra.trigger.click(); h.flush();
  assert.equal(extra.popover.style.top, "156px");
  assert.equal(extra.popover.style.left, "30px");
  extra.trigger.rect = rectangle(30, 80, 300, 20);
  h.window.fire("scroll", { target: modal }); h.flush();
  assert.equal(extra.popover.hidden, true);
});

test("removed modal calendars release their active placement observer", () => {
  const h = setup(); h.open();
  h.trigger.isConnected = false; h.popover.isConnected = false;
  h.resizeContent();
  assert.equal(h.popover.hidden, true);
  assert.ok(h.observers.every(observer => !observer.connected));
});

test("Escape and outside clicks close calendars and stop placement", () => {
  const h = setup(); h.open();
  h.window.fire("resize");
  h.document.fire("keydown", { key: "Escape" }); h.flush();
  assert.equal(h.popover.hidden, true);
  assert.ok(h.observers.every(observer => !observer.connected));
  h.open(); h.document.fire("click", { target: element() });
  assert.equal(h.popover.hidden, true);
});

test("reinitialization does not attach duplicate trigger handlers", () => {
  const h = setup(); h.window.initDateTimePickers(h.document); h.open();
  assert.equal(h.popover.hidden, false);
  assert.equal(h.popover.style.top, "210px");
});

test("only the active calendar follows the viewport", () => {
  const h = setup(); h.open();
  const extra = h.add({ top: 200 }); extra.trigger.click(); h.flush();
  h.trigger.rect = rectangle(32, 110, 300, 44);
  h.window.fire("scroll"); h.flush();
  assert.equal(h.popover.hidden, true);
  assert.equal(h.popover.style.top, "210px");
  assert.equal(extra.popover.style.top, "250px");
});

test("date selection, Clear and Today preserve existing values and events", () => {
  const h = setup(); h.input.value = "2026-10-04"; h.open();
  const fifth = h.controls["[data-calendar-grid]"].children.find(button => button.attrs["aria-label"].includes("05 Oct 2026"));
  fifth.click();
  assert.equal(h.input.value, "2026-10-05");
  assert.deepEqual(h.input.events, ["input", "change"]);
  assert.equal(h.popover.hidden, true);
  h.open(); h.controls["[data-calendar-clear]"].click();
  assert.equal(h.input.value, "");
  h.open(); h.controls["[data-calendar-today]"].click();
  const now = new Date();
  assert.equal(h.input.value, `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`);
  assert.deepEqual(h.input.events, ["input", "change", "input", "change", "input", "change"]);
});

test("time pickers keep existing positioning and commit behavior", () => {
  const h = setup({ type: "time" }); h.open();
  assert.equal(h.popover.style.top, undefined);
  h.window.fire("resize"); h.window.fire("scroll"); h.flush();
  assert.equal(h.popover.style.top, undefined);
  assert.equal(h.observers.length, 0);
  h.controls["[data-time-apply]"].click();
  assert.equal(h.input.value, "09:00");
  assert.deepEqual(h.input.events, ["input", "change"]);
});

test("date to time to date switching cancels stale placement frames", () => {
  const h = setup(); h.open();
  h.window.fire("resize");
  const clock = h.add({ type: "time" }); clock.trigger.click(); h.flush();
  assert.equal(h.popover.hidden, true);
  assert.equal(clock.popover.hidden, false);
  assert.equal(clock.popover.style.top, undefined);
  assert.ok(h.observers.every(observer => !observer.connected));
  h.open();
  assert.equal(clock.popover.hidden, true);
  assert.equal(h.popover.style.top, "210px");
});

test("replacing modal content closes the old calendar on the next open", () => {
  const h = setup(); h.open(); h.window.fire("resize");
  h.trigger.isConnected = false; h.popover.isConnected = false;
  const replacement = h.add({ top: 200 }); replacement.trigger.click(); h.flush();
  assert.equal(h.popover.hidden, true);
  assert.equal(h.observers[0].connected, false);
  assert.equal(replacement.popover.style.top, "250px");
  assert.equal(replacement.popover.hidden, false);
});
