(function () {
  "use strict";

  const EDGE_ZONE = 24;
  const INTENT_DISTANCE = 10;
  const OPEN_RATIO = 0.35;
  const CLOSE_RATIO = 0.65;
  const FLICK_VELOCITY = 0.45;
  const TRANSITION_MS = 240;

  const menuButton = document.querySelector(".admin-mobile-menu-button");
  const drawer = document.querySelector(".admin-mobile-drawer");
  const backdrop = document.querySelector(".admin-mobile-drawer-backdrop");
  const edgeZone = document.querySelector(".admin-edge-swipe-zone");
  const closeButton = document.querySelector(".admin-mobile-close-button");
  const closeControls = document.querySelectorAll("[data-admin-menu-close]");

  if (!menuButton || !drawer || !backdrop || !edgeZone || !closeButton) {
    return;
  }

  const state = {
    open: false,
    tracking: false,
    dragging: false,
    mode: null,
    pointerId: null,
    pointerTarget: null,
    startX: 0,
    startY: 0,
    lastX: 0,
    lastTime: 0,
    velocityX: 0,
    progress: 0,
    hideTimer: null,
  };

  function drawerWidth() {
    return Math.max(drawer.getBoundingClientRect().width, 1);
  }

  function revealLayers() {
    window.clearTimeout(state.hideTimer);
    drawer.hidden = false;
    backdrop.hidden = false;
    drawer.setAttribute("aria-hidden", "false");
  }

  function hideLayersAfterTransition() {
    window.clearTimeout(state.hideTimer);
    state.hideTimer = window.setTimeout(function () {
      if (!state.open && !state.dragging) {
        drawer.hidden = true;
        backdrop.hidden = true;
        drawer.setAttribute("aria-hidden", "true");
      }
    }, TRANSITION_MS);
  }

  function clearInlineDragStyles() {
    drawer.style.removeProperty("transform");
    backdrop.style.removeProperty("opacity");
  }

  function setDrawerOpen(open, options) {
    const settings = options || {};
    const moveFocus = settings.moveFocus !== false;

    state.open = open;
    state.progress = open ? 1 : 0;
    state.dragging = false;
    document.body.classList.remove("admin-nav-dragging");
    clearInlineDragStyles();
    menuButton.setAttribute("aria-expanded", String(open));
    edgeZone.hidden = open;

    if (open) {
      revealLayers();
      window.requestAnimationFrame(function () {
        document.body.classList.add("admin-nav-open");
      });
      if (moveFocus) {
        window.setTimeout(function () {
          closeButton.focus();
        }, TRANSITION_MS);
      }
      return;
    }

    document.body.classList.remove("admin-nav-open");
    hideLayersAfterTransition();
    if (moveFocus) {
      menuButton.focus();
    }
  }

  function resetTracking() {
    if (
      state.pointerTarget &&
      state.pointerId !== null &&
      state.pointerTarget.hasPointerCapture &&
      state.pointerTarget.hasPointerCapture(state.pointerId)
    ) {
      state.pointerTarget.releasePointerCapture(state.pointerId);
    }

    state.tracking = false;
    state.dragging = false;
    state.mode = null;
    state.pointerId = null;
    state.pointerTarget = null;
    document.body.classList.remove("admin-nav-dragging");
  }

  function beginTracking(event, mode) {
    if (!event.isPrimary || state.tracking) {
      return;
    }

    if (mode === "open" && event.clientX > EDGE_ZONE) {
      return;
    }

    state.tracking = true;
    state.dragging = false;
    state.mode = mode;
    state.pointerId = event.pointerId;
    state.pointerTarget = event.currentTarget;
    state.startX = event.clientX;
    state.startY = event.clientY;
    state.lastX = event.clientX;
    state.lastTime = event.timeStamp;
    state.velocityX = 0;
    state.progress = mode === "open" ? 0 : 1;
  }

  function resolveIntent(deltaX, deltaY) {
    const horizontalDistance = Math.abs(deltaX);
    const verticalDistance = Math.abs(deltaY);

    if (verticalDistance > INTENT_DISTANCE && verticalDistance > horizontalDistance) {
      return "vertical";
    }
    if (horizontalDistance > INTENT_DISTANCE && horizontalDistance > verticalDistance) {
      return "horizontal";
    }
    return "pending";
  }

  function beginDrag(event) {
    state.dragging = true;
    revealLayers();
    document.body.classList.add("admin-nav-dragging");
    if (state.pointerTarget.setPointerCapture) {
      state.pointerTarget.setPointerCapture(event.pointerId);
    }
  }

  function updateDrag(event) {
    if (!state.tracking || event.pointerId !== state.pointerId) {
      return;
    }

    const deltaX = event.clientX - state.startX;
    const deltaY = event.clientY - state.startY;
    const intent = resolveIntent(deltaX, deltaY);

    if (!state.dragging) {
      if (intent === "vertical") {
        resetTracking();
        return;
      }
      if (intent !== "horizontal") {
        return;
      }
      if ((state.mode === "open" && deltaX <= 0) || (state.mode === "close" && deltaX >= 0)) {
        resetTracking();
        return;
      }
      beginDrag(event);
    }

    event.preventDefault();
    const width = drawerWidth();
    state.progress = state.mode === "open"
      ? Math.min(Math.max(deltaX / width, 0), 1)
      : Math.min(Math.max(1 + deltaX / width, 0), 1);

    const elapsed = Math.max(event.timeStamp - state.lastTime, 1);
    state.velocityX = (event.clientX - state.lastX) / elapsed;
    state.lastX = event.clientX;
    state.lastTime = event.timeStamp;

    drawer.style.transform = "translate3d(" + ((state.progress - 1) * 100) + "%, 0, 0)";
    backdrop.style.opacity = String(state.progress);
  }

  function finishTracking(event) {
    if (!state.tracking || event.pointerId !== state.pointerId) {
      return;
    }

    if (!state.dragging) {
      resetTracking();
      return;
    }

    const shouldOpen = state.mode === "open"
      ? state.progress >= OPEN_RATIO || state.velocityX >= FLICK_VELOCITY
      : state.progress > CLOSE_RATIO && state.velocityX > -FLICK_VELOCITY;

    resetTracking();
    window.requestAnimationFrame(function () {
      setDrawerOpen(shouldOpen, { moveFocus: false });
    });
  }

  function cancelTracking() {
    if (!state.tracking) {
      return;
    }

    const returnOpen = state.open || state.mode === "close";
    resetTracking();
    setDrawerOpen(returnOpen, { moveFocus: false });
  }

  menuButton.addEventListener("click", function () {
    setDrawerOpen(true);
  });

  closeControls.forEach(function (control) {
    control.addEventListener("click", function () {
      setDrawerOpen(false);
    });
  });

  edgeZone.addEventListener("pointerdown", function (event) {
    beginTracking(event, "open");
  });
  edgeZone.addEventListener("pointermove", updateDrag);
  edgeZone.addEventListener("pointerup", finishTracking);
  edgeZone.addEventListener("pointercancel", cancelTracking);

  drawer.addEventListener("pointerdown", function (event) {
    beginTracking(event, "close");
  });
  drawer.addEventListener("pointermove", updateDrag);
  drawer.addEventListener("pointerup", finishTracking);
  drawer.addEventListener("pointercancel", cancelTracking);

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && state.open) {
      setDrawerOpen(false);
    }
  });

  const desktopQuery = window.matchMedia("(min-width: 761px)");
  const resetAtDesktopWidth = function (event) {
    if (!event.matches) {
      return;
    }
    resetTracking();
    state.open = false;
    document.body.classList.remove("admin-nav-open");
    clearInlineDragStyles();
    menuButton.setAttribute("aria-expanded", "false");
    drawer.hidden = true;
    backdrop.hidden = true;
    drawer.setAttribute("aria-hidden", "true");
    edgeZone.hidden = false;
  };

  if (desktopQuery.addEventListener) {
    desktopQuery.addEventListener("change", resetAtDesktopWidth);
  } else {
    desktopQuery.addListener(resetAtDesktopWidth);
  }
})();
