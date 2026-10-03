(() => {
  const reason = document.getElementById("id_revision_reason");
  const details = document.getElementById("id_revision_details");
  const container = document.getElementById("sc-revision-details");
  if (!reason || !details || !container) return;

  const updateDetailsRequirement = () => {
    const required = reason.value === "other";
    container.hidden = !required;
    details.disabled = !required;
    details.required = required;
    details.setAttribute("aria-required", String(required));
  };

  reason.addEventListener("change", updateDetailsRequirement);
  updateDetailsRequirement();
})();
