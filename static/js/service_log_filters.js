(() => {
  const form = document.querySelector("[data-service-log-filters]");
  if (!form) return;

  const range = form.elements.date_range;
  const start = form.elements.date_from;
  const end = form.elements.date_to;

  const validateDates = () => {
    const reversed = start.value && end.value && end.value < start.value;
    end.setCustomValidity(reversed ? "End date must be on or after start date." : "");
  };

  [start, end].forEach((input) => {
    input.addEventListener("input", () => {
      range.value = "custom";
      validateDates();
    });
  });

  range.addEventListener("change", () => {
    if (range.value !== "custom") {
      // The server resolves presets in the business timezone on submission.
      start.value = "";
      end.value = "";
    }
    validateDates();
  });
  validateDates();
})();
