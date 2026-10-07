(function () {
  "use strict";
  const form = document.querySelector("#planner-filter-form");
  const toggle = document.querySelector("#planner-billing-toggle");
  const filter = document.querySelector("#planner-billing-filter");
  if (form && toggle && filter) {
    toggle.addEventListener("change", function () {
      filter.disabled = !toggle.checked;
      form.requestSubmit();
    });
    filter.addEventListener("change", function () { form.requestSubmit(); });
  }

  const drawer = document.querySelector("#planner-billing-drawer");
  if (!drawer || typeof drawer.showModal !== "function") return;
  const content = drawer.querySelector("[data-planner-billing-content]");
  const context = drawer.querySelector("[data-planner-billing-context]");
  const position = drawer.querySelector("[data-planner-billing-position]");
  const closeButton = drawer.querySelector("[data-planner-billing-close]");
  const previous = drawer.querySelector("[data-planner-billing-prev]");
  const next = drawer.querySelector("[data-planner-billing-next]");
  let triggers = [];
  let currentIndex = -1;
  let lastTrigger = null;
  let controller = null;
  let revision = 0;

  function stopRequest() {
    revision += 1;
    if (controller) controller.abort();
  }

  async function load(trigger) {
    stopRequest();
    controller = new AbortController();
    const requestRevision = revision;
    context.textContent = trigger.dataset.plannerBillingContext;
    content.innerHTML = '<p class="planner-billing-message" role="status">Loading billing details...</p>';
    content.setAttribute("aria-busy", "true");
    content.scrollTop = 0;
    position.textContent = `${currentIndex + 1} of ${triggers.length} shifts`;
    previous.disabled = currentIndex <= 0;
    next.disabled = currentIndex >= triggers.length - 1;
    try {
      const response = await fetch(trigger.dataset.plannerBillingUrl, {
        method: "GET", credentials: "same-origin", cache: "no-store", signal: controller.signal,
        headers: { Accept: "text/html" },
      });
      if (!response.ok || response.redirected || response.headers.get("X-Planner-Billing") !== "1") {
        throw new Error("Billing details unavailable");
      }
      const html = await response.text();
      if (requestRevision !== revision || !drawer.open) return;
      // The authenticated endpoint returns an autoescaped Django partial, never user-provided HTML.
      content.innerHTML = html;
    } catch (error) {
      if (requestRevision !== revision || !drawer.open || error.name === "AbortError") return;
      content.innerHTML = '<div class="planner-billing-message" role="alert"><strong>Unable to load billing details.</strong><p>Check your connection and sign-in, then try again.</p><button type="button" data-planner-billing-retry>Retry</button></div>';
    } finally {
      if (requestRevision === revision) content.removeAttribute("aria-busy");
    }
  }

  document.addEventListener("click", function (event) {
    const trigger = event.target.closest("[data-planner-billing-url]");
    if (!trigger || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button > 0) return;
    event.preventDefault();
    triggers = Array.from(document.querySelectorAll("[data-planner-billing-url]"));
    currentIndex = triggers.indexOf(trigger);
    lastTrigger = trigger;
    if (!drawer.open) {
      drawer.showModal();
      document.body.classList.add("planner-billing-open");
    }
    closeButton.focus();
    load(trigger);
  });

  closeButton.addEventListener("click", function () { drawer.close(); });
  drawer.addEventListener("close", function () {
    stopRequest();
    content.innerHTML = "";
    content.removeAttribute("aria-busy");
    document.body.classList.remove("planner-billing-open");
    if (lastTrigger && lastTrigger.isConnected) lastTrigger.focus();
  });
  // Native dialog handles Escape and keyboard focus containment.
  drawer.addEventListener("click", function (event) {
    if (event.target !== drawer) return;
    const bounds = drawer.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) drawer.close();
  });
  content.addEventListener("click", function (event) {
    if (event.target.closest("[data-planner-billing-retry]") && triggers[currentIndex]) {
      closeButton.focus();
      load(triggers[currentIndex]);
    }
  });
  function step(offset) {
    const candidate = currentIndex + offset;
    if (!triggers[candidate]) return;
    currentIndex = candidate;
    lastTrigger = triggers[currentIndex];
    load(lastTrigger);
    // A disabled paging button cannot retain reliable keyboard focus at either end.
    if ((offset < 0 && previous.disabled) || (offset > 0 && next.disabled)) closeButton.focus();
  }
  previous.addEventListener("click", function () { step(-1); });
  next.addEventListener("click", function () { step(1); });
})();
