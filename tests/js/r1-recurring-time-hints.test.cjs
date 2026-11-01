const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../static/js/r1_recurring_time_hints.js'), 'utf8');

function setup(value) {
  const listeners = {};
  const input = {value, addEventListener(name, callback) {listeners[name] = callback;}};
  let empty;
  const shell = {querySelector(selector) {assert.equal(selector, 'input[type=time]');return input;},
    classList: {toggle(name, active) {assert.equal(name, 'is-empty');empty = active;}}};
  const document = {querySelectorAll(selector) {
    assert.equal(selector, '.r1-roster-record .recurring-time-shell');return [shell];
  }};
  vm.runInNewContext(source, {document});
  return {input, listeners, empty: () => empty};
}

test('empty control gets only the empty display class', () => {
  const state = setup('');assert.equal(state.empty(), true);assert.equal(state.input.value, '');
});
test('server-rendered nonempty control retains its value', () => {
  const state = setup('09:17');assert.equal(state.empty(), false);assert.equal(state.input.value, '09:17');
});
test('input event preserves arbitrary minute precision', () => {
  const state = setup('');state.input.value = '11:17';state.listeners.input();
  assert.equal(state.empty(), false);assert.equal(state.input.value, '11:17');
});
test('clearing the native control restores the empty class', () => {
  const state = setup('11:17');state.input.value = '';state.listeners.change();
  assert.equal(state.empty(), true);assert.equal(state.input.value, '');
});
test('helper registers no submission, validation, storage or network behavior', () => {
  const state = setup('');assert.deepEqual(Object.keys(state.listeners), ['input', 'change']);
  for (const forbidden of ['fetch(', '.submit(', 'requestSubmit(', 'setCustomValidity', 'localStorage']) {
    assert.equal(source.includes(forbidden), false);
  }
});
