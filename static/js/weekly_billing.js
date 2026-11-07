/* Period control behavior only. Preset dates remain resolved by the server. */
(() => {
  "use strict";
  const form = document.querySelector("[data-weekly-billing-filters]");
  if (!form) return;
  const { period, start, end } = form.elements;
  let applyingPreset = false;

  const validateDates = (complete = false) => {
    const custom = period.value === "custom";
    const reversed = custom && start.value && end.value && end.value < start.value;
    start.setCustomValidity(custom && complete && !start.value ? "Enter both dates for a custom period." : "");
    end.setCustomValidity(reversed ? "End date must be on or after start date." :
      custom && complete && !end.value ? "Enter both dates for a custom period." : "");
    // Resync the shared adapter after validity changes without creating input loops.
    [start, end].forEach(input => input.dispatchEvent(new Event("invoice-date-sync")));
  };
  [start, end].forEach(input => {
    const edited = () => {
      if (!applyingPreset) period.value = "custom";
      // A date edit replaces bound errors for this pair with current validation.
      [start, end].forEach(date => date.dispatchEvent(new Event("invoice-date-clear-error")));
      validateDates();
    };
    input.addEventListener("input", edited);
    input.addEventListener("change", edited);
  });
  period.addEventListener("change", () => {
    if (period.value !== "custom") {
      applyingPreset = true;
      [start, end].forEach(input => {
        input.value = "";
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
      applyingPreset = false;
    }
    validateDates();
  });
  form.addEventListener("submit", event => {
    validateDates(true);
    if (!form.reportValidity()) event.preventDefault();
  });
  validateDates();
})();
