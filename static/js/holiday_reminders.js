(function () {
  // Presentation only: this module never changes submitted fields or billing choices.
  const regions = ["QLD", "Brisbane", "Logan", "Gold Coast"];
  let data = { coverage: {}, holidays: {} };
  try {
    const element = document.getElementById("qld-holiday-data");
    const parsed = element && JSON.parse(element.textContent);
    if (parsed && parsed.coverage && parsed.holidays) data = parsed;
  } catch (_) {
    // Keep date selection usable if the reminder data cannot be read.
  }

  function holidaysOn(value) {
    return Array.isArray(data.holidays[value]) ? data.holidays[value] : [];
  }

  function regionLabel(holiday) {
    return holiday.region === "QLD" ? "QLD statewide" : `${holiday.region} only`;
  }

  function holidayLabel(holiday) {
    return `${holiday.name} | ${regionLabel(holiday)} | ${holiday.hours}`;
  }

  function coverageWarning(year) {
    const verified = data.coverage[String(year)] || [];
    const missing = regions.filter(function (region) { return !verified.includes(region); });
    return missing.length ? `${year} holiday dates not verified for ${missing.join(", ")}. Check the official calendar.` : "";
  }

  function paragraph(text, className) {
    const node = document.createElement("p");
    node.className = className;
    node.textContent = text;
    return node;
  }

  function decorateDay(button, value) {
    const holidays = holidaysOn(value);
    if (!holidays.length) return;
    const labels = holidays.map(holidayLabel).join("; ");
    button.classList.add(holidays.some(function (holiday) { return holiday.region === "QLD"; }) ? "holiday-statewide" : "holiday-regional");
    button.title = labels;
    button.setAttribute("aria-label", `${button.getAttribute("aria-label")}. ${labels}`);
  }

  function updateMonth(container, year, month, gridStart, gridEnd) {
    const list = container.querySelector("[data-calendar-holidays]");
    if (!list) return;
    list.replaceChildren();
    const prefix = `${year}-${String(month + 1).padStart(2, "0")}-`;
    Object.keys(data.holidays).filter(function (key) {
      return gridStart && gridEnd ? key >= gridStart && key <= gridEnd : key.startsWith(prefix);
    }).sort().forEach(function (key) {
      const parts = key.split("-").map(Number);
      const date = new Date(parts[0], parts[1] - 1, parts[2]);
      const label = date.toLocaleDateString("en-AU", { day: "numeric", month: "short", ...(parts[0] !== year ? { year: "numeric" } : {}) });
      holidaysOn(key).forEach(function (holiday) {
        list.append(paragraph(`${label}: ${holidayLabel(holiday)}`, holiday.region === "QLD" ? "holiday-statewide" : "holiday-regional"));
      });
    });
    const visibleYears = new Set([year]);
    if (gridStart && gridEnd) {
      visibleYears.add(Number(gridStart.slice(0, 4)));
      visibleYears.add(Number(gridEnd.slice(0, 4)));
    }
    visibleYears.forEach(function (visibleYear) {
      const warning = coverageWarning(visibleYear);
      if (warning) list.append(paragraph(warning, "holiday-coverage-warning"));
    });
    list.hidden = !list.children.length;
  }

  function updateSelected(container, value) {
    const selected = container.querySelector("[data-selected-holidays]");
    if (!selected) return;
    selected.replaceChildren();
    const holidays = holidaysOn(value);
    holidays.forEach(function (holiday) {
      const badge = document.createElement("span");
      badge.className = `holiday-badge ${holiday.region === "QLD" ? "holiday-statewide" : "holiday-regional"}`;
      const name = document.createElement("strong");
      name.textContent = holiday.name;
      const detail = document.createElement("small");
      detail.textContent = `${regionLabel(holiday)} | ${holiday.hours}`;
      badge.append(name, detail);
      selected.append(badge);
    });
    const warning = /^\d{4}-\d{2}-\d{2}$/.test(value) ? coverageWarning(Number(value.slice(0, 4))) : "";
    if (warning) selected.append(paragraph(warning, "holiday-coverage-warning"));
    selected.hidden = !selected.children.length;
    const form = container.closest("form");
    const reminder = form && form.querySelector("[data-holiday-item-reminder]");
    if (reminder) reminder.hidden = !holidays.length && !warning;
  }

  window.BscHolidayReminders = { decorateDay, updateMonth, updateSelected };
})();
