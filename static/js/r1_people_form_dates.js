/* People-form presentation adapter; original named date controls are preserved. */
(() => {
  "use strict";
  const form = document.querySelector(".r1-people-form .record-form");
  if (!form || typeof window.initDateTimePickers !== "function") return;
  const desktop = window.matchMedia("(min-width: 761px) and (hover: hover) and (pointer: fine)");
  form.querySelectorAll("[data-people-date]").forEach(root => {
    const native = root.querySelector("input[type=date]");
    const proxy = root.querySelector("[data-people-date-proxy]");
    const trigger = root.querySelector("[data-picker-trigger]");
    const display = root.querySelector("[data-picker-display]");
    const panel = root.querySelector("[data-picker-popover]");
    const error = root.querySelector("[data-people-date-error]");
    const boundInvalid = trigger.getAttribute("aria-invalid") === "true";
    let initialized = false;
    let validationAttempted = false;

    const sync = () => {
      proxy.value = native.value;
      const parts = native.value.split("-");
      display.textContent = native.value ? `${parts[2]}/${parts[1]}/${parts[0]}` : "dd/mm/yyyy";
      trigger.disabled = native.disabled;
      trigger.setAttribute("aria-invalid", String(boundInvalid || (validationAttempted && !native.validity.valid)));
      if (native.validity.valid) { error.hidden = true; error.textContent = ""; }
    };
    const enhance = () => {
      if (desktop.matches && !initialized) {
        root.dataset.dateTimePicker = "date";
        proxy.value = native.value;
        window.initDateTimePickers(root.parentElement);
        trigger.addEventListener("click", () => {
          if (trigger.getAttribute("aria-expanded") === "true") {
            const day = panel.querySelector(".calendar-day.selected") || panel.querySelector(".calendar-day.today") || panel.querySelector(".calendar-day");
            if (day) day.focus({ preventScroll: true });
          }
        });
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
      validationAttempted = true;
      error.textContent = native.validationMessage;
      error.hidden = false;
      trigger.setAttribute("aria-invalid", "true");
      if (form.querySelector(":invalid") === native) trigger.focus();
    });
    root.querySelector("label").addEventListener("click", event => {
      if (desktop.matches) { event.preventDefault(); trigger.focus(); }
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && (panel.contains(event.target) || event.target === trigger)) trigger.focus({ preventScroll: true });
    });
    form.addEventListener("reset", () => setTimeout(sync, 0));
    desktop.addEventListener("change", enhance);
    enhance();
  });
})();
