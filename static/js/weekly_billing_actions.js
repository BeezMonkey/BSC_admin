/* Same-page coordination; the server remains the authority for reviews and billing. */
(() => {
  "use strict";
  const requiresReason = action => action === "return" || action === "cancel_reject";
  function selectToken(form) {
    const fields = form.elements;
    if (fields.preview_token && fields.period_mode) {
      fields.preview_token.value = fields["preview_token_" + fields.period_mode.value].value;
    }
  }
  function markStale(preview) {
    preview.dataset.stale = "true";
    const create = preview.querySelector("[data-wb-create]");
    const warning = preview.querySelector("[data-wb-stale]");
    if (create) create.disabled = true;
    if (warning) warning.hidden = false;
  }
  function openReview(scope, hash) {
    if (!/^#review-(log|cancellation)-\d+$/.test(hash)) return false;
    const detail = scope.querySelector(hash);
    if (!detail) return false;
    detail.open = true;
    detail.querySelector("summary")?.focus({ preventScroll: true });
    return true;
  }
  const api = { requiresReason, selectToken, markStale, openReview };
  window.WeeklyBillingActions = api;
  const root = document.querySelector("[data-weekly-billing]");
  if (!root || root.dataset.actionsReady) return;
  root.dataset.actionsReady = "true";
  const snapshots = new WeakMap();
  let inFlight = false;
  let leaving = false;
  const forms = () => [...root.querySelectorAll("form[data-wb-action]")];
  function signature(form) {
    return JSON.stringify([...form.querySelectorAll("input[name], select[name], textarea[name]")]
      .filter(control => control.name !== "csrfmiddlewaretoken" && control.name !== "preview_token")
      .map(control => [control.name, control.type === "checkbox" ? control.checked : control.value])
      .sort(([first], [second]) => first.localeCompare(second)));
  }
  function dirty(form) { return form.dataset.wbUnsaved === "true" || snapshots.has(form) && signature(form) !== snapshots.get(form); }
  function hasChanges() {
    return forms().some(dirty) || Boolean(window.InvoiceBilling?.hasUnappliedChanges());
  }
  function initialize(scope) {
    window.SupportItemPicker?.initWithin(scope);
    window.InvoiceBilling?.initWithin(scope);
    window.R1InvoiceAdjustmentTime?.initWithin(scope);
    scope.querySelectorAll("form[data-wb-action]").forEach(form => {
      selectToken(form);
      if (!snapshots.has(form)) snapshots.set(form, signature(form));
    });
  }
  function feedback(message, error = false) {
    const output = root.querySelector("[data-wb-feedback]");
    if (!output) return;
    output.textContent = message; output.hidden = false;
    output.classList.toggle("wb-error", error);
    output.setAttribute("role", error ? "alert" : "status");
  }
  function destroy(scope) {
    window.R1InvoiceAdjustmentTime?.destroyWithin(scope);
    window.InvoiceBilling?.destroyWithin(scope);
    window.SupportItemPicker?.destroyWithin(scope);
  }
  function detailKey(detail) {
    if (detail.id) return detail.id;
    const row = detail.closest("[data-log-id]");
    if (row) return "log-" + row.dataset.logId + "-" + [...row.querySelectorAll("details")].indexOf(detail);
    return "";
  }
  function refresh(payload, status) {
    const next = new DOMParser().parseFromString(payload.html, "text/html").querySelector("[data-wb-results]");
    const previous = root.querySelector("[data-wb-results]");
    if (!next || !previous) throw new Error("The workbench response was incomplete. Please retry.");
    const x = window.scrollX; const y = window.scrollY;
    const opened = new Map([...previous.querySelectorAll("details")].map(detail => [detailKey(detail), detail.open]));
    const scroll = new Map([...previous.querySelectorAll("[role=region]")].map(region => [region.getAttribute("aria-label"), [region.scrollLeft, region.scrollTop]]));
    const notes = new Map([...previous.querySelectorAll("textarea[data-wb-reason]")].map(input => {
      const form = input.closest("form");
      return [input.id, { value: input.value, baseline: snapshots.get(form), unsaved: form.dataset.wbUnsaved }];
    }));
    const oldParticipants = new Map([...previous.querySelectorAll("[data-wb-participant]")].map(node => [node.dataset.wbParticipant, node]));
    next.querySelectorAll("[data-wb-participant]").forEach(participant => {
      const old = oldParticipants.get(participant.dataset.wbParticipant);
      if (!old) return;
      const targeted = participant.dataset.wbParticipant === String(payload.participant_id);
      const replacePreview = targeted && (payload.action === "preview" || payload.action === "create") && status !== 409;
      const oldSlot = old.querySelector("[data-wb-preview-slot]");
      if (!replacePreview && oldSlot) {
        const freshSlot = participant.querySelector("[data-wb-preview-slot]");
        const freshRefresh = freshSlot.querySelector("[data-wb-refresh]");
        const oldRefresh = oldSlot.querySelector("[data-wb-refresh]");
        if (freshRefresh && oldRefresh) oldRefresh.replaceWith(freshRefresh);
        freshSlot.replaceWith(oldSlot);
        const preview = oldSlot.querySelector("[data-wb-preview]");
        if (preview && freshRefresh) {
          const refreshButton = freshRefresh.querySelector("button[type=submit]");
          refreshButton.disabled = false;
          refreshButton.textContent = "Refresh preview";
        }
        if (preview && (old.dataset.sourceKey !== participant.dataset.sourceKey || (targeted && status === 409))) markStale(preview);
      }
    });
    // Retained preview nodes have already moved out, so teardown only visits discarded controls.
    destroy(previous);
    previous.replaceWith(next);
    next.querySelectorAll("textarea[data-wb-reason]").forEach(input => {
      const retained = notes.get(input.id);
      if (!retained) return;
      input.value = retained.value;
      const form = input.closest("form");
      if (retained.baseline !== undefined) snapshots.set(form, retained.baseline);
      if (retained.unsaved === "true") form.dataset.wbUnsaved = "true";
    });
    initialize(next);
    next.querySelectorAll("details").forEach(detail => {
      const key = detailKey(detail);
      if (key && opened.has(key)) detail.open = opened.get(key);
    });
    const target = next.querySelector('[data-wb-participant="' + payload.participant_id + '"]');
    if (target && (payload.action === "preview" || (payload.action === "create" && status !== 200))) target.open = true;
    next.querySelectorAll("[role=region]").forEach(region => {
      const position = scroll.get(region.getAttribute("aria-label"));
      if (position) [region.scrollLeft, region.scrollTop] = position;
    });
    window.scrollTo(x, y);
  }
  api.refresh = refresh;
  api.initWithin = initialize;
  api.hasChanges = hasChanges;
  root.addEventListener("click", event => {
    const button = event.target.closest("button[name=action]");
    if (!button || !button.form?.matches("[data-wb-action]")) return;
    const reason = button.form.querySelector("[data-wb-reason]");
    if (reason) {
      reason.required = requiresReason(button.value);
      reason.setCustomValidity(reason.required && !reason.value.trim() ? "Enter a reason for this decision." : "");
    }
  });
  root.addEventListener("input", event => {
    if (event.target.matches("[data-wb-reason]")) event.target.setCustomValidity("");
  });
  root.addEventListener("change", event => {
    if (event.target.name === "period_mode") selectToken(event.target.form);
  });
  root.addEventListener("submit", async event => {
    const form = event.target;
    if (form.matches("[data-weekly-billing-filters]")) {
      if (!event.defaultPrevented && hasChanges() && !window.confirm("Leave this billing period and discard unsaved billing changes?")) event.preventDefault();
      else if (!event.defaultPrevented) leaving = true;
      return;
    }
    if (!form.matches("[data-wb-action]") || event.defaultPrevented) return;
    event.preventDefault();
    if (inFlight || window.InvoiceBilling?.isOpen()) return;
    const action = event.submitter?.value || form.elements.action?.value;
    if (!action) return;
    const participant = form.closest("[data-wb-participant]");
    const preview = participant?.querySelector("[data-wb-preview]");
    if (action === "preview" && participant && [...participant.querySelectorAll("form[data-wb-action]")].some(dirty) &&
        !window.confirm("Refresh this preview and discard its unsaved billing changes?")) return;
    if (action === "create") {
      if (preview?.dataset.stale === "true") { feedback("Refresh this preview before creating a draft.", true); return; }
      selectToken(form);
      if (!window.confirm("Create one draft invoice for " + form.dataset.participantName + " with these records and adjustments?")) return;
    }
    const reason = form.querySelector("[data-wb-reason]");
    if (reason) {
      reason.required = requiresReason(action);
      reason.setCustomValidity(reason.required && !reason.value.trim() ? "Enter a reason for this decision." : "");
    }
    if (!form.reportValidity()) return;
    const body = new FormData(form); body.set("action", action);
    const disabled = [...root.querySelectorAll("form[data-wb-action] button[type=submit]")].map(button => [button, button.disabled]);
    inFlight = true; disabled.forEach(([button]) => { button.disabled = true; });
    feedback("Working…");
    try {
      // Named action buttons/inputs can shadow HTMLFormElement.action.
      const response = await fetch(form.getAttribute("action") || window.location.href, { method: "POST", body,
        credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest", "Accept": "application/json" } });
      if (response.status === 403) throw new Error("This action is no longer authorized. Reload the page and sign in again before retrying.");
      const invalidResponse = "The workbench could not load its response. Your inputs are retained. Please retry; if this continues, reload the page.";
      if (!(response.headers.get("content-type") || "").toLowerCase().includes("application/json")) throw new Error(invalidResponse);
      let payload;
      try { payload = await response.json(); }
      catch (_) { throw new Error(invalidResponse); }
      if (payload.html) refresh(payload, response.status);
      else throw new Error(payload.message || "The workbench response was incomplete. Please retry.");
    } catch (error) {
      feedback(error.message || "The request could not be completed. Your inputs are retained; please retry.", true);
    } finally {
      inFlight = false;
      disabled.forEach(([button, wasDisabled]) => {
        if (button.isConnected) button.disabled = wasDisabled || button.closest("[data-wb-preview]")?.dataset.stale === "true" && button.matches("[data-wb-create]");
      });
    }
  });
  document.addEventListener("click", event => {
    const link = event.target.closest("a[href]");
    if (!link || link.target === "_blank" || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.getAttribute("href").startsWith("#")) return;
    if (hasChanges() && !window.confirm("Leave the workbench and discard unsaved billing changes?")) event.preventDefault();
    else leaving = true;
  });
  // Delegate because review rows are replaced after same-page decisions.
  root.addEventListener("click", event => {
    const link = event.target.closest("a[data-wb-review-link]");
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const hash = link.getAttribute("href");
    if (openReview(root, hash)) {
      // Native repeated fragment navigation can move keyboard focus back to body.
      event.preventDefault();
      if (window.location.hash !== hash) window.history.pushState(null, "", hash);
      root.querySelector(hash).scrollIntoView({ block: "start" });
    }
  });
  window.addEventListener("hashchange", () => openReview(root, window.location.hash));
  document.addEventListener("submit", event => {
    if (root.contains(event.target) || event.defaultPrevented) return;
    if (hasChanges() && !window.confirm("Leave the workbench and discard unsaved billing changes?")) event.preventDefault();
    else leaving = true;
  });
  window.addEventListener("beforeunload", event => {
    if (!leaving && (inFlight || hasChanges())) { event.preventDefault(); event.returnValue = ""; }
  });
  initialize(root);
  openReview(root, window.location.hash);
})();
