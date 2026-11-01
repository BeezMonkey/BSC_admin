(() => {
  'use strict';
  document.querySelectorAll('.r1-roster-record .recurring-time-shell').forEach(shell => {
    const input = shell.querySelector('input[type=time]');
    const refresh = () => shell.classList.toggle('is-empty', !input.value);
    input.addEventListener('input', refresh);
    input.addEventListener('change', refresh);
    refresh();
  });
})();
