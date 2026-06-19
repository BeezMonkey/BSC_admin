(function () {
  const triggerSelector = ".js-shift-modal-trigger";
  const copySourceSelector = ".js-shift-copy-source";
  const pasteTargetSelector = ".js-shift-paste-target";
  const closeSelector = "[data-shift-modal-close]";
  const rootId = "shift-modal-root";
  let lastTrigger = null;
  let copiedShiftUrl = "";

  function copiedShiftUrlForDate(serviceDate, includeModal) {
    const url = new URL(copiedShiftUrl, window.location.origin);
    url.searchParams.set("service_date", serviceDate);
    if (includeModal) {
      url.searchParams.set("modal", "1");
    } else {
      url.searchParams.delete("modal");
    }
    return `${url.pathname}?${url.searchParams.toString()}`;
  }

  function showPasteTargets() {
    document.querySelectorAll(pasteTargetSelector).forEach(function (target) {
      target.classList.remove("planner-paste-shift-hidden");
      target.removeAttribute("hidden");
    });
  }

  function markCopiedShift(trigger) {
    document.querySelectorAll(copySourceSelector).forEach(function (source) {
      source.classList.remove("planner-shift-action-active");
    });
    trigger.classList.add("planner-shift-action-active");
    copiedShiftUrl = trigger.dataset.copyUrl || trigger.href;
    showPasteTargets();
  }

  function modalRoot() {
    let root = document.getElementById(rootId);
    if (!root) {
      root = document.createElement("div");
      root.id = rootId;
      document.body.appendChild(root);
    }
    return root;
  }

  function focusFirstField() {
    const root = modalRoot();
    const firstField = root.querySelector(
      "select:not([disabled]), input:not([type='hidden']):not([disabled]), textarea:not([disabled]), button:not([disabled])"
    );
    if (firstField) {
      firstField.focus();
    }
  }

  function openModal(html) {
    const root = modalRoot();
    root.innerHTML = html;
    document.body.classList.add("shift-modal-open");
    focusFirstField();
  }

  function closeModal() {
    const root = modalRoot();
    root.innerHTML = "";
    document.body.classList.remove("shift-modal-open");
    if (lastTrigger) {
      lastTrigger.focus();
    }
  }

  async function loadModal(trigger) {
    const url = trigger.dataset.modalUrl || trigger.href;
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    if (!response.ok) {
      window.location.href = trigger.href;
      return;
    }
    openModal(await response.text());
  }

  async function submitModal(form) {
    const response = await fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });

    const contentType = response.headers.get("content-type") || "";
    if (response.ok && contentType.includes("application/json")) {
      const data = await response.json();
      if (data.ok) {
        closeModal();
        window.location.reload();
        return;
      }
    }

    openModal(await response.text());
  }

  document.addEventListener("click", function (event) {
    const copySource = event.target.closest(copySourceSelector);
    if (copySource) {
      event.preventDefault();
      markCopiedShift(copySource);
      return;
    }

    const pasteTarget = event.target.closest(pasteTargetSelector);
    if (pasteTarget && copiedShiftUrl) {
      event.preventDefault();
      lastTrigger = pasteTarget;
      const pasteUrl = copiedShiftUrlForDate(pasteTarget.dataset.serviceDate, false);
      const pasteModalUrl = copiedShiftUrlForDate(pasteTarget.dataset.serviceDate, true);
      loadModal({
        href: pasteUrl,
        dataset: { modalUrl: pasteModalUrl },
      }).catch(function () {
        window.location.href = pasteUrl;
      });
      return;
    }

    const trigger = event.target.closest(triggerSelector);
    if (trigger) {
      event.preventDefault();
      lastTrigger = trigger;
      loadModal(trigger).catch(function () {
        window.location.href = trigger.href;
      });
      return;
    }

    if (event.target.closest(closeSelector)) {
      event.preventDefault();
      closeModal();
      return;
    }

    if (event.target.matches("[data-shift-modal-backdrop]")) {
      closeModal();
    }
  });

  document.addEventListener("submit", function (event) {
    const form = event.target.closest(".js-shift-modal-form");
    if (!form) {
      return;
    }
    event.preventDefault();
    submitModal(form).catch(function () {
      form.submit();
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && document.body.classList.contains("shift-modal-open")) {
      closeModal();
    }
  });
})();
