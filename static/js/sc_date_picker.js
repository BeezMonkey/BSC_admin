(function () {
  "use strict";

  const gap = 6;
  const margin = 8;

  function viewportBounds() {
    const viewport = window.visualViewport;
    const left = viewport ? viewport.offsetLeft : 0;
    const top = viewport ? viewport.offsetTop : 0;
    const bounds = {
      left: left + margin,
      right: Math.min(document.documentElement.clientWidth, left + (viewport ? viewport.width : window.innerWidth)) - margin,
      top: top + margin,
      bottom: top + (viewport ? viewport.height : window.innerHeight) - margin,
    };
    [".worker-mobile-header", ".worker-bottom-nav"].forEach(function (selector, index) {
      const element = document.querySelector(selector);
      if (!element) return;
      const style = getComputedStyle(element);
      if (!["fixed", "sticky"].includes(style.position) || style.display === "none" || style.visibility === "hidden") return;
      const rect = element.getBoundingClientRect();
      if (!rect.height || rect.bottom <= bounds.top || rect.top >= bounds.bottom) return;
      if (index === 0) bounds.top = Math.max(bounds.top, rect.bottom + margin);
      else bounds.bottom = Math.min(bounds.bottom, rect.top - margin);
    });
    return bounds;
  }

  document.querySelectorAll('.sc-log-form [data-date-time-picker="date"]').forEach(function (picker) {
    const trigger = picker.querySelector("[data-picker-trigger]");
    const popover = picker.querySelector("[data-picker-popover]");
    if (!trigger || !popover) return;
    let frame = null;

    function positionCalendar() {
      if (popover.hidden) return;
      const bounds = viewportBounds();
      const rect = trigger.getBoundingClientRect();
      if (rect.bottom <= bounds.top || rect.top >= bounds.bottom || rect.right <= bounds.left || rect.left >= bounds.right) {
        // Close through the shared picker so its active state stays in sync.
        trigger.click();
        return;
      }

      popover.style.width = Math.min(292, Math.max(0, bounds.right - bounds.left)) + "px";
      popover.style.maxHeight = "none";
      const natural = popover.getBoundingClientRect();
      const below = Math.max(0, bounds.bottom - rect.bottom - gap);
      const above = Math.max(0, rect.top - bounds.top - gap);
      const openAbove = natural.height > below && above > below;
      const available = Math.floor(openAbove ? above : below);
      if (available < 48) {
        trigger.click();
        return;
      }

      const height = Math.min(natural.height, available);
      popover.style.maxHeight = available + "px";
      popover.style.left = Math.max(bounds.left, Math.min(rect.left, bounds.right - natural.width)) + "px";
      popover.style.top = (openAbove ? rect.top - gap - height : rect.bottom + gap) + "px";
    }

    function schedulePosition() {
      if (popover.hidden || frame !== null) return;
      frame = requestAnimationFrame(function () {
        frame = null;
        positionCalendar();
      });
    }

    picker.addEventListener("click", schedulePosition);
    window.addEventListener("resize", schedulePosition);
    window.addEventListener("scroll", function (event) {
      if (!popover.contains(event.target)) schedulePosition();
    }, { capture: true, passive: true });
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", schedulePosition);
      window.visualViewport.addEventListener("scroll", schedulePosition);
    }
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(schedulePosition);
      observer.observe(trigger);
      observer.observe(popover);
    }
  });
})();
