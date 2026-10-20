/* Local calendar adapter. The original named date input stays manually editable. */
(() => {
  "use strict";
  const form = document.querySelector(".r1-worker-documents .sw-document-form");
  if (!form) return;
  const file = form.querySelector("input[type=file]");
  const selectedFile = form.querySelector("[data-sw-selected-file]");
  if (file && selectedFile) {
    const showFilename = () => {
      selectedFile.textContent = file.files.length ? file.files[0].name : "";
      selectedFile.hidden = !selectedFile.textContent;
    };
    file.addEventListener("change", showFilename);
    form.addEventListener("reset", () => setTimeout(showFilename, 0));
    showFilename();
  }
  if (typeof window.initDateTimePickers !== "function") return;
  const desktop = window.matchMedia("(min-width: 761px) and (hover: hover) and (pointer: fine)");
  form.querySelectorAll("[data-maintenance-date]").forEach(root => {
    const native = root.querySelector("input[type=date]");
    const proxy = root.querySelector("[data-maintenance-date-proxy]");
    const trigger = root.querySelector("[data-picker-trigger]");
    const panel = root.querySelector("[data-picker-popover]");
    const display = root.querySelector("[data-picker-display]");
    // SW-only horizontal placement; the shared engine retains all date behavior.
    const alignToInput = () => {
      if (panel.hidden || !desktop.matches) return;
      const inputRect = native.getBoundingClientRect();
      const viewport = window.visualViewport;
      const minimum = (viewport ? viewport.offsetLeft : 0) + 8;
      const maximum = Math.min(document.documentElement.clientWidth,
        (viewport ? viewport.offsetLeft + viewport.width : window.innerWidth)) - 8;
      const width = panel.getBoundingClientRect().width;
      const left = Math.max(minimum, Math.min(inputRect.left, maximum - width));
      if (Math.abs(parseFloat(panel.style.left) - left) > 0.5) panel.style.left = left + "px";
    };
    // The engine recalculates on open, scroll, resize and month changes.
    // Observe its placement rather than duplicating those behaviors or date logic.
    const placementObserver = new MutationObserver(alignToInput);
    placementObserver.observe(panel, {attributes:true, attributeFilter:["hidden", "style"]});
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
