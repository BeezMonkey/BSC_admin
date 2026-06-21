(function () {
  const triggerSelector = ".js-shift-modal-trigger";
  const copySourceSelector = ".js-shift-copy-source";
  const pasteTargetSelector = ".js-shift-paste-target";
  const deleteTriggerSelector = ".js-shift-delete-trigger";
  const closeSelector = "[data-shift-modal-close]";
  const rootId = "shift-modal-root";
  let lastTrigger = null;
  let copiedShiftUrl = "";
  let pendingDeleteForm = null;

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
    pendingDeleteForm = null;
    if (lastTrigger) {
      lastTrigger.focus();
    }
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function deleteDetail(label, value) {
    if (!value) {
      return "";
    }
    return `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd>`;
  }

  function openDeleteConfirm(trigger) {
    const form = trigger.closest(".planner-shift-delete-form");
    if (!form) {
      return false;
    }

    pendingDeleteForm = form;
    lastTrigger = trigger;

    const details = [
      deleteDetail("Shift", trigger.dataset.deleteSummary),
      deleteDetail("Participant", trigger.dataset.deleteParticipant),
      deleteDetail("Worker", trigger.dataset.deleteWorker),
    ].join("");

    openModal(`
      <div class="shift-modal-backdrop" data-shift-modal-backdrop>
        <section class="shift-modal-dialog shift-delete-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="shift-delete-confirm-title">
          <header class="shift-modal-header">
            <div>
              <h2 id="shift-delete-confirm-title">Delete shift?</h2>
              <p>This will permanently remove this rostered shift.</p>
            </div>
            <button class="shift-modal-close" type="button" data-shift-modal-close aria-label="Close">&times;</button>
          </header>
          <div class="shift-modal-body">
            <div class="shift-delete-confirm-card">
              <dl>${details}</dl>
            </div>
          </div>
          <footer class="shift-modal-footer">
            <button class="button secondary" type="button" data-shift-modal-close>Cancel</button>
            <button class="shift-modal-delete-button" type="button" data-shift-delete-confirm>Delete Shift</button>
          </footer>
        </section>
      </div>
    `);
    return true;
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
    const deleteTrigger = event.target.closest(deleteTriggerSelector);
    if (deleteTrigger) {
      event.preventDefault();
      openDeleteConfirm(deleteTrigger);
      return;
    }

    if (event.target.closest("[data-shift-delete-confirm]")) {
      event.preventDefault();
      if (pendingDeleteForm) {
        pendingDeleteForm.submit();
      }
      return;
    }

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
