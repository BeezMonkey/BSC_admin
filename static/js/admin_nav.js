(function () {
  "use strict";

  const INSET_START = 32;
  const INTENT_DISTANCE = 6;
  const OPEN_RATIO = 0.35;
  const CLOSE_RATIO = 0.65;
  const FLICK_VELOCITY = 0.45;
  const TRANSITION_MS = 240;
  const SUPPRESS_CLICK_MS = 450;
  const shell = document.querySelector("[data-admin-theme]");
  const menuButton = document.querySelector(".admin-mobile-menu-button");
  const drawer = document.querySelector(".admin-mobile-drawer");
  const surface = document.querySelector(".admin-mobile-surface");
  const backdrop = document.querySelector(".admin-mobile-drawer-backdrop");
  const closeButton = document.querySelector(".admin-mobile-close-button");

  if (!shell || !menuButton || !drawer || !surface || !backdrop || !closeButton) {
    return;
  }

  const mobileQuery = window.matchMedia("(max-width: 760px)");
  let open = false;
  let gesture = null;
  let hideTimer = null;
  let focusTimer = null;
  let suppressClickUntil = 0;

  function isIgnoredGestureTarget(target) {
    if (!(target instanceof Element)) return true;
    if (target.closest(
      "a, button, input, select, textarea, summary, [contenteditable], [role='slider'], dialog, .table-wrap, .planner-scroll-frame, [data-admin-swipe-ignore]"
    )) return true;

    // Other pages may supply scroll containers without the shared table class.
    for (let element = target; element && element !== shell; element = element.parentElement) {
      if (element.scrollWidth > element.clientWidth + 1 && /auto|scroll/.test(getComputedStyle(element).overflowX)) {
        return true;
      }
    }
    return false;
  }

  function revealLayers() {
    window.clearTimeout(hideTimer);
    drawer.hidden = backdrop.hidden = false;
    drawer.setAttribute("aria-hidden", "false");
  }

  function setDrawerOpen(value, moveFocus) {
    window.clearTimeout(focusTimer);
    revealLayers();
    // Establish the closed position before a button-initiated opening transition.
    drawer.getBoundingClientRect();
    open = value;
    document.body.classList.remove("admin-nav-dragging");
    document.body.classList.toggle("admin-nav-open", open);
    drawer.style.removeProperty("transform");
    backdrop.style.removeProperty("opacity");
    menuButton.setAttribute("aria-expanded", String(open));
    surface.inert = open;
    if (open && moveFocus) {
      focusTimer = window.setTimeout(function () {
        closeButton.focus({ preventScroll: true });
      }, TRANSITION_MS);
    }
    if (!open) {
      if (moveFocus) menuButton.focus({ preventScroll: true });
      hideTimer = window.setTimeout(function () {
        if (!open && !gesture) {
          drawer.hidden = backdrop.hidden = true;
          drawer.setAttribute("aria-hidden", "true");
        }
      }, TRANSITION_MS);
    }
  }

  function cancelTracking() {
    if (!gesture) return;
    gesture = null;
    setDrawerOpen(open, false);
  }

  function beginTracking(x, y, target, id, source) {
    if (!mobileQuery.matches || gesture) return;
    if (!open && (!surface.contains(target) || x < INSET_START || x > window.innerWidth - 24)) return;
    if (target !== backdrop && isIgnoredGestureTarget(target)) return;
    gesture = {
      x, y, id, source,
      start: open ? 1 : 0,
      progress: open ? 1 : 0,
      dragging: false,
      lastX: x,
      lastTime: performance.now(),
      velocity: 0,
    };
  }

  function updateDrag(x, y, event) {
    if (!gesture) return;
    const deltaX = x - gesture.x;
    const deltaY = y - gesture.y;
    if (!gesture.dragging) {
      if (Math.abs(deltaY) > Math.abs(deltaX) || (gesture.start === 0 ? deltaX < 0 : deltaX > 0)) {
        cancelTracking();
        return;
      }
      if (Math.abs(deltaX) < INTENT_DISTANCE) return;
      if (!event.cancelable) {
        cancelTracking();
        return;
      }
      gesture.dragging = true;
      window.clearTimeout(focusTimer);
      revealLayers();
      document.body.classList.add("admin-nav-dragging");
    }
    if (event.cancelable) event.preventDefault();
    const now = performance.now();
    gesture.velocity = (x - gesture.lastX) / Math.max(now - gesture.lastTime, 1);
    gesture.lastX = x;
    gesture.lastTime = now;
    const width = Math.max(drawer.getBoundingClientRect().width, 1);
    gesture.progress = Math.min(1, Math.max(0, gesture.start + deltaX / width));
    drawer.style.transform = "translate3d(" + ((gesture.progress - 1) * 100) + "%, 0, 0)";
    backdrop.style.opacity = String(gesture.progress);
  }

  function finishTracking() {
    if (!gesture) return;
    const finished = gesture;
    gesture = null;
    if (!finished.dragging) return;
    suppressClickUntil = performance.now() + SUPPRESS_CLICK_MS;
    const velocity = performance.now() - finished.lastTime < 100 ? finished.velocity : 0;
    const shouldOpen = finished.start === 0
      ? finished.progress >= OPEN_RATIO || velocity > FLICK_VELOCITY
      : finished.progress > CLOSE_RATIO && velocity > -FLICK_VELOCITY;
    setDrawerOpen(shouldOpen, false);
  }

  // Pointer cancellation does not cancel Touch Events. Claim the first horizontal
  // touchmove explicitly so the browser cannot take over an eligible page gesture.
  shell.addEventListener("touchstart", function (event) {
    if (event.touches.length !== 1) {
      cancelTracking();
      return;
    }
    const touch = event.touches[0];
    beginTracking(touch.clientX, touch.clientY, event.target, touch.identifier, "touch");
  }, { passive: true });

  shell.addEventListener("touchmove", function (event) {
    if (!gesture || gesture.source !== "touch") return;
    if (event.touches.length !== 1) {
      cancelTracking();
      return;
    }
    const touch = Array.from(event.touches).find(function (item) { return item.identifier === gesture.id; });
    if (touch) updateDrag(touch.clientX, touch.clientY, event);
  }, { passive: false });

  shell.addEventListener("touchend", function (event) {
    if (gesture && gesture.source === "touch" && Array.from(event.changedTouches).some(function (item) { return item.identifier === gesture.id; })) {
      finishTracking();
    }
  });
  shell.addEventListener("touchcancel", cancelTracking);

  shell.addEventListener("pointerdown", function (event) {
    if (event.pointerType === "touch" || !event.isPrimary || event.button !== 0) return;
    beginTracking(event.clientX, event.clientY, event.target, event.pointerId, "pointer");
  });
  document.addEventListener("pointermove", function (event) {
    if (gesture && gesture.source === "pointer" && event.pointerId === gesture.id) {
      updateDrag(event.clientX, event.clientY, event);
    }
  }, { passive: false });
  document.addEventListener("pointerup", function (event) {
    if (gesture && gesture.source === "pointer" && event.pointerId === gesture.id) finishTracking();
  });
  document.addEventListener("pointercancel", function (event) {
    if (gesture && gesture.source === "pointer" && event.pointerId === gesture.id) cancelTracking();
  });

  shell.addEventListener("click", function (event) {
    if (performance.now() < suppressClickUntil) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);
  menuButton.addEventListener("click", function () { setDrawerOpen(true, true); });
  closeButton.addEventListener("click", function () { setDrawerOpen(false, true); });
  backdrop.addEventListener("click", function () { setDrawerOpen(false, true); });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && (open || gesture)) {
      cancelTracking();
      setDrawerOpen(false, true);
    }
    if (event.key === "Tab" && open) {
      const items = Array.from(drawer.querySelectorAll("a[href], button:not(:disabled)"));
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });

  function resetNavigation() {
    gesture = null;
    open = false;
    suppressClickUntil = 0;
    window.clearTimeout(hideTimer);
    window.clearTimeout(focusTimer);
    document.body.classList.remove("admin-nav-open", "admin-nav-dragging");
    drawer.style.removeProperty("transform");
    backdrop.style.removeProperty("opacity");
    menuButton.setAttribute("aria-expanded", "false");
    surface.inert = false;
    drawer.hidden = backdrop.hidden = true;
    drawer.setAttribute("aria-hidden", "true");
  }
  if (mobileQuery.addEventListener) {
    mobileQuery.addEventListener("change", resetNavigation);
  } else {
    mobileQuery.addListener(resetNavigation);
  }
  window.addEventListener("blur", cancelTracking);
  window.addEventListener("pagehide", resetNavigation);
})();
