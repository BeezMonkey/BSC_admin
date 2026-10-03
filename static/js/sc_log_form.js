(function () {
  "use strict";

  document.querySelectorAll('.sc-service-duration input[type="number"]').forEach(function (input) {
    let clearedZero = false;

    function restoreZero() {
      if (clearedZero && input.value === "" && !input.validity.badInput) {
        input.value = "0";
      }
      clearedZero = false;
    }

    input.addEventListener("focus", function () {
      clearedZero = input.value === "0";
      if (clearedZero) input.value = "";
    });
    input.addEventListener("blur", restoreZero);
    // Enter can submit while the temporarily empty input still has focus.
    if (input.form) input.form.addEventListener("submit", restoreZero);
  });
})();
