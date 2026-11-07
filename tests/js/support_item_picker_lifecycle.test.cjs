const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
test('support item partial teardown releases document listeners and preserves native accessibility state', () => {
  function node() {
    const classes = new Set(); const attrs = {}; const listeners = {};
    return { dataset: {}, children: [], options: [], labels: [], selectedIndex: -1, tabIndex: 2,
      classList: { add: name => classes.add(name), remove: (...names) => names.forEach(name => classes.delete(name)), toggle(name, value) { if (value) classes.add(name); else classes.delete(name); } },
      setAttribute: (key, value) => { attrs[key] = value; }, getAttribute: key => attrs[key] ?? null, removeAttribute: key => { delete attrs[key]; },
      append(...children) { children.forEach(child => this.appendChild(child)); }, appendChild(child) { child.parentElement = this; this.children.push(child); return child; },
      insertAdjacentElement(position, child) { assert.equal(position, 'afterend'); this.parentElement.appendChild(child); },
      replaceChildren(...children) { this.children = []; this.append(...children); },
      remove() { this.parentElement.children = this.parentElement.children.filter(child => child !== this); },
      addEventListener(type, callback) { (listeners[type] ||= []).push(callback); }, removeEventListener(type, callback) { listeners[type] = (listeners[type] || []).filter(item => item !== callback); },
      querySelectorAll(selector) { return selector === 'select[data-support-item-picker]' ? this.children.filter(child => child.dataset.supportItemPicker !== undefined) : []; },
      matches() { return false; }, contains(child) { return child === this || this.children.includes(child); }, listeners,
    };
  }
  const document = node(); document.body = node(); document.readyState = 'complete';
  document.createElement = document.createDocumentFragment = node;
  const select = document.appendChild(node()); select.dataset.supportItemPicker = ''; select.setAttribute('aria-hidden', 'false');
  const window = {};
  vm.runInNewContext(readFileSync(path.resolve(__dirname, '../../static/js/support_item_picker.js'), 'utf8'), {
    document, window, MutationObserver: class { observe() {} },
  });
  assert.ok(window.SupportItemPicker, 'picker must expose cleanup for partial page replacement');
  window.SupportItemPicker.initWithin(document);
  assert.equal(document.listeners.click.length, 1);
  window.SupportItemPicker.destroyWithin(document);
  assert.equal(document.listeners.click.length, 0);
  assert.equal(select.listeners.change.length, 0);
  assert.equal(select.getAttribute('aria-hidden'), 'false'); assert.equal(select.tabIndex, 2);
  window.SupportItemPicker.initWithin(document);
  assert.equal(document.listeners.click.length, 1);
  assert.equal(select.dataset.supportItemPickerReady, 'true');
});
