(function () {
  const wheelRowHeight = 32;
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  const dateFormatter = new Intl.DateTimeFormat("en-AU", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
  let activePicker = null;

  function parseDate(value) {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
    if (!match) return null;
    return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  }

  function isoDate(date) {
    return [
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0"),
    ].join("-");
  }

  function sameDate(first, second) {
    return Boolean(
      first && second &&
      first.getFullYear() === second.getFullYear() &&
      first.getMonth() === second.getMonth() &&
      first.getDate() === second.getDate()
    );
  }

  function parseTime(value) {
    const match = /^(\d{1,2}):(\d{2})/.exec(value || "");
    if (!match) return null;
    const hour = Number(match[1]);
    const minute = Number(match[2]);
    if (hour > 23 || minute > 59) return null;
    return hour * 60 + minute;
  }

  function formatTime(minutes) {
    const hour24 = Math.floor(minutes / 60);
    const minute = minutes % 60;
    const period = hour24 >= 12 ? "pm" : "am";
    const hour12 = hour24 % 12 || 12;
    return `${hour12}:${String(minute).padStart(2, "0")} ${period}`;
  }

  function draftFromMinutes(minutes) {
    const hour24 = Math.floor(minutes / 60);
    return {
      hour: hour24 % 12 || 12,
      minute: minutes % 60,
      period: hour24 >= 12 ? "pm" : "am",
    };
  }

  function minutesFromDraft(draft) {
    const hour24 = (draft.hour % 12) + (draft.period === "pm" ? 12 : 0);
    return hour24 * 60 + draft.minute;
  }

  function announceChange(input) {
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function closePicker() {
    if (!activePicker) return;
    activePicker.popover.hidden = true;
    activePicker.trigger.setAttribute("aria-expanded", "false");
    activePicker = null;
  }

  function placePopover(instance) {
    instance.popover.classList.remove("open-up");
    requestAnimationFrame(function () {
      const popoverRect = instance.popover.getBoundingClientRect();
      const triggerRect = instance.trigger.getBoundingClientRect();
      const scrollContainer = instance.trigger.closest(".shift-modal-body");
      const scrollRect = scrollContainer
        ? scrollContainer.getBoundingClientRect()
        : null;
      const visibleBottom = Math.min(
        window.innerHeight - 12,
        scrollRect ? scrollRect.bottom - 12 : window.innerHeight - 12
      );
      const visibleTop = scrollRect ? scrollRect.top + 12 : 12;
      if (
        window.innerWidth > 700 &&
        popoverRect.bottom > visibleBottom &&
        triggerRect.top - popoverRect.height > visibleTop
      ) {
        instance.popover.classList.add("open-up");
      }
    });
  }

  function openPicker(instance) {
    const wasOpen = activePicker === instance;
    closePicker();
    if (wasOpen) return;
    instance.prepare();
    instance.popover.hidden = false;
    instance.trigger.setAttribute("aria-expanded", "true");
    activePicker = instance;
    instance.afterOpen();
    placePopover(instance);
  }

  function setDisplay(display, text, hasValue) {
    display.textContent = text;
    display.classList.toggle("date-time-picker-placeholder", !hasValue);
  }

  function createCalendarPicker(container) {
    const input = container.querySelector("input[type='hidden']");
    const trigger = container.querySelector("[data-picker-trigger]");
    const display = container.querySelector("[data-picker-display]");
    const popover = container.querySelector("[data-picker-popover]");
    const title = container.querySelector("[data-calendar-title]");
    const grid = container.querySelector("[data-calendar-grid]");
    const today = new Date();
    let selectedDate = parseDate(input.value);
    let visibleMonth = selectedDate
      ? new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1)
      : new Date(today.getFullYear(), today.getMonth(), 1);

    function updateDisplay() {
      setDisplay(display, selectedDate ? dateFormatter.format(selectedDate) : "Select date", Boolean(selectedDate));
    }

    function selectDate(date) {
      selectedDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
      visibleMonth = new Date(date.getFullYear(), date.getMonth(), 1);
      input.value = isoDate(selectedDate);
      updateDisplay();
      render();
      announceChange(input);
      closePicker();
    }

    function render() {
      title.textContent = `${monthNames[visibleMonth.getMonth()]} ${visibleMonth.getFullYear()}`;
      grid.replaceChildren();
      const firstOfMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth(), 1);
      const mondayOffset = (firstOfMonth.getDay() + 6) % 7;
      const daysInMonth = new Date(
        visibleMonth.getFullYear(),
        visibleMonth.getMonth() + 1,
        0
      ).getDate();
      const cellCount = mondayOffset + daysInMonth > 35 ? 42 : 35;
      const gridStart = new Date(firstOfMonth);
      gridStart.setDate(firstOfMonth.getDate() - mondayOffset);

      for (let index = 0; index < cellCount; index += 1) {
        const date = new Date(gridStart);
        date.setDate(gridStart.getDate() + index);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "calendar-day";
        button.textContent = date.getDate();
        button.setAttribute("aria-label", dateFormatter.format(date));
        if (date.getMonth() !== visibleMonth.getMonth()) button.classList.add("outside");
        if (date.getDay() === 0 || date.getDay() === 6) button.classList.add("weekend");
        if (sameDate(date, today)) button.classList.add("today");
        if (sameDate(date, selectedDate)) {
          button.classList.add("selected");
          button.setAttribute("aria-current", "date");
        }
        button.addEventListener("click", function () { selectDate(date); });
        grid.append(button);
      }
    }

    const instance = {
      popover: popover,
      trigger: trigger,
      prepare: function () {
        selectedDate = parseDate(input.value);
        if (selectedDate) {
          visibleMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1);
        }
        render();
      },
      afterOpen: function () {},
    };

    trigger.addEventListener("click", function () { openPicker(instance); });
    container.querySelector("[data-calendar-previous]").addEventListener("click", function () {
      visibleMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() - 1, 1);
      render();
    });
    container.querySelector("[data-calendar-next]").addEventListener("click", function () {
      visibleMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() + 1, 1);
      render();
    });
    container.querySelector("[data-calendar-today]").addEventListener("click", function () {
      selectDate(today);
    });
    container.querySelector("[data-calendar-clear]").addEventListener("click", function () {
      selectedDate = null;
      input.value = "";
      updateDisplay();
      announceChange(input);
      closePicker();
    });

    updateDisplay();
    render();
    return instance;
  }

  function createTimePicker(container) {
    const input = container.querySelector("input[type='hidden']");
    const trigger = container.querySelector("[data-picker-trigger]");
    const display = container.querySelector("[data-picker-display]");
    const popover = container.querySelector("[data-picker-popover]");
    const isEndTime = input.name.endsWith("end_time");
    const valuesByPart = {
      hour: Array.from({ length: 12 }, function (_, index) { return index + 1; }),
      minute: Array.from({ length: 12 }, function (_, index) { return index * 5; }),
      period: ["am", "pm"],
    };
    const columns = {};
    const scrollTimers = new WeakMap();
    let draft = draftFromMinutes(isEndTime ? 17 * 60 : 9 * 60);

    function selectedMinutes() {
      return parseTime(input.value);
    }

    function updateDisplay() {
      const minutes = selectedMinutes();
      setDisplay(display, minutes === null ? "Select time" : formatTime(minutes), minutes !== null);
    }

    function updateWheels(align) {
      Object.keys(valuesByPart).forEach(function (part) {
        const column = columns[part];
        const values = valuesByPart[part];
        const selectedIndex = values.findIndex(function (value) { return value === draft[part]; });
        column.querySelectorAll("[data-wheel-value]").forEach(function (button, index) {
          button.classList.toggle("selected", index === selectedIndex);
          button.classList.toggle("near", Math.abs(index - selectedIndex) === 1);
          button.setAttribute("aria-selected", index === selectedIndex ? "true" : "false");
        });
        if (align && selectedIndex >= 0) {
          column.scrollTo({ top: selectedIndex * wheelRowHeight, behavior: "auto" });
        }
      });
    }

    Object.keys(valuesByPart).forEach(function (part) {
      const column = container.querySelector(`[data-wheel-part="${part}"]`);
      const values = valuesByPart[part];
      columns[part] = column;
      values.forEach(function (value, index) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "time-wheel-option";
        button.dataset.wheelValue = String(value);
        button.textContent = part === "period"
          ? String(value).toUpperCase()
          : part === "minute"
            ? String(value).padStart(2, "0")
            : String(value);
        button.addEventListener("click", function () {
          draft[part] = value;
          updateWheels(false);
          column.scrollTo({ top: index * wheelRowHeight, behavior: "smooth" });
        });
        column.append(button);
      });
      column.addEventListener("scroll", function () {
        clearTimeout(scrollTimers.get(column));
        scrollTimers.set(column, setTimeout(function () {
          const index = Math.max(0, Math.min(
            values.length - 1,
            Math.round(column.scrollTop / wheelRowHeight)
          ));
          draft[part] = values[index];
          updateWheels(false);
          column.scrollTo({ top: index * wheelRowHeight, behavior: "smooth" });
        }, 90));
      });
    });

    const instance = {
      popover: popover,
      trigger: trigger,
      prepare: function () {
        let minutes = selectedMinutes();
        if (minutes === null && isEndTime) {
          const form = container.closest("form");
          const startInput = form && form.querySelector("input[name$='start_time']");
          const startMinutes = startInput ? parseTime(startInput.value) : null;
          minutes = startMinutes === null ? 17 * 60 : Math.min(startMinutes + 60, 23 * 60 + 55);
        }
        if (minutes === null) minutes = 9 * 60;
        draft = draftFromMinutes(minutes);
      },
      afterOpen: function () {
        requestAnimationFrame(function () { updateWheels(true); });
      },
    };

    trigger.addEventListener("click", function () { openPicker(instance); });
    container.querySelector("[data-time-cancel]").addEventListener("click", closePicker);
    container.querySelector("[data-time-apply]").addEventListener("click", function () {
      const minutes = minutesFromDraft(draft);
      input.value = `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
      updateDisplay();
      announceChange(input);
      closePicker();
    });

    updateDisplay();
    updateWheels(true);
    return instance;
  }

  function initDateTimePickers(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-date-time-picker]:not([data-picker-initialized])").forEach(function (container) {
      container.dataset.pickerInitialized = "true";
      if (container.dataset.dateTimePicker === "date") {
        createCalendarPicker(container);
      } else {
        createTimePicker(container);
      }
    });
  }

  document.addEventListener("click", function (event) {
    if (activePicker && !activePicker.popover.parentElement.contains(event.target)) {
      closePicker();
    }
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closePicker();
  });

  window.initDateTimePickers = initDateTimePickers;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { initDateTimePickers(document); });
  } else {
    initDateTimePickers(document);
  }
})();
