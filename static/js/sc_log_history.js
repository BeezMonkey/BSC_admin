(() => {
  const histories = document.querySelectorAll(".sc-log-history");
  histories.forEach((history) => {
    const entries = [...history.querySelectorAll("[data-history-text]")].map((wrapper) => ({
      wrapper,
      value: wrapper.querySelector("[data-history-text-value]"),
      button: wrapper.querySelector("[data-history-text-toggle]"),
    }));

    const setExpanded = (entry, expanded) => {
      entry.wrapper.classList.toggle("is-collapsed", !expanded);
      entry.button.setAttribute("aria-expanded", String(expanded));
      entry.button.textContent = expanded ? "Show less" : "Show full text";
      entry.button.setAttribute("aria-label", `${entry.button.textContent}: ${entry.wrapper.dataset.textLabel}`);
    };

    const measure = () => {
      entries.forEach((entry) => {
        if (!entry.value.getClientRects().length) return;
        if (entry.button.getAttribute("aria-expanded") === "true") return;
        setExpanded(entry, false);
        const overflowing = entry.value.scrollHeight > entry.value.clientHeight + 1;
        entry.button.hidden = !overflowing;
        if (!overflowing) entry.wrapper.classList.remove("is-collapsed");
      });
    };

    let scheduled = false;
    const scheduleMeasure = () => {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(() => {
        scheduled = false;
        measure();
      });
    };

    entries.forEach((entry) => {
      entry.button.addEventListener("click", () => {
        setExpanded(entry, entry.button.getAttribute("aria-expanded") !== "true");
        scheduleMeasure();
      });
    });
    history.addEventListener("toggle", scheduleMeasure, true);
    if (typeof ResizeObserver !== "undefined") {
      const observer = new ResizeObserver(scheduleMeasure);
      entries.forEach((entry) => observer.observe(entry.value));
    } else {
      window.addEventListener("resize", scheduleMeasure);
    }
    scheduleMeasure();
  });
})();
