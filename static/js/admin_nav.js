(function () {
  "use strict";

  const TRANSITION_MS = 240;
  const menuButton = document.querySelector(".admin-mobile-menu-button");
  const drawer = document.querySelector(".admin-mobile-drawer");
  const surface = document.querySelector(".admin-mobile-surface");
  const backdrop = document.querySelector(".admin-mobile-drawer-backdrop");
  const closeButton = document.querySelector(".admin-mobile-close-button");

  if (!menuButton || !drawer || !surface || !backdrop || !closeButton) {
    return;
  }

  const mobileQuery = window.matchMedia("(max-width: 760px)");
  let open = false;
  let hideTimer = null;
  let focusTimer = null;

  function setDrawerOpen(value) {
    window.clearTimeout(hideTimer);
    window.clearTimeout(focusTimer);
    drawer.hidden = backdrop.hidden = false;
    drawer.setAttribute("aria-hidden", "false");
    // Establish the closed position before the opening transition.
    drawer.getBoundingClientRect();
    open = value;
    document.body.classList.toggle("admin-nav-open", open);
    menuButton.setAttribute("aria-expanded", String(open));
    surface.inert = open;
    if (open) {
      focusTimer = window.setTimeout(function () {
        closeButton.focus({ preventScroll: true });
      }, TRANSITION_MS);
    } else {
      menuButton.focus({ preventScroll: true });
      hideTimer = window.setTimeout(function () {
        if (!open) {
          drawer.hidden = backdrop.hidden = true;
          drawer.setAttribute("aria-hidden", "true");
        }
      }, TRANSITION_MS);
    }
  }

  menuButton.addEventListener("click", function () { setDrawerOpen(true); });
  closeButton.addEventListener("click", function () { setDrawerOpen(false); });
  backdrop.addEventListener("click", function () { setDrawerOpen(false); });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && open) {
      setDrawerOpen(false);
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
    open = false;
    window.clearTimeout(hideTimer);
    window.clearTimeout(focusTimer);
    document.body.classList.remove("admin-nav-open");
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
  window.addEventListener("pagehide", resetNavigation);
})();
