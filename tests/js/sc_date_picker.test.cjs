const assert = require("node:assert/strict");
const { readFileSync, existsSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const filename = path.resolve(__dirname, "../../static/js/sc_date_picker.js");
const source = existsSync(filename) ? readFileSync(filename, "utf8") : "";

function target() {
  const listeners = new Map();
  return {
    addEventListener(name, handler) {
      if (!listeners.has(name)) listeners.set(name, []);
      listeners.get(name).push(handler);
    },
    fire(name, event = {}) { for (const handler of listeners.get(name) || []) handler(event); },
  };
}

function rectangle(left, top, width, height) {
  return { left, top, width, height, right: left + width, bottom: top + height };
}

function setup({ enabled = true, top = 160, left = 32, width = 390, height = 844 } = {}) {
  const frames = new Map();
  const observers = [];
  let frameId = 0;
  const window = Object.assign(target(), { innerWidth: width, innerHeight: height });
  window.visualViewport = Object.assign(target(), { offsetTop: 0, offsetLeft: 0, width, height });
  const trigger = Object.assign(target(), {
    rect: rectangle(left, top, 300, 44), closes: 0,
    getBoundingClientRect() { return this.rect; },
    click() { popover.hidden = true; this.closes += 1; picker.fire("click"); },
  });
  const popover = {
    hidden: true, style: {}, naturalHeight: 288,
    contains(element) { return element === this; },
    getBoundingClientRect() {
      const heightLimit = parseFloat(this.style.maxHeight);
      return rectangle(parseFloat(this.style.left) || 0, parseFloat(this.style.top) || 0,
        parseFloat(this.style.width) || 292,
        Number.isNaN(heightLimit) ? this.naturalHeight : Math.min(heightLimit, this.naturalHeight));
    },
  };
  const header = { getBoundingClientRect: () => rectangle(0, 0, window.innerWidth, 64) };
  const nav = { getBoundingClientRect: () => rectangle(0, window.innerHeight - 67, window.innerWidth, 67) };
  const picker = Object.assign(target(), {
    querySelector(selector) {
      return selector === "[data-picker-trigger]" ? trigger :
        selector === "[data-picker-popover]" ? popover : null;
    },
  });
  const document = {
    documentElement: { clientWidth: width },
    querySelectorAll(selector) {
      assert.equal(selector, '.sc-log-form [data-date-time-picker="date"]');
      return enabled ? [picker] : [];
    },
    querySelector(selector) {
      return selector === ".worker-mobile-header" ? header :
        selector === ".worker-bottom-nav" ? nav : null;
    },
  };
  vm.runInNewContext(source, {
    window, document,
    getComputedStyle: () => ({ position: "fixed", display: "block", visibility: "visible" }),
    requestAnimationFrame(callback) { frames.set(++frameId, callback); return frameId; },
    ResizeObserver: class {
      constructor(callback) { observers.push(callback); }
      observe() {}
    },
  });
  function flush() {
    for (let count = 0; frames.size && count < 20; count += 1) {
      const pending = [...frames.values()];
      frames.clear();
      for (const callback of pending) callback();
    }
    assert.equal(frames.size, 0, "Placement must settle without an animation loop");
  }
  return {
    window, trigger, popover, picker, flush,
    open() { popover.hidden = false; picker.fire("click"); flush(); },
    resizeContent() { for (const callback of observers) callback(); flush(); },
  };
}

test("opens directly below the SC date trigger", () => {
  const h = setup(); h.open();
  assert.equal(h.popover.style.top, "210px");
  assert.equal(h.popover.style.left, "32px");
});

test("flips above when below cannot fit", () => {
  const h = setup({ top: 600 }); h.open();
  assert.equal(h.popover.style.top, "306px");
});

test("keeps a right-edge calendar inside the viewport", () => {
  const h = setup({ left: 320 }); h.open();
  assert.equal(h.popover.style.left, "90px");
});

test("tracks scrolling while the trigger remains visible", () => {
  const h = setup(); h.open();
  h.trigger.rect = rectangle(32, 110, 300, 44);
  h.window.fire("scroll"); h.flush();
  assert.equal(h.popover.style.top, "160px");
});

test("closes through the existing picker when trigger is behind the fixed header", () => {
  const h = setup(); h.open();
  h.trigger.rect = rectangle(32, 5, 300, 44);
  h.window.fire("scroll"); h.flush();
  assert.equal(h.trigger.closes, 1);
  assert.equal(h.popover.hidden, true);
});

test("constrains height instead of covering fixed navigation", () => {
  const h = setup({ top: 220, height: 450 }); h.open();
  const r = h.popover.getBoundingClientRect();
  assert.equal(h.popover.style.maxHeight, "142px");
  assert.equal(r.top, 72);
  assert.ok(r.bottom < 450 - 67);
});

test("repositions when a longer calendar month changes its height", () => {
  const h = setup({ top: 420 }); h.open();
  assert.equal(h.popover.style.top, "470px");
  h.popover.naturalHeight = 320; h.resizeContent();
  assert.equal(h.popover.style.top, "94px");
});

test("honors the visual viewport when a mobile keyboard reduces space", () => {
  const h = setup({ top: 350 }); h.open();
  h.window.visualViewport.offsetTop = 80;
  h.window.visualViewport.height = 450;
  h.window.visualViewport.fire("resize"); h.flush();
  assert.equal(h.popover.style.top, "88px");
  assert.equal(h.popover.style.maxHeight, "256px");
});

test("does not initialize shared pickers outside SC forms", () => {
  const h = setup({ enabled: false }); h.open();
  assert.equal(h.popover.style.top, undefined);
  h.window.fire("scroll"); h.flush();
  assert.equal(h.trigger.closes, 0);
});

test("does not reposition an already dismissed calendar", () => {
  const h = setup(); h.open(); h.popover.hidden = true;
  h.trigger.rect = rectangle(32, 110, 300, 44);
  h.window.fire("scroll"); h.flush();
  assert.equal(h.popover.style.top, "210px");
});
