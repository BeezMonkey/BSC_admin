(function () {
  const triggerSelector = ".js-shift-modal-trigger";
  const closeSelector = "[data-shift-modal-close]";
  const rootId = "shift-modal-root";
  let lastTrigger = null;

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
