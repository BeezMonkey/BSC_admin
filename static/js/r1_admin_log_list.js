/* UI-only disclosure enhancement. Native details remains the no-script fallback. */
(() => {
  "use strict";

  const root = document.querySelector(".r1-admin-log-list");
  const disclosure = root && root.querySelector("details.service-log-missing");
  if (!disclosure) return;

  const trigger = disclosure.querySelector(":scope > summary");
  const panel = disclosure.querySelector(".service-log-missing-panel");
  const closeButton = panel.querySelector("[data-missing-close]");
  const mobile = window.matchMedia("(max-width: 760px)");
  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  const position = () => {
    if (!disclosure.open) return;
    if (mobile.matches) {
      panel.removeAttribute("data-anchored");
      panel.removeAttribute("style");
      return;
    }

    // Clamp to the visible viewport, including when the anchor is near an edge.
    const viewport = window.visualViewport;
    const left = (viewport ? viewport.offsetLeft : 0) + 12;
    const top = (viewport ? viewport.offsetTop : 0) + 12;
    const width = (viewport ? viewport.width : window.innerWidth) - 24;
    const height = (viewport ? viewport.height : window.innerHeight) - 24;
    const anchor = trigger.getBoundingClientRect();
    panel.setAttribute("data-anchored", "");
    panel.style.width = `${Math.min(520, width)}px`;
    panel.style.maxHeight = `${Math.min(432, height)}px`;
    const bounds = panel.getBoundingClientRect();
    const below = anchor.bottom + 8;
    const above = anchor.top - bounds.height - 8;
    const preferred = below + bounds.height <= top + height ? below : above;
    panel.style.left = `${clamp(anchor.left, left, left + width - bounds.width)}px`;
    panel.style.top = `${clamp(preferred, top, top + height - bounds.height)}px`;
  };

  const close = (restoreFocus) => {
    disclosure.open = false;
    trigger.setAttribute("aria-expanded", "false");
    if (restoreFocus) trigger.focus({ preventScroll: true });
  };

  closeButton.hidden = false;
  trigger.setAttribute("aria-expanded", String(disclosure.open));
  closeButton.addEventListener("click", () => close(true));
  disclosure.addEventListener("toggle", (event) => {
    if (event.target === disclosure) {
      trigger.setAttribute("aria-expanded", String(disclosure.open));
    }
    position();
  }, true);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && disclosure.open) {
      event.preventDefault();
      close(true);
    }
  });
  document.addEventListener("click", (event) => {
    if (disclosure.open && !disclosure.contains(event.target)) {
      close(panel.contains(document.activeElement));
    }
  });
  window.addEventListener("resize", position, { passive: true });
  window.addEventListener("scroll", position, { passive: true });
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", position, { passive: true });
    window.visualViewport.addEventListener("scroll", position, { passive: true });
  }
  position();
})();
