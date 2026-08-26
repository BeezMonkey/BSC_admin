(function () {
  const menuButton = document.querySelector(".worker-mobile-menu-button");
  const drawer = document.querySelector(".worker-mobile-drawer");
  const backdrop = document.querySelector(".worker-mobile-drawer-backdrop");
  const closeButtons = document.querySelectorAll("[data-worker-menu-close]");

  if (!menuButton || !drawer || !backdrop) {
    return;
  }

  function openMenu() {
    drawer.hidden = false;
    backdrop.hidden = false;
    document.body.classList.add("worker-nav-open");
    menuButton.setAttribute("aria-expanded", "true");

    const firstItem = drawer.querySelector("a, button");
    if (firstItem) {
      firstItem.focus();
    }
  }

  function closeMenu() {
    drawer.hidden = true;
    backdrop.hidden = true;
    document.body.classList.remove("worker-nav-open");
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.focus();
  }

  menuButton.addEventListener("click", openMenu);

  closeButtons.forEach((button) => {
    button.addEventListener("click", closeMenu);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !drawer.hidden) {
      closeMenu();
    }
  });
})();
