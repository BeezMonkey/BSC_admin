const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const filename = path.resolve(__dirname, "../../static/js/invoice_billing.js");
const source = readFileSync(filename, "utf8");
const namedControls = "input[name], select[name], textarea[name]";

class MockEvent {
  constructor(type, options = {}) {
    Object.assign(this, { type, bubbles: false, cancelable: true, defaultPrevented: false }, options);
  }
  preventDefault() { if (this.cancelable) this.defaultPrevented = true; }
}

// Tree-backed selectors and reparenting keep ownership assertions independent of
// the production controller's cached references. Only used DOM APIs are mocked.
function element(tag = "div", properties = {}) {
  const classes = new Set();
  let hidden = false;
  return Object.assign({
    tag, value: "", type: "", name: "", checked: false,
    get hidden() { return hidden; },
    set hidden(value) { hidden = Boolean(value); },
    disabled: false, required: false, open: false,
    dataset: {}, listeners: {}, children: [], parentElement: null,
    textContent: "", validationMessage: "", scrollTop: 0,
    classList: {
      add(name) { classes.add(name); },
      remove(name) { classes.delete(name); },
      contains(name) { return classes.has(name); },
    },
    get form() { return this.closest("form"); },
    hasAttribute(name) {
      if (name.startsWith("data-")) {
        const key = name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
        return Object.hasOwn(this.dataset, key);
      }
      return name === "name" && Boolean(this.name);
    },
    matches(selector) {
      const parts = selector.trim().split(/\s+/);
      const last = parts.pop();
      const match = last.match(/^([a-z]+)?(?:\[([\w-]+)(?:\$="([^"]*)")?\])?$/);
      let matches;
      if (last.startsWith(".")) matches = this.classList.contains(last.slice(1));
      else {
        assert.ok(match, `Unsupported mock selector: ${selector}`);
        matches = (!match[1] || this.tag === match[1]) && (!match[2] || (
          match[3] === undefined ? this.hasAttribute(match[2]) : String(this[match[2]]).endsWith(match[3])
        ));
      }
      if (!matches || !parts.length) return matches;
      for (let parent = this.parentElement; parent; parent = parent.parentElement) {
        if (parent.matches(parts.join(" "))) return true;
      }
      return false;
    },
    querySelectorAll(selector) {
      const selectors = selector.split(",").map(value => value.trim());
      const found = [];
      const visit = parent => parent.children.forEach(child => {
        if (selectors.some(value => child.matches(value))) found.push(child);
        visit(child);
      });
      visit(this);
      return found;
    },
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; },
    closest(selector) {
      for (let node = this; node; node = node.parentElement) {
        if (node.matches(selector)) return node;
      }
      return null;
    },
    appendChild(child) {
      if (child.parentElement) {
        const siblings = child.parentElement.children;
        siblings.splice(siblings.indexOf(child), 1);
      }
      this.children.push(child);
      child.parentElement = this;
      return child;
    },
    addEventListener(type, listener) { (this.listeners[type] ||= []).push(listener); },
    dispatchEvent(event) {
      event.target ||= this;
      event.currentTarget = this;
      for (const listener of this.listeners[event.type] || []) listener.call(this, event);
      this[`on${event.type}`]?.call(this, event);
      if (event.bubbles && this.parentElement) this.parentElement.dispatchEvent(event);
      return !event.defaultPrevented;
    },
    fire(type, options = {}) {
      const event = new MockEvent(type, options);
      this.dispatchEvent(event);
      return event;
    },
    focus() {
      let root = this;
      while (root.parentElement) root = root.parentElement;
      root.activeElement = this;
    },
    showModal() { this.open = true; },
    close() { this.open = false; },
    getBoundingClientRect() { return { left: 800 }; },
    setCustomValidity(message) { this.validationMessage = message; },
    reportValidity() {
      if (this.disabled || this.type === "hidden") return true;
      const missing = this.required && (this.type === "checkbox" ? !this.checked : !this.value);
      if (missing || this.validationMessage) {
        this.fire("invalid");
        return false;
      }
      return true;
    },
  }, properties);
}

function marked(parent, marker, tag = "div", properties = {}) {
  return parent.appendChild(element(tag, { ...properties, dataset: { [marker]: "" } }));
}

function setup(options = {}) {
  const { travelPrice = "1.00", rows: rowOptions = [options], dialogSupported = true } = options;
  const document = element("document");
  document.body = document.appendChild(element("body"));
  const table = document.body.appendChild(element("section"));
  table.classList.add("invoice-preview-table");
  const forms = [];
  const rows = rowOptions.map((config, index) => {
    const {
      originalKm = "0", category = "Self-care", item = "", km = "", claim = "",
      reason = "", other = "Checked with worker", errors = false, admin = true,
      originalHours = "2.50", originalPrice = "60.00", originalStart = "09:00",
      originalEnd = "11:30", originalBreak = "0", correctTime = false,
      start = originalStart, end = originalEnd, pause = originalBreak,
      formIndex = 0, withClaim = true,
    } = config;
    if (!forms[formIndex]) {
      forms[formIndex] = table.appendChild(element("form"));
      marked(forms[formIndex], "invoiceTotal", "span");
    }
    const form = forms[formIndex];
    const row = form.appendChild(element("tr", { dataset: {
      invoiceRow: "", hours: originalHours, price: originalPrice,
      originalItem: "1", originalCategory: category, originalKm, originalPrice,
      originalLabel: "Original item", originalHours, originalStart, originalEnd,
      originalBreak, originalName: "Original service", originalCode: "01_TEST", logId: String(index + 1), serviceDate: "04/10/2026", billingErrors: String(errors), ...(admin ? { billingRow: "" } : {}),
    } }));
    const f = {};
    for (const [key, marker] of Object.entries({
      rate: "billingRate", total: "billingTotal", hours: "billingHours",
      "item-label": "billingItemLabel", adjusted: "billingAdjusted", "km-summary": "billingKmSummary",
      "claim-home": "billingClaimHome", "claim-empty": "billingClaimEmpty",
    })) f[key] = marked(row, marker);
    if (withClaim) {
      f["claim-field"] = marked(f["claim-home"], "billingClaimField");
      f.claim = marked(f["claim-field"], "billingClaim").appendChild(element("input", {
        name: `travel-${index + 1}-amount`, type: "number", value: claim,
      }));
    }
    if (admin) {
      f.open = marked(row, "billingOpen", "button", { hidden: true });
      f.details = marked(row, "billingDetails", "details", { open: errors });
      f.fields = marked(f.details, "billingFields");
      function control(parent, key, name, tag, value, type = "") {
        f[key] = parent.appendChild(element(tag, { name: `adjustment-${index + 1}-${name}`, value, type }));
      }
      control(f.fields, "version", "source_version", "input", "2026-10-07T00:00:00+00:00", "hidden");
      control(f.fields, "toggle", "correct_time", "input", "on", "checkbox");
      f.toggle.checked = correctTime;
      f["time-fields"] = marked(f.fields, "billingTimeFields");
      control(f["time-fields"], "start", "actual_start_time", "input", start, "time");
      control(f["time-fields"], "end", "actual_end_time", "input", end, "time");
      control(f["time-fields"], "pause", "break_minutes", "input", pause, "number");
      control(marked(f.fields, "billingItem"), "item", "support_item", "select", item);
      f.item.options = [
        { value: "", textContent: "Keep original item", dataset: {} },
        { value: "1", textContent: "Original item", dataset: { price: originalPrice, category } },
        { value: "2", textContent: "Community item", dataset: { price: "80.25", category: "Community access" } },
        { value: "3", textContent: "Other item", dataset: { price: "90.00", category: "Self-care" } },
      ];
      Object.defineProperty(f.item, "selectedOptions", { get() { return this.options.filter(option => option.value === this.value); } });
      control(marked(f.fields, "billingKm"), "km", "kilometres", "input", km, "number");
      control(marked(f.fields, "billingReason"), "reason", "reason", "select", reason);
      f["other-field"] = marked(f.fields, "billingOtherField");
      control(marked(f["other-field"], "billingOther"), "other", "reason_details", "textarea", other);
      for (const [key, marker] of Object.entries({
        "reset-item": "billingResetItem", "drawer-claim": "billingDrawerClaim",
        "time-error": "billingTimeError", "claim-error": "billingClaimError",
        "hours-preview": "billingHoursPreview", "rate-preview": "billingRatePreview",
        "service-preview": "billingServicePreview",
        "edit-time": "billingEditTime", "restore-time": "billingRestoreTime",
        "time-summary": "billingTimeSummary", "current-time": "billingCurrentTime",
        "current-break": "billingCurrentBreak",
      })) f[key] = marked(f.fields, marker, key === "reset-item" ? "button" : "div");
    }
    return { fields: f, row, form };
  });
  const drawer = marked(document.body, "billingDrawer", "dialog");
  drawer.dataset.travelPrice = travelPrice;
  const ui = {};
  for (const name of ["body", "before", "after", "close", "cancel", "apply", "subtitle", "breakdown", "change-status"]) {
    ui[name] = marked(drawer, `drawer${name[0].toUpperCase()}${name.slice(1)}`.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase()));
  }
  const discard = marked(document.body, "billingDiscard", "dialog");
  ui.keep = marked(discard, "discardKeep", "button");
  ui.discard = marked(discard, "discardConfirm", "button");
  if (!dialogSupported) drawer.showModal = undefined;
  vm.runInNewContext(source, { document, Event: MockEvent }, { filename });
  return { document, drawer, discard, ui, forms, rows, ...rows[0] };
}

test("prototype time control edits and restores the same original time fields", () => {
  const state = setup();
  const { fields: f } = state;
  f.open.fire("click");
  f["edit-time"].fire("click");
  assert.equal(f.toggle.checked, true);
  assert.equal(f["time-summary"].hidden, true);
  change(f.end, "10:45");
  f["restore-time"].fire("click");
  assert.equal(f.toggle.checked, false);
  assert.equal(f.end.value, "11:30");
  assert.equal(f["time-summary"].hidden, false);
  assert.equal(f["current-time"].textContent, "9:00am - 11:30am");
});

test("prototype header and footer reflect active log and manual claim", () => {
  const { fields: f, ui } = setup({ originalKm: "25" });
  f.open.fire("click");
  assert.equal(ui.subtitle.textContent, "Log #1 | 04/10/2026");
  assert.equal(ui.apply.disabled, true);
  assert.equal(ui["change-status"].textContent, "No changes");
  change(f.claim, "20");
  assert.equal(ui.apply.disabled, false);
  assert.equal(ui.breakdown.textContent, "$150.00 service + $20.00 travel");
  assert.equal(ui["change-status"].textContent, "Unsaved changes");
});

function change(control, value, type = "input") {
  if (control.type === "checkbox") control.checked = value;
  else control.value = value;
  control.fire(type, { bubbles: true });
}

function posted(form) {
  return form.querySelectorAll(namedControls)
    .filter(control => !control.disabled && (control.type !== "checkbox" || control.checked))
    .map(control => [control.name, control.value]);
}

function postedValues(form, control) {
  return posted(form).filter(([name]) => name === control.name).map(([, value]) => value);
}

// Compare canonical displayed money in integer cents, without float rounding or
// reimplementing the production parser for the input formats under regression.
function displayedCents(text) {
  const match = text.match(/(?:^|\$)(\d+)\.(\d{2})$/);
  assert.ok(match, `Expected a two-decimal money display, got ${JSON.stringify(text)}`);
  return BigInt(match[1]) * 100n + BigInt(match[2]);
}

function assertTotals(state, expected) {
  assert.equal(displayedCents(state.fields.total.textContent), expected);
  assert.equal(displayedCents(state.row.dataset.lineTotal), expected);
  assert.equal(displayedCents(state.form.querySelector("[data-invoice-total]").textContent), expected);
  if (state.drawer.open) assert.equal(displayedCents(state.ui.after.textContent), expected);
}

test("ordinary admin rows keep km in the drawer fields and hide empty claims", () => {
  const { fields: f, row } = setup();
  assert.equal(f["claim-field"].hidden, true);
  assert.equal(f.claim.disabled, true);
  assert.equal(f.km.closest("[data-billing-fields]"), f.fields);
  assert.equal(f.fields.parentElement, f.details);
  assert.equal(f.reason.required, false);
  assert.equal(f.open.hidden, false);
  assert.equal(row.classList.contains("invoice-drawer-ready"), true);
});

test("original Community access retains claim access after selecting another item", () => {
  const { fields: f } = setup({ category: "Community access", item: "3" });
  assert.equal(f["claim-field"].hidden, false);
  assert.equal(f.claim.disabled, false);
  assert.equal(f.reason.required, true);
});

test("item selection previews service and combined totals without changing hours or claim", () => {
  const state = setup({ originalKm: "20", claim: "17.35" });
  const f = state.fields;
  change(f.item, "2", "change");
  assert.equal(f.rate.textContent, "80.25");
  assert.equal(f["service-preview"].textContent, "Service $200.63");
  assertTotals(state, 21798n);
  assert.equal(f["item-label"].textContent, "Community item");
  assert.equal(f.claim.value, "17.35");
  assert.equal(f.hours.textContent, "2.50");
  assert.equal(state.row.dataset.originalHours, "2.50");
  assert.equal(f.reason.required, true);
});

test("blank item restores original preview and is not an adjustment", () => {
  const state = setup({ item: "2" });
  change(state.fields.item, "", "change");
  assert.equal(state.fields.rate.textContent, "60.00");
  assertTotals(state, 15000n);
  assert.equal(state.fields.reason.required, false);
  assert.equal(state.fields.adjusted.hidden, true);
});

test("reset item restores the rate without clearing km or the manual claim", () => {
  const { fields: f } = setup({ item: "2", km: "20", claim: "15.50" });
  f["reset-item"].fire("click");
  assert.equal(f.item.value, "");
  assert.equal(f.rate.textContent, "60.00");
  assert.equal(f.km.value, "20");
  assert.equal(f.claim.value, "15.50");
  assert.equal(f.reason.required, true);
  assert.equal(f["reset-item"].hidden, true);
});

test("reset item is hidden until a different item is selected", () => {
  const { fields: f } = setup();
  assert.equal(f["reset-item"].hidden, true);
  change(f.item, "2", "change");
  assert.equal(f["reset-item"].hidden, false);
  f["reset-item"].fire("click");
  assert.equal(f.reason.required, false);
  assert.equal(f["reset-item"].hidden, true);
});

test("blank km carries recorded km but explicit zero requires a correction reason", () => {
  const { fields: f } = setup({ originalKm: "12.00" });
  assert.equal(f["km-summary"].textContent, "12.00");
  assert.equal(f.reason.required, false);
  assert.equal(f.claim.disabled, false);
  change(f.km, "0");
  assert.equal(f.reason.required, true);
  assert.equal(f["claim-field"].hidden, false);
  assert.equal(f["km-summary"].textContent, "0.00");
  change(f.km, "");
  assert.equal(f["km-summary"].textContent, "12.00");
  assert.equal(f.reason.required, false);
});

test("missing km correction enables the same claim control without deriving money", () => {
  const state = setup();
  const f = state.fields;
  f.open.fire("click");
  const originalClaim = f.claim;
  change(f.km, "4.5");
  assert.equal(f.claim.disabled, false);
  assert.equal(f["claim-field"].hidden, false);
  assert.equal(f.claim.value, "");
  assert.equal(f["drawer-claim"].querySelector("input"), originalClaim);
  assert.equal(f.reason.required, true);
  assertTotals(state, 15000n);
});

test("manual claim remains visible when switching away from Community access", () => {
  const { fields: f } = setup({ originalKm: "12", item: "2" });
  change(f.claim, "23.75");
  change(f.item, "3", "change");
  assert.equal(f["claim-field"].hidden, false);
  assert.equal(f.claim.disabled, false);
  assert.equal(f.claim.value, "23.75");
});

test("Other details are required only for Other and disabled while hidden", () => {
  const { fields: f } = setup({ item: "2", reason: "other" });
  assert.equal(f.other.required, true);
  assert.equal(f["other-field"].hidden, false);
  change(f.reason, "service_changed", "change");
  assert.equal(f["other-field"].hidden, true);
  assert.equal(f.other.disabled, true);
  assert.equal(f.other.required, false);
  change(f.reason, "other", "change");
  assert.equal(f.other.disabled, false);
  assert.equal(f.other.value, "Checked with worker");
});

test("numerically identical km and the original item are not changes", () => {
  const { fields: f } = setup({ originalKm: "12.00", km: "12", item: "1" });
  assert.equal(f.reason.required, false);
  assert.equal(f.rate.textContent, "60.00");
  assert.equal(f.adjusted.hidden, true);
});

test("reverting a change does not require leftover Other details", () => {
  const { fields: f } = setup({ item: "2", reason: "other", other: "" });
  change(f.item, "", "change");
  assert.equal(f.reason.required, false);
  assert.equal(f.other.required, false);
});

test("service preview uses originalHours and decimal half-up rounding", () => {
  const state = setup({ item: "2", originalHours: "1.50" });
  state.fields.item.options[2].dataset.price = "70.07";
  state.row.dataset.hours = "99.00";
  state.fields.item.fire("change");
  assert.equal(state.fields["service-preview"].textContent, "Service $105.11");
  assertTotals(state, 10511n);
});

test("Apply stages values and returns the same controls to their original homes", () => {
  const state = setup({ originalKm: "12", claim: "10" });
  const { fields: f, drawer, ui, form, document } = state;
  f.open.fire("click");
  assert.equal(drawer.parentElement, form);
  assert.equal(f.fields.parentElement, ui.body);
  assert.equal(f["claim-field"].parentElement, f["drawer-claim"]);
  assert.equal(document.activeElement, ui.close);
  assert.equal(ui.before.textContent, "$160.00");
  change(f.item, "2", "change");
  change(f.claim, "17.35");
  change(f.reason, "service_changed", "change");
  assertTotals(state, 21798n);
  let submissions = 0;
  form.addEventListener("submit", () => submissions++);
  ui.apply.fire("click");
  assert.equal(submissions, 0);
  assert.equal(drawer.open, false);
  assert.equal(f.fields.parentElement, f.details);
  assert.equal(f["claim-field"].parentElement, f["claim-home"]);
  assert.deepEqual(postedValues(form, f.claim), ["17.35"]);
  assert.deepEqual(postedValues(form, f.item), ["2"]);
  assert.equal(document.activeElement, f.open);
  assert.equal(document.body.classList.contains("invoice-drawer-open"), false);
  f.open.fire("click");
  assert.equal(ui.before.textContent, "$217.98");
  assert.equal(f.claim.value, "17.35");
});

test("discard restores all values and checkbox state from the latest opening", () => {
  const state = setup({ originalKm: "12", item: "2", claim: "10", reason: "service_changed" });
  const { fields: f, ui, drawer, discard, form } = state;
  const before = posted(form);
  f.open.fire("click");
  change(f.toggle, true, "change");
  change(f.end, "10:45");
  change(f.pause, "15");
  change(f.item, "3", "change");
  change(f.km, "20");
  change(f.claim, "15.50");
  change(f.reason, "other", "change");
  change(f.other, "Changed notes");
  ui.cancel.fire("click");
  assert.equal(discard.open, true);
  assert.equal(drawer.open, true);
  ui.keep.fire("click");
  assert.equal(discard.open, false);
  assert.equal(f.claim.value, "15.50");
  ui.close.fire("click");
  ui.discard.fire("click");
  assert.equal(drawer.open, false);
  assert.equal(discard.open, false);
  assert.equal(f.toggle.checked, false);
  assert.equal(f.end.value, "11:30");
  assert.equal(f.pause.value, "0");
  assert.equal(f.other.value, "Checked with worker");
  assert.deepEqual(posted(form), before);
  assertTotals(state, 21063n);
});

test("closing an unchanged drawer skips discard confirmation and restores focus", () => {
  const { fields: f, drawer, discard, ui, document } = setup();
  f.open.fire("click");
  ui.cancel.fire("click");
  assert.equal(drawer.open, false);
  assert.equal(discard.open, false);
  assert.equal(document.activeElement, f.open);
  assert.equal(f.claim.disabled, true);
});

test("shared drawer retains one named claim and correct ownership across participant forms", () => {
  const state = setup({ rows: [
    { originalKm: "12", claim: "10" },
    { originalKm: "20", claim: "25", formIndex: 1 },
  ] });
  const [first, second] = state.rows;
  for (const current of [first, second, first]) {
    const f = current.fields;
    f.open.fire("click");
    assert.equal(state.drawer.parentElement, current.form);
    assert.equal(f.claim.form, current.form);
    assert.equal(f.km.form, current.form);
    assert.equal(state.document.querySelectorAll(namedControls).filter(c => c.name === f.claim.name).length, 1);
    assert.deepEqual(postedValues(current.form, f.claim), [f.claim.value]);
    const other = current === first ? second : first;
    assert.deepEqual(postedValues(other.form, f.claim), []);
    assert.deepEqual(postedValues(other.form, other.fields.claim), [other.fields.claim.value]);
    state.ui.apply.fire("click");
    assert.equal(f.claim.form, current.form);
    assert.equal(f.fields.parentElement, f.details);
    assert.deepEqual(postedValues(current.form, f.claim), [f.claim.value]);
  }
  assert.equal(first.form.querySelector("[data-invoice-total]").textContent, "Invoice total: $160.00");
  assert.equal(second.form.querySelector("[data-invoice-total]").textContent, "Invoice total: $175.00");
});

test("invoice total includes each row once while its controls are in the drawer", () => {
  const state = setup({ rows: [{ originalKm: "12" }, { originalHours: "1.00" }] });
  state.fields.open.fire("click");
  change(state.fields.claim, "0.50");
  assert.equal(state.form.querySelector("[data-invoice-total]").textContent, "Invoice total: $210.50");
  assert.equal(state.ui.after.textContent, "$150.50");
});

test("form submission is prevented while a drawer is open, but allowed after Apply", () => {
  const { fields: f, form, ui } = setup();
  f.open.fire("click");
  assert.equal(form.fire("submit").defaultPrevented, true);
  ui.apply.fire("click");
  assert.equal(form.fire("submit").defaultPrevented, false);
});

test("Escape requests discard and Enter in an input cannot submit the invoice", () => {
  const { fields: f, drawer, discard, ui } = setup({ originalKm: "12" });
  f.open.fire("click");
  assert.equal(f.claim.fire("keydown", { key: "Enter", bubbles: true }).defaultPrevented, true);
  change(f.claim, "5");
  assert.equal(drawer.fire("cancel").defaultPrevented, true);
  assert.equal(drawer.open, true);
  assert.equal(discard.open, true);
  ui.discard.fire("click");
  assert.equal(drawer.open, false);
});

test("bound errors reopen the first affected drawer and retain posted values", () => {
  const state = setup({ rows: [{}, { errors: true, claim: "20", km: "0", item: "2" }] });
  const f = state.rows[1].fields;
  assert.equal(state.drawer.open, true);
  assert.equal(f.fields.parentElement, state.ui.body);
  assert.equal(state.rows[0].fields.fields.parentElement, state.rows[0].fields.details);
  assert.equal(f.claim.value, "20");
  assert.equal(f.km.value, "0");
  assert.equal(f.item.value, "2");
  assert.equal(f["claim-field"].hidden, false);
  assert.equal(f["claim-error"].hidden, false);
});

test("invalid controls reopen a closed drawer without stealing another open drawer", () => {
  const state = setup({ rows: [{ item: "2" }, { item: "3" }] });
  const [first, second] = state.rows;
  assert.equal(first.fields.reason.reportValidity(), false);
  assert.equal(state.drawer.open, true);
  assert.equal(first.fields.fields.parentElement, state.ui.body);
  second.fields.reason.reportValidity();
  assert.equal(first.fields.fields.parentElement, state.ui.body);
  state.ui.cancel.fire("click");
  second.fields.reason.reportValidity();
  assert.equal(second.fields.fields.parentElement, state.ui.body);
});

test("Apply blocks missing reasons and Other details until they are supplied", () => {
  const { fields: f, drawer, ui } = setup();
  f.open.fire("click");
  change(f.item, "2", "change");
  ui.apply.fire("click");
  assert.equal(drawer.open, true);
  change(f.reason, "other", "change");
  change(f.other, "");
  ui.apply.fire("click");
  assert.equal(drawer.open, true);
  change(f.other, "Checked with worker");
  ui.apply.fire("click");
  assert.equal(drawer.open, false);
});

test("Apply blocks positive travel without confirmed km and allows correction", () => {
  const { fields: f, drawer, ui } = setup();
  f.open.fire("click");
  change(f.claim, "20");
  ui.apply.fire("click");
  assert.equal(drawer.open, true);
  assert.notEqual(f.claim.validationMessage, "");
  assert.equal(f["claim-error"].hidden, false);
  change(f.km, "10");
  change(f.reason, "missing_km", "change");
  assert.equal(f.claim.validationMessage, "");
  ui.apply.fire("click");
  assert.equal(drawer.open, false);
});

test("time correction is opt-in and preserves legacy original hours until changed", () => {
  const state = setup({ originalHours: "2.25" });
  const f = state.fields;
  assert.equal(f["time-fields"].hidden, true);
  assert.equal(f.start.disabled, true);
  assert.deepEqual(postedValues(state.form, f.start), []);
  f.open.fire("click");
  change(f.toggle, true, "change");
  assert.equal(f["time-fields"].hidden, false);
  assert.equal(f.start.required, true);
  assert.equal(f.start.disabled, false);
  assert.equal(f.hours.textContent, "2.25");
  assert.equal(f.reason.required, false);
  change(f.end, "10:45");
  assert.equal(f.hours.textContent, "1.75");
  change(f.toggle, false, "change");
  assert.equal(f.hours.textContent, "2.25");
  assert.equal(f.reason.required, false);
  assertTotals(state, 13500n);
});

test("time preview deducts breaks, rounds hours, and stages corrected time on Apply", () => {
  const state = setup();
  const { fields: f, ui, form } = state;
  f.open.fire("click");
  change(f.toggle, true, "change");
  change(f.end, "10:45");
  change(f.pause, "15");
  change(f.reason, "incorrect_time", "change");
  assert.equal(f.hours.textContent, "1.50");
  assert.equal(f["hours-preview"].textContent, "1.50 h");
  assertTotals(state, 9000n);
  change(f.end, "10:46");
  assert.equal(f.hours.textContent, "1.52");
  assertTotals(state, 9120n);
  ui.apply.fire("click");
  assert.deepEqual(postedValues(form, f.toggle), ["on"]);
  assert.deepEqual(postedValues(form, f.end), ["10:46"]);
  assert.deepEqual(postedValues(form, f.pause), ["15"]);
  assert.equal(state.row.dataset.originalHours, "2.50");
  assert.equal(state.row.dataset.originalEnd, "11:30");
});

for (const [label, end, pause] of [
  ["missing end", "", "0"], ["reversed time", "08:00", "0"],
  ["missing break", "10:45", ""], ["negative break", "10:45", "-1"],
  ["fractional break", "10:45", "0.5"], ["break consuming service", "10:45", "105"],
]) {
  test(`invalid time (${label}) blocks Apply and clears its error after correction`, () => {
    const { fields: f, drawer, ui } = setup();
    f.open.fire("click");
    change(f.toggle, true, "change");
    change(f.end, end);
    change(f.pause, pause);
    change(f.reason, "incorrect_time", "change");
    ui.apply.fire("click");
    assert.equal(drawer.open, true);
    assert.equal(f["time-error"].hidden, false);
    assert.equal(f.hours.textContent, "-");
    assert.equal(ui.after.textContent, "-");
    change(f.end, "10:45");
    change(f.pause, "0");
    assert.equal(f["time-error"].hidden, true);
    assert.equal(f.end.validationMessage, "");
    ui.apply.fire("click");
    assert.equal(drawer.open, false);
  });
}

for (const [amount, expectedClaimCents] of [[".50", 50n], ["1e2", 10000n]]) {
  test(`manual travel ${amount} contributes exactly ${expectedClaimCents} cents in list and drawer`, () => {
    const state = setup({ originalKm: "12" });
    const { fields: f, ui, form } = state;
    change(f.claim, amount);
    assertTotals(state, 15000n + expectedClaimCents);
    f.open.fire("click");
    assertTotals(state, 15000n + expectedClaimCents);
    change(f.claim, "0");
    assertTotals(state, 15000n);
    change(f.claim, amount);
    assertTotals(state, 15000n + expectedClaimCents);
    ui.apply.fire("click");
    assertTotals(state, 15000n + expectedClaimCents);
    assert.deepEqual(postedValues(form, f.claim), [amount]);
  });
}

for (const [travelPrice, claim, total] of [
  ["0.00", "20", 15000n], ["1.25", "20", 17500n], ["1.25", "0.02", 15003n],
]) {
  for (const admin of [true, false]) {
    test(`${admin ? "admin" : "accountant"} travel uses configured price ${travelPrice} for claim ${claim}`, () => {
      const state = setup({ admin, originalKm: "12", travelPrice });
      change(state.fields.claim, claim);
      assertTotals(state, total);
      assert.equal(state.fields.claim.value, claim);
      if (admin) {
        state.fields.open.fire("click");
        assertTotals(state, total);
        assert.equal(state.fields.reason.required, false);
      }
    });
  }
}

test("accountant rows preview claims without exposing adjustments", () => {
  const state = setup({ admin: false, originalKm: "12", claim: "10" });
  assert.equal(state.row.querySelector("[data-billing-open]"), null);
  assert.equal(state.row.classList.contains("invoice-drawer-ready"), false);
  assert.equal(state.drawer.open, false);
  change(state.fields.claim, "20");
  assertTotals(state, 17000n);
});

test("rows without claim controls retain their service-only total", () => {
  const state = setup({ admin: false, withClaim: false, originalHours: "1.50", originalPrice: "70.07" });
  assertTotals(state, 10511n);
  assert.equal(state.row.querySelector("[data-billing-claim] input"), null);
});

test("unsupported dialogs leave native adjustment controls available", () => {
  const { fields: f, row, form } = setup({ dialogSupported: false, originalKm: "12" });
  assert.equal(f.open.hidden, true);
  assert.equal(row.classList.contains("invoice-drawer-ready"), false);
  assert.equal(f.fields.parentElement, f.details);
  assert.equal(f.km.form, form);
  assert.equal(f.claim.disabled, false);
});
