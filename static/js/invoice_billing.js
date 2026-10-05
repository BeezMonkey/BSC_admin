(function () {
  "use strict";

  function hundredths(value) {
    var text = String(value);
    var negative = text[0] === "-";
    var parts = (negative ? text.slice(1) : text).split(".");
    var scaled = BigInt(parts[0]) * 100n + BigInt((parts[1] || "").padEnd(2, "0"));
    return negative ? -scaled : scaled;
  }

  function serviceTotal(rate, hours) {
    // Both stored values have two decimal places; round half-up without binary floats.
    var product = hundredths(rate) * hundredths(hours);
    var negative = product < 0n;
    var cents = ((negative ? -product : product) + 50n) / 100n;
    return (negative && cents ? "-" : "") + String(cents / 100n) + "." + String(cents % 100n).padStart(2, "0");
  }

  document.querySelectorAll("[data-billing-row]").forEach(function (row) {
    var item = row.querySelector("[data-billing-item] select");
    var km = row.querySelector("[data-billing-km] input");
    var claim = row.querySelector("[data-billing-claim] input");
    var reason = row.querySelector("[data-billing-reason] select");
    var other = row.querySelector("[data-billing-other] textarea");
    var details = row.querySelector("[data-billing-details]");
    var resetItem = row.querySelector("[data-billing-reset-item]");
    var original = row.dataset;
    var originalOption = Array.from(item.options).find(function (option) {
      return option.value === original.originalItem;
    });
    var originalCategory = originalOption ? originalOption.dataset.category : original.originalCategory;

    function update() {
      var selected = item.selectedOptions[0];
      var category = item.value && selected ? selected.dataset.category : originalCategory;
      var community = originalCategory === "Community access" || category === "Community access";
      var confirmedKm = km.value.trim() === "" ? Number(original.originalKm) : Number(km.value);
      var changed = Boolean(item.value && item.value !== original.originalItem) || confirmedKm !== Number(original.originalKm);
      var hasErrors = original.billingErrors === "true";
      var priceText = item.value && selected ? selected.dataset.price : original.originalPrice;
      var price = Number(priceText);
      var showClaim = community || confirmedKm > 0 || Number(original.originalKm) > 0 || claim.value.trim() !== "" || hasErrors;
      var kmField = row.querySelector("[data-billing-km-field]");
      var kmTarget = row.querySelector(community ? "[data-billing-km-slot]" : "[data-billing-km-home]");

      // Move the single control; never clone prefixed fields or rewrite entered amounts.
      if (kmField.parentElement !== kmTarget) kmTarget.appendChild(kmField);
      row.querySelector("[data-billing-claim-field]").hidden = !showClaim;
      row.querySelector("[data-billing-claim-empty]").hidden = showClaim;
      claim.disabled = !showClaim;
      reason.required = changed;
      resetItem.hidden = !item.value || item.value === original.originalItem;

      var isOther = reason.value === "other";
      row.querySelector("[data-billing-other-field]").hidden = !isOther;
      other.disabled = !isOther;
      other.required = isOther && changed;

      row.querySelector("[data-billing-item-label]").textContent = item.value && selected ? selected.textContent : original.originalLabel;
      if (Number.isFinite(price)) {
        row.querySelector("[data-billing-rate]").textContent = price.toFixed(2);
        row.querySelector("[data-billing-total]").textContent = serviceTotal(priceText, original.hours);
      }
      if (hasErrors || (changed && !reason.value)) details.open = true;
    }

    resetItem.addEventListener("click", function () {
      item.value = "";
      item.dispatchEvent(new Event("change", { bubbles: true }));
    });
    [item, km, claim, reason, other].forEach(function (field) {
      field.addEventListener("change", update);
      field.addEventListener("input", update);
      field.addEventListener("invalid", function () { details.open = true; });
    });
    update();
  });
})();
