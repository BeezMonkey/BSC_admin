const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const css = readFileSync(path.resolve(__dirname, "../../static/css/r1_admin_invoice_create.css"), "utf8");
const rules = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)];
const rule = selector => rules.find(match => match[1].trim() === selector)?.[2] || "";

test("adjust action retains its dark icon on quiet hover and keyboard focus", () => {
  const style = rule(".app-shell.r1-ui.r1-admin-invoice-create .invoice-billing-row .invoice-adjust-button:is(:hover, :focus-visible)");
  assert.match(style, /background:\s*#f0f4f8\s+url\('\.\.\/img\/r1\/icons\/invoice-adjust\.svg'\)/);
  assert.match(style, /border-color:\s*var\(--r1-strong-border\)/);
  assert.doesNotMatch(style, /outline:\s*none/);
});

test("only inline claim help is shortened; the moved drawer field retains full help", () => {
  assert.match(rule(".r1-admin-invoice-create .invoice-claim-help-inline"), /display:\s*none/);
  assert.match(rule(".r1-admin-invoice-create .invoice-travel-claim .invoice-claim-help-inline"), /display:\s*inline/);
  assert.match(rule(".r1-admin-invoice-create .invoice-travel-claim .invoice-claim-help-full"), /display:\s*none/);
});
