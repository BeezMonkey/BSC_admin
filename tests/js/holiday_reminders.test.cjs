const assert = require("node:assert/strict");
const { readFileSync, existsSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const filename = path.resolve(__dirname, "../../static/js/holiday_reminders.js");
const source = existsSync(filename) ? readFileSync(filename, "utf8") : "";

function element() {
  const classes = new Set();
  return {
    children: [], attrs: {}, hidden: false, textContent: "", className: "",
    classList: { add: (...names) => names.forEach(name => classes.add(name)), contains: name => classes.has(name) },
    setAttribute(name, value) { this.attrs[name] = value; },
    getAttribute(name) { return this.attrs[name] || null; },
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; },
  };
}
function setup(raw) {
  const data = {
    coverage: { "2026": ["QLD", "Brisbane", "Logan", "Gold Coast"], "2027": ["QLD", "Brisbane"] },
    holidays: {
      "2026-08-10": [{ name: "Royal Queensland Show", region: "Logan", hours: "All day" }],
      "2026-12-24": [{ name: "Christmas Eve", region: "QLD", hours: "6 pm - midnight" }],
    },
  };
  const window = {};
  const fields = { service_date: { value: "2026-08-10" }, support_item: { value: "weekday-item" }, rate: { value: "65.47" } };
  let fieldEvents = 0;
  for (const field of Object.values(fields)) field.dispatchEvent = () => { fieldEvents += 1; };
  const document = {
    getElementById: id => id === "qld-holiday-data" ? { textContent: raw === undefined ? JSON.stringify(data) : raw } : fields[id.replace(/^id_/, "")],
    createElement: element,
    querySelector: selector => fields[selector.match(/service_date|support_item|rate/)?.[0]] || null,
    querySelectorAll: () => Object.values(fields),
  };
  vm.runInNewContext(source, { window, document });
  assert.ok(window.BscHolidayReminders, "holiday decoration must be available");
  const selected = element(), month = element(), reminder = element();
  const container = {
    querySelector(selector) { return selector === "[data-selected-holidays]" ? selected : month; },
    closest() { return { querySelector: selector => selector === "[data-holiday-item-reminder]" ? reminder : document.querySelector(selector), querySelectorAll: document.querySelectorAll }; },
  };
  return { api: window.BscHolidayReminders, selected, month, reminder, container, fields, fieldEvents: () => fieldEvents };
}
function text(node) { return [node.textContent, ...node.children.map(text)].join(" "); }

test("regional day has accessible name and keeps existing button behavior", () => {
  const { api } = setup(); const button = element();
  button.setAttribute("aria-label", "Mon, 10 Aug 2026"); button.type = "button";
  api.decorateDay(button, "2026-08-10");
  assert.match(button.getAttribute("aria-label"), /Logan only/);
  assert.match(button.title, /Royal Queensland Show/);
  assert.ok(button.classList.contains("holiday-regional"));
  assert.equal(button.type, "button"); assert.equal(button.disabled, undefined);
});
test("ordinary dates are not labelled as holidays", () => {
  const { api } = setup(); const button = element(); button.setAttribute("aria-label", "11 Aug");
  api.decorateDay(button, "2026-08-11");
  assert.equal(button.getAttribute("aria-label"), "11 Aug");
  assert.equal(button.title, undefined);
});
test("part-day reminder remains explicit and clearing removes it", () => {
  const h = setup(); h.api.updateSelected(h.container, "2026-12-24");
  assert.match(text(h.selected), /Christmas Eve/); assert.match(text(h.selected), /6 pm - midnight/);
  assert.equal(h.reminder.hidden, false);
  h.api.updateSelected(h.container, ""); assert.equal(h.selected.hidden, true); assert.equal(h.reminder.hidden, true);
});
test("month details list holiday dates for touch users", () => {
  const h = setup(); h.api.updateMonth(h.container, 2026, 7);
  assert.match(text(h.month), /10 Aug/); assert.match(text(h.month), /Logan only/);
  h.api.updateMonth(h.container, 2026, 8); assert.equal(h.month.hidden, true);
});
test("unknown and partially verified years show coverage warnings", () => {
  const h = setup(); h.api.updateSelected(h.container, "2027-08-09");
  assert.match(text(h.selected), /Logan/); assert.match(text(h.selected), /Gold Coast/);
  h.api.updateMonth(h.container, 2030, 0); assert.match(text(h.month), /not verified/i);
});
test("malformed data does not break the calendar", () => {
  const h = setup("invalid json"); h.api.updateSelected(h.container, "2026-08-10");
  assert.match(text(h.selected), /not verified/i);
});
test("December grid warns about unverified regions in January spillover", () => {
  const h = setup(); h.api.updateMonth(h.container, 2026, 11, "2026-11-30", "2027-01-03");
  assert.match(text(h.month), /2027.*Logan, Gold Coast/);
});
test("all decoration helpers leave date, support item and rate unchanged without events", () => {
  const h = setup(); const before = Object.values(h.fields).map(field => field.value);
  h.api.decorateDay(element(), "2026-12-24");
  h.api.updateMonth(h.container, 2026, 11);
  h.api.updateSelected(h.container, "2026-12-24");
  h.api.updateSelected(h.container, "2027-01-01");
  h.api.updateSelected(h.container, "");
  assert.deepEqual(Object.values(h.fields).map(field => field.value), before);
  assert.equal(h.fieldEvents(), 0);
});
