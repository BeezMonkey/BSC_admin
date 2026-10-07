(function () {
  "use strict";
  var drawer = document.querySelector("[data-billing-drawer]");
  if (!drawer || typeof drawer.showModal !== "function") return;
  var body = drawer.querySelector("[data-drawer-body]");
  var discard = document.querySelector("[data-billing-discard]");
  var active = null;
  var controllers = [];

  function cents(value) {
    // Number inputs accept forms such as .50 and 1e2; normalize before integer arithmetic.
    var numeric = Number(value || "0");
    if (!Number.isFinite(numeric) || numeric < 0) return 0n;
    var text = numeric.toFixed(2);
    if (!/^\d+(\.\d{0,2})?$/.test(text)) return 0n;
    var parts = text.split(".");
    return BigInt(parts[0]) * 100n + BigInt((parts[1] || "").padEnd(2, "0"));
  }
  function decimal(value) { return String(value / 100n) + "." + String(value % 100n).padStart(2, "0"); }
  function serviceTotal(rate, hours) { return (cents(rate) * cents(hours) + 50n) / 100n; }
  function minutes(value) {
    if (!/^\d{2}:\d{2}/.test(value)) return NaN;
    var parts = value.split(":");
    return Number(parts[0]) * 60 + Number(parts[1]);
  }
  function updateForm(form) {
    var total = 0n;
    form.querySelectorAll("[data-invoice-row]").forEach(function (row) { total += cents(row.dataset.lineTotal); });
    var output = form.querySelector("[data-invoice-total]");
    if (output) output.textContent = "Invoice total: $" + decimal(total);
  }
  function fieldState(control) { return control.type === "checkbox" ? control.checked : control.value; }
  function textAt(root, selector, value) {
    var element = root.querySelector(selector);
    if (element) element.textContent = value;
  }
  function displayTime(value) {
    var hour = Number(value.split(":")[0]);
    return (hour % 12 || 12) + ":" + value.split(":")[1] + (hour < 12 ? "am" : "pm");
  }
  function finish(apply) {
    var current = active;
    if (!current) return;
    if (!apply) current.controls.forEach(function (control, index) {
      if (control.type === "checkbox") control.checked = current.snapshot[index];
      else control.value = current.snapshot[index];
    });
    current.claimHome.appendChild(current.claimField);
    current.details.appendChild(current.fields);
    current.details.open = false;
    current.item.dispatchEvent(new Event("change", { bubbles: true }));
    active = null;
    current.update();
    drawer.close();
    document.body.classList.remove("invoice-drawer-open");
    current.opener.focus();
  }
  function requestClose() {
    if (!active) return;
    var dirty = active.controls.some(function (control, index) { return fieldState(control) !== active.snapshot[index]; });
    if (dirty) discard.showModal();
    else finish(false);
  }
  function open(controller) {
    if (active) return;
    active = controller;
    controller.snapshot = controller.controls.map(fieldState);
    textAt(drawer, "[data-drawer-subtitle]", "Log #" + controller.row.dataset.logId + " | " + controller.row.dataset.serviceDate);
    drawer.querySelector("[data-drawer-before]").textContent = "$" + controller.row.dataset.lineTotal;
    // Move the real controls within their owning form, preserving one POST value per field.
    controller.form.appendChild(drawer);
    body.appendChild(controller.fields);
    controller.fields.querySelector("[data-billing-drawer-claim]").appendChild(controller.claimField);
    controller.update();
    drawer.showModal();
    body.scrollTop = 0;
    document.body.classList.add("invoice-drawer-open");
    drawer.querySelector("[data-drawer-close]").focus();
  }
  drawer.querySelector("[data-drawer-close]").addEventListener("click", requestClose);
  drawer.querySelector("[data-drawer-cancel]").addEventListener("click", requestClose);
  drawer.addEventListener("cancel", function (event) { event.preventDefault(); requestClose(); });
  drawer.addEventListener("click", function (event) {
    if (event.target === drawer && event.clientX < drawer.getBoundingClientRect().left) requestClose();
  });
  drawer.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && event.target.matches("input")) event.preventDefault();
  });
  discard.querySelector("[data-discard-keep]").onclick = function () { discard.close(); };
  discard.querySelector("[data-discard-confirm]").onclick = function () { discard.close(); finish(false); };
  drawer.querySelector("[data-drawer-apply]").onclick = function () {
    if (!active) return;
    active.update();
    for (var control of active.controls) {
      if (!control.disabled && !control.reportValidity()) return;
    }
    if (!active.valid) return;
    finish(true);
  };

  document.querySelectorAll("[data-invoice-row]").forEach(function (row) {
    var form = row.closest("form");
    var claim = row.querySelector("[data-billing-claim] input");
    if (!row.hasAttribute("data-billing-row")) {
      function legacyTotal() {
        row.dataset.lineTotal = decimal(serviceTotal(row.dataset.price, row.dataset.hours) + serviceTotal(drawer.dataset.travelPrice, claim && claim.value));
        row.querySelector("[data-billing-total]").textContent = row.dataset.lineTotal;
        updateForm(form);
      }
      if (claim) claim.addEventListener("input", legacyTotal);
      legacyTotal();
      return;
    }
    var fields = row.querySelector("[data-billing-fields]");
    var item = fields.querySelector("[data-billing-item] select");
    var km = fields.querySelector("[data-billing-km] input");
    var reason = fields.querySelector("[data-billing-reason] select");
    var other = fields.querySelector("[data-billing-other] textarea");
    var toggle = fields.querySelector('[name$="-correct_time"]');
    var start = fields.querySelector('[name$="-actual_start_time"]');
    var end = fields.querySelector('[name$="-actual_end_time"]');
    var pause = fields.querySelector('[name$="-break_minutes"]');
    var original = row.dataset;
    var controller = {
      row: row, form: form, fields: fields, item: item,
      details: row.querySelector("[data-billing-details]"),
      claimHome: row.querySelector("[data-billing-claim-home]"),
      claimField: row.querySelector("[data-billing-claim-field]"),
      opener: row.querySelector("[data-billing-open]"),
      controls: Array.from(fields.querySelectorAll("input[name], select[name], textarea[name]")).concat([claim]),
      valid: true
    };
    function update() {
      var selected = item.selectedOptions[0];
      var category = item.value && selected ? selected.dataset.category : original.originalCategory;
      var community = original.originalCategory === "Community access" || category === "Community access";
      var confirmedKm = km.value.trim() === "" ? Number(original.originalKm) : Number(km.value);
      var timeChanged = toggle.checked && (start.value !== original.originalStart || end.value !== original.originalEnd || Number(pause.value) !== Number(original.originalBreak));
      var duration = minutes(end.value) - minutes(start.value) - Number(pause.value);
      var validTime = !toggle.checked || (start.value && end.value && pause.value !== "" && Number(pause.value) >= 0 && Number.isInteger(Number(pause.value)) && duration > 0);
      var hours = validTime && timeChanged ? (Math.round(duration * 100 / 60) / 100).toFixed(2) : original.originalHours;
      var changed = Boolean(item.value && item.value !== original.originalItem) || confirmedKm !== Number(original.originalKm) || timeChanged;
      var price = item.value && selected ? selected.dataset.price : original.originalPrice;
      var showClaim = community || confirmedKm > 0 || Number(original.originalKm) > 0 || claim.value.trim() !== "" || original.billingErrors === "true";
      var validClaim = !Number(claim.value) || confirmedKm > 0;
      fields.querySelector("[data-billing-time-fields]").hidden = !toggle.checked;
      var timeSummary = fields.querySelector("[data-billing-time-summary]");
      if (timeSummary) timeSummary.hidden = toggle.checked;
      textAt(fields, "[data-billing-current-time]", displayTime(original.originalStart) + " - " + displayTime(original.originalEnd));
      textAt(fields, "[data-billing-current-break]", original.originalBreak + " min break | " + original.originalHours + " service hours");
      [start, end, pause].forEach(function (control) { control.disabled = !toggle.checked; control.required = toggle.checked; });
      end.setCustomValidity(validTime ? "" : "Check service times and break minutes.");
      claim.setCustomValidity(validClaim ? "" : "Enter confirmed kilometres before adding a travel claim.");
      fields.querySelector("[data-billing-time-error]").hidden = validTime;
      fields.querySelector("[data-billing-claim-error]").hidden = validClaim;
      controller.valid = Boolean(validTime && validClaim);
      controller.claimField.hidden = active === controller ? false : !showClaim;
      row.querySelector("[data-billing-claim-empty]").hidden = showClaim;
      claim.disabled = !showClaim && active !== controller;
      reason.required = changed;
      var isOther = reason.value === "other";
      fields.querySelector("[data-billing-other-field]").hidden = !isOther;
      other.disabled = !isOther;
      other.required = isOther && changed;
      fields.querySelector("[data-billing-reset-item]").hidden = !item.value || item.value === original.originalItem;
      row.querySelector("[data-billing-item-label]").textContent = item.value && selected ? selected.textContent : original.originalLabel;
      var pickerLabel = fields.querySelector(".support-item-picker-trigger-label");
      if (pickerLabel) {
        pickerLabel.dataset.invoiceItemName = item.value && selected ? selected.dataset.itemName : original.originalName;
        pickerLabel.dataset.invoiceItemCode = item.value && selected ? selected.dataset.itemCode : original.originalCode;
        // Keep the two-line visual label from repeating its CSS content to screen readers.
        var pickerTrigger = fields.querySelector(".support-item-picker-trigger");
        pickerLabel.setAttribute("aria-hidden", "true");
        pickerTrigger.removeAttribute("aria-labelledby");
        pickerTrigger.setAttribute("aria-label", "Billing support item: " + (item.value && selected ? selected.textContent : original.originalLabel));
        if (!item.value) {
          pickerLabel.textContent = original.originalLabel;
          pickerTrigger.classList.remove("is-placeholder");
        }
      }
      row.querySelector("[data-billing-adjusted]").hidden = !changed;
      row.querySelector("[data-billing-hours]").textContent = validTime ? hours : "-";
      row.querySelector("[data-billing-km-summary]").textContent = Number.isFinite(confirmedKm) ? confirmedKm.toFixed(2) : "-";
      row.querySelector("[data-billing-rate]").textContent = Number(price).toFixed(2);
      fields.querySelector("[data-billing-hours-preview]").textContent = validTime ? hours + " h" : "-";
      fields.querySelector("[data-billing-rate-preview]").textContent = "$" + Number(price).toFixed(2) + "/hr";
      var service = serviceTotal(price, hours);
      fields.querySelector("[data-billing-service-preview]").textContent = validTime ? "Service $" + decimal(service) : "-";
      row.dataset.lineTotal = decimal(service + serviceTotal(drawer.dataset.travelPrice, claim.value));
      row.querySelector("[data-billing-total]").textContent = controller.valid ? row.dataset.lineTotal : "-";
      if (active === controller) {
        drawer.querySelector("[data-drawer-after]").textContent = controller.valid ? "$" + row.dataset.lineTotal : "-";
        textAt(drawer, "[data-drawer-breakdown]", controller.valid ? "$" + decimal(service) + " service + $" + decimal(serviceTotal(drawer.dataset.travelPrice, claim.value)) + " travel" : "-");
        var dirty = controller.controls.some(function (control, index) { return fieldState(control) !== controller.snapshot[index]; });
        textAt(drawer, "[data-drawer-change-status]", dirty ? "Unsaved changes" : "No changes");
        drawer.querySelector("[data-drawer-apply]").disabled = !dirty;
      }
      updateForm(form);
    }
    controller.update = update;
    controller.opener.hidden = false;
    row.classList.add("invoice-drawer-ready");
    fields.classList.add("invoice-fields-enhanced");
    var editTime = fields.querySelector("[data-billing-edit-time]");
    var restoreTime = fields.querySelector("[data-billing-restore-time]");
    if (editTime && restoreTime) {
      editTime.hidden = false;
      restoreTime.hidden = false;
      editTime.onclick = function () {
        toggle.checked = true;
        toggle.dispatchEvent(new Event("change", { bubbles: true }));
        start.focus();
      };
      restoreTime.onclick = function () {
        start.value = original.originalStart;
        end.value = original.originalEnd;
        pause.value = original.originalBreak;
        toggle.checked = false;
        toggle.dispatchEvent(new Event("change", { bubbles: true }));
        editTime.focus();
      };
    }
    controller.opener.onclick = function () { open(controller); };
    fields.querySelector("[data-billing-reset-item]").onclick = function () {
      item.value = ""; item.dispatchEvent(new Event("change", { bubbles: true }));
    };
    controller.controls.forEach(function (control) {
      control.addEventListener("input", update);
      control.addEventListener("change", update);
      control.addEventListener("invalid", function () { if (!active) open(controller); });
    });
    controllers.push(controller);
    update();
  });
  document.querySelectorAll(".invoice-preview-table form").forEach(function (form) {
    form.addEventListener("submit", function (event) { if (active) event.preventDefault(); });
    updateForm(form);
  });
  var firstError = controllers.find(function (controller) { return controller.row.dataset.billingErrors === "true"; });
  if (firstError) open(firstError);
})();
