const assert = require("node:assert/strict");
const { existsSync, readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const filename = path.resolve(__dirname, "../../static/js/invoice_billing.js");
const source = existsSync(filename) ? readFileSync(filename, "utf8") : "";

function element(value = "") {
  return {
    value, hidden: false, disabled: false, required: false, open: false,
    dataset: {}, listeners: {}, textContent: "", parentElement: null,
    addEventListener(type, listener) { this.listeners[type] = listener; },
    fire(type) { this.listeners[type]?.({ target: this }); },
    dispatchEvent(event) { this.fire(event.type); },
    appendChild(child) { child.parentElement = this; },
  };
}

function setup({ originalKm = "0", category = "Self-care", item = "", km = "", claim = "", reason = "", errors = false, admin = true } = {}) {
  const fields = Object.fromEntries([
    "item", "km", "claim", "reason", "other", "other-field", "details",
    "km-field", "km-home", "km-slot", "claim-field", "claim-empty", "rate", "total", "item-label", "reset-item",
  ].map(name => [name, element()]));
  fields.item.options = [
    { value: "", textContent: "Keep original item", dataset: {} },
    { value: "1", textContent: "Original item", dataset: { price: "60.00", category } },
    { value: "2", textContent: "Community item", dataset: { price: "80.25", category: "Community access" } },
    { value: "3", textContent: "Other item", dataset: { price: "90.00", category: "Self-care" } },
  ];
  Object.defineProperty(fields.item, "selectedOptions", { get() { return this.options.filter(option => option.value === this.value); } });
  Object.assign(fields.item, { value: item });
  Object.assign(fields.km, { value: km });
  Object.assign(fields.claim, { value: claim });
  Object.assign(fields.reason, { value: reason });
  fields.other.value = "Checked with worker";
  const row = {
    dataset: { originalItem: "1", originalCategory: category, originalKm, originalPrice: "60.00", originalLabel: "Original item", hours: "2.5", billingErrors: String(errors) },
    querySelector(selector) { return fields[selector.match(/data-billing-([a-z-]+)/)?.[1]] || null; },
  };
  const document = { querySelectorAll: () => admin ? [row] : [] };
  vm.runInNewContext(source, { document, Event });
  return { fields, row };
}

test("ordinary admin rows keep optional km in the adjustment menu and hide empty claims", () => {
  const { fields: f } = setup();
  assert.equal(f["claim-field"].hidden, true);
  assert.equal(f.claim.disabled, true);
  assert.equal(f["km-field"].parentElement, f["km-home"]);
  assert.equal(f.reason.required, false);
});

test("original Community access keeps confirmed km visible even after selecting another item", () => {
  const { fields: f } = setup({ category: "Community access", item: "3" });
  assert.equal(f["km-field"].parentElement, f["km-slot"]);
  assert.equal(f["claim-field"].hidden, false);
  assert.equal(f.reason.required, true);
});

test("item selection previews the rate and service total without changing hours or claim", () => {
  const { fields: f, row } = setup({ claim: "17.35" });
  f.item.value = "2";
  f.item.fire("change");
  assert.equal(f.rate.textContent, "80.25");
  assert.equal(f.total.textContent, "200.63");
  assert.equal(f["item-label"].textContent, "Community item");
  assert.equal(f["km-field"].parentElement, f["km-slot"]);
  assert.equal(f.claim.value, "17.35");
  assert.equal(row.dataset.hours, "2.5");
  assert.equal(f.reason.required, true);
});

test("blank item restores original preview and is not an adjustment", () => {
  const { fields: f } = setup({ item: "2" });
  f.item.value = "";
  f.item.fire("change");
  assert.equal(f.rate.textContent, "60.00");
  assert.equal(f.total.textContent, "150.00");
  assert.equal(f.reason.required, false);
});

test("reset item restores the original rate without clearing confirmed km or manual claim", () => {
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
  f.item.value = "2";
  f.item.fire("change");
  assert.equal(f["reset-item"].hidden, false);
  f["reset-item"].fire("click");
  assert.equal(f.reason.required, false);
});

test("blank km retains recorded km but explicit zero requires a correction reason", () => {
  const { fields: f } = setup({ originalKm: "12.00" });
  assert.equal(f.reason.required, false);
  assert.equal(f.claim.disabled, false);
  f.km.value = "0";
  f.km.fire("input");
  assert.equal(f.reason.required, true);
  assert.equal(f["claim-field"].hidden, false);
  assert.equal(f.km.value, "0");
});

test("missing km correction enables the same claim control without deriving money", () => {
  const { fields: f } = setup();
  f.km.value = "4.5";
  f.km.fire("input");
  assert.equal(f.claim.disabled, false);
  assert.equal(f["claim-field"].hidden, false);
  assert.equal(f.claim.value, "");
  assert.equal(f.reason.required, true);
  assert.equal(f.details.open, true);
});

test("manual claim remains visible and enabled when switching away from Community access", () => {
  const { fields: f } = setup({ item: "2" });
  f.claim.value = "23.75";
  f.item.value = "3";
  f.item.fire("change");
  assert.equal(f["claim-field"].hidden, false);
  assert.equal(f.claim.disabled, false);
  assert.equal(f.claim.value, "23.75");
});

test("Other details are required only for Other and disabled while hidden", () => {
  const { fields: f } = setup({ item: "2", reason: "other" });
  assert.equal(f.other.required, true);
  assert.equal(f["other-field"].hidden, false);
  f.reason.value = "service_changed";
  f.reason.fire("change");
  assert.equal(f["other-field"].hidden, true);
  assert.equal(f.other.disabled, true);
  assert.equal(f.other.required, false);
  f.reason.value = "other";
  f.reason.fire("change");
  assert.equal(f.other.disabled, false);
  assert.equal(f.other.value, "Checked with worker");
});

test("bound errors expand the adjustment menu and retain claim access", () => {
  const { fields: f } = setup({ errors: true });
  assert.equal(f.details.open, true);
  assert.equal(f["claim-field"].hidden, false);
});

test("invalid controls open a manually collapsed adjustment menu", () => {
  const { fields: f } = setup({ item: "2" });
  f.details.open = false;
  f.reason.fire("invalid");
  assert.equal(f.details.open, true);
});

test("numerically identical kilometres and explicit original item are not changes", () => {
  const { fields: f } = setup({ originalKm: "12.00", km: "12", item: "1" });
  assert.equal(f.reason.required, false);
  assert.equal(f.rate.textContent, "60.00");
});

test("accountant rows are not enhanced", () => {
  const { fields: f } = setup({ admin: false });
  assert.equal(f.claim.disabled, false);
  assert.equal(f["claim-field"].hidden, false);
  assert.deepEqual(f.item.listeners, {});
});

test("reverting a change does not require leftover Other details", () => {
  const { fields: f } = setup({ item: "2", reason: "other" });
  f.item.value = "";
  f.item.fire("change");
  assert.equal(f.reason.required, false);
  assert.equal(f.other.required, false);
});

test("preview uses the same decimal half-up rounding as invoice creation", () => {
  const { fields: f, row } = setup({ item: "2" });
  f.item.options[2].dataset.price = "70.07";
  row.dataset.hours = "1.50";
  f.item.fire("change");
  assert.equal(f.total.textContent, "105.11");
});
