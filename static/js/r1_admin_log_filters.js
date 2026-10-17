/* List-only adapter: native named dates remain the sole submitted/validated fields. */
(() => {
  "use strict";
  const form = document.querySelector(".r1-admin-log-list [data-service-log-filters]");
  if (!form || typeof window.initDateTimePickers !== "function") return;
  const desktop = window.matchMedia("(min-width: 761px) and (hover: hover) and (pointer: fine)");
  form.querySelectorAll("[data-log-date]").forEach(root => {
    const native = root.querySelector("input[type=date]");
    const proxy = root.querySelector("[data-log-date-proxy]");
    const trigger = root.querySelector("[data-picker-trigger]");
    const display = root.querySelector("[data-picker-display]");
    const panel = root.querySelector("[data-picker-popover]");
    const error = root.querySelector("[data-log-date-error]");
    let initialized = false;

    const sync = () => {
      proxy.value = native.value;
      const parts = native.value.split("-");
      display.textContent = native.value ? `${parts[2]}/${parts[1]}/${parts[0]}` : "dd/mm/yyyy";
      trigger.disabled = native.disabled;
      trigger.setAttribute("aria-invalid", String(!native.validity.valid));
      if (native.validity.valid) { error.hidden = true; error.textContent = ""; }
    };
    const enhance = () => {
      if (desktop.matches && !initialized) {
        root.dataset.dateTimePicker = "date";
        proxy.value = native.value;
        window.initDateTimePickers(root.parentElement);
        initialized = true;
      }
      if (!desktop.matches && trigger.getAttribute("aria-expanded") === "true") trigger.click();
      root.classList.toggle("is-enhanced", desktop.matches);
      native.tabIndex = desktop.matches ? -1 : 0;
      native.setAttribute("aria-hidden", String(desktop.matches));
      trigger.hidden = !desktop.matches;
      sync();
    };
    proxy.addEventListener("change", () => {
      native.value = proxy.value;
      native.dispatchEvent(new Event("input", { bubbles: true }));
      native.dispatchEvent(new Event("change", { bubbles: true }));
      sync();
      trigger.focus({ preventScroll: true });
    });
    native.addEventListener("input", sync);
    native.addEventListener("change", sync);
    native.addEventListener("invalid", event => {
      if (!desktop.matches) return;
      event.preventDefault();
      error.textContent = native.validationMessage;
      error.hidden = false;
      trigger.setAttribute("aria-invalid", "true");
      if (form.querySelector(":invalid") === native) trigger.focus();
    });
    trigger.addEventListener("click", () => {
      if (trigger.getAttribute("aria-expanded") === "true") {
        (panel.querySelector(".calendar-day.selected, .calendar-day.today") || panel.querySelector(".calendar-day")).focus({ preventScroll: true });
      }
    });
    root.querySelector("label").addEventListener("click", event => {
      if (desktop.matches) { event.preventDefault(); trigger.focus(); }
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && (panel.contains(event.target) || event.target === trigger)) trigger.focus({ preventScroll: true });
    });
    form.elements.date_range.addEventListener("change", sync);
    form.addEventListener("reset", () => setTimeout(sync, 0));
    desktop.addEventListener("change", enhance);
    enhance();
  });
})();
