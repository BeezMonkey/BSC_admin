const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");

test("only the inline travel claim uses compact desktop sizing and keeps mobile height", () => {
  const css = readFileSync(path.resolve(__dirname, "../../static/css/r1_admin_invoice_create.css"), "utf8");
  const selector = ".app-shell.r1-admin-invoice-create .invoice-billing-row .invoice-travel-claim input";
  const rules = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter(match => match[1].trim() === selector).map(match => match[2]);
  assert.equal(rules.length, 2);
  assert.match(rules[0], /width:\s*80px/);
  assert.match(rules[0], /height:\s*30px/);
  assert.match(rules[0], /min-height:\s*30px/);
  assert.match(rules[0], /font-size:\s*14px/);
  assert.match(rules[1], /height:\s*44px/);
  assert.match(rules[1], /font-size:\s*16px/);
});
