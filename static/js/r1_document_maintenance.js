/* Local calendar adapter. The original named date input stays manually editable. */
(() => {
  "use strict";
  const form = document.querySelector(".r1-admin-document-maintenance .document-metadata-form");
  if (!form || typeof window.initDateTimePickers !== "function") return;
  const desktop = window.matchMedia("(min-width: 761px) and (hover: hover) and (pointer: fine)");
  form.querySelectorAll("[data-maintenance-date]").forEach(root => {
    const native = root.querySelector("input[type=date]");
    const proxy = root.querySelector("[data-maintenance-date-proxy]");
    const trigger = root.querySelector("[data-picker-trigger]");
    const panel = root.querySelector("[data-picker-popover]");
    const display = root.querySelector("[data-picker-display]");
    let initialized = false;
    const sync = () => {
      proxy.value = native.value;
      display.textContent = native.value;
      trigger.disabled = native.disabled;
    };
    const enhance = () => {
      sync();
      if (desktop.matches && !initialized) {
        root.dataset.dateTimePicker = "date";
        window.initDateTimePickers(form);
        trigger.addEventListener("click", () => {
          if (trigger.getAttribute("aria-expanded") === "true") {
            const day = panel.querySelector(".calendar-day.selected") || panel.querySelector(".calendar-day.today") || panel.querySelector(".calendar-day");
            if (day) day.focus({ preventScroll: true });
          }
        });
        initialized = true;
      }
      if (!desktop.matches && trigger.getAttribute("aria-expanded") === "true") trigger.click();
      trigger.hidden = !desktop.matches;
      root.classList.toggle("is-enhanced", desktop.matches);
    };
    proxy.addEventListener("change", () => {
      native.value = proxy.value;
      native.dispatchEvent(new Event("input", { bubbles: true }));
      native.dispatchEvent(new Event("change", { bubbles: true }));
      trigger.focus({ preventScroll: true });
    });
    native.addEventListener("input", sync);
    native.addEventListener("change", sync);
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && panel.contains(event.target)) trigger.focus({ preventScroll: true });
    });
    form.addEventListener("reset", () => setTimeout(sync, 0));
    desktop.addEventListener("change", enhance);
    enhance();
  });
})();
