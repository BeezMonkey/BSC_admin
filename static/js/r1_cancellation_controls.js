(function () {
  "use strict";

  const pad = value => String(value).padStart(2, "0");
  const months = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];

  function formatDateTime(value) {
    const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
    if (!match) return "Select date and time";
    const hour = Number(match[4]);
    return `${match[3]}/${match[2]}/${match[1]} ${pad(hour % 12 || 12)}:${match[5]} ${hour >= 12 ? "PM" : "AM"}`;
  }

  function composeDateTime(date, hour, minute, period) {
    if (!date) return "";
    return `${date}T${pad(Number(hour) % 12 + (period === "PM" ? 12 : 0))}:${minute}`;
  }

  function localDateValue(date) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }

  document.querySelectorAll(".r1-cancellation [data-cancellation-datetime]").forEach(function (root) {
    if (typeof window.initDateTimePickers !== "function") return;
    const input = root.querySelector("input[type='datetime-local']");
    const trigger = root.querySelector("[data-cancellation-datetime-trigger]");
    const popover = root.querySelector("[data-cancellation-datetime-popover]");
    const calendarHost = root.querySelector("[data-cancellation-calendar]");
    const template = root.querySelector("[data-cancellation-calendar-template]");
    const display = root.querySelector("[data-cancellation-display]");
    const invalid = root.querySelector("[data-cancellation-invalid]");
    const apply = root.querySelector("[data-cancellation-datetime-apply]");
    const timeHost = root.querySelector("[data-cancellation-time]");
    const serverInvalid = input.getAttribute("aria-invalid") === "true";
    const parts = {};
    let dateInput = null;
    let frame = null;
    let observer = null;

    [
      ["hour", "Hour", Array.from({ length: 12 }, (_, index) => String(index + 1))],
      ["minute", "Minute", Array.from({ length: 60 }, (_, index) => pad(index))],
      ["period", "Period", ["AM", "PM"]],
    ].forEach(function ([part, caption, values]) {
      const label = document.createElement("label");
      label.textContent = caption;
      const select = document.createElement("select");
      select.setAttribute(`data-cancellation-${part}`, "");
      values.forEach(function (value) { select.add(new Option(value, value)); });
      label.append(select);
      timeHost.append(label);
      parts[part] = select;
    });

    function syncDisplay() {
      display.textContent = formatDateTime(input.value);
      trigger.classList.toggle("is-empty", !input.value);
      trigger.disabled = input.disabled;
      if (input.validity.valid) {
        invalid.hidden = true;
        invalid.textContent = "";
      }
      trigger.setAttribute("aria-invalid", String(serverInvalid || !invalid.hidden));
    }

    function close(returnFocus = true) {
      if (popover.hidden) return;
      popover.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
      if (frame !== null) cancelAnimationFrame(frame);
      frame = null;
      if (observer) observer.disconnect();
      observer = null;
      if (returnFocus) trigger.focus({ preventScroll: true });
    }

    function position() {
      if (popover.hidden) return;
      const viewport = window.visualViewport;
      const left = (viewport ? viewport.offsetLeft : 0) + 8;
      const top = (viewport ? viewport.offsetTop : 0) + 8;
      const bounds = {
        left, top,
        right: Math.min(document.documentElement.clientWidth,
          (viewport ? viewport.offsetLeft + viewport.width : window.innerWidth)) - 8,
        bottom: (viewport ? viewport.offsetTop + viewport.height : window.innerHeight) - 8,
      };
      [".worker-mobile-header", ".worker-bottom-nav"].forEach(function (selector) {
        const element = document.querySelector(selector);
        if (!element) return;
        const style = getComputedStyle(element);
        if (!["fixed", "sticky"].includes(style.position) || style.display === "none" || style.visibility === "hidden") return;
        const rect = element.getBoundingClientRect();
        if (!rect.height || rect.bottom <= bounds.top || rect.top >= bounds.bottom) return;
        if (selector === ".worker-bottom-nav") bounds.bottom = Math.min(bounds.bottom, rect.top - 8);
        else bounds.top = Math.max(bounds.top, rect.bottom + 8);
      });
      const rect = trigger.getBoundingClientRect();
      if (!trigger.isConnected || rect.bottom <= bounds.top || rect.top >= bounds.bottom || bounds.bottom - bounds.top < 48) {
        close();
        return;
      }
      popover.style.width = Math.max(0, Math.min(320, bounds.right - bounds.left)) + "px";
      popover.style.maxHeight = "none";
      const naturalHeight = popover.getBoundingClientRect().height;
      if (window.innerWidth <= 700) {
        popover.style.maxHeight = Math.max(48, bounds.bottom - bounds.top) + "px";
        const height = popover.getBoundingClientRect().height;
        const width = popover.getBoundingClientRect().width;
        popover.style.left = Math.max(bounds.left, (bounds.left + bounds.right - width) / 2) + "px";
        popover.style.top = Math.max(bounds.top, (bounds.top + bounds.bottom - height) / 2) + "px";
        return;
      }
      const below = Math.max(0, bounds.bottom - rect.bottom - 6);
      const above = Math.max(0, rect.top - bounds.top - 6);
      const openAbove = naturalHeight > below && above > below;
      const available = Math.floor(openAbove ? above : below);
      if (available < 48) { close(); return; }
      popover.style.maxHeight = available + "px";
      const height = popover.getBoundingClientRect().height;
      const preferred = openAbove ? rect.top - height - 6 : rect.bottom + 6;
      popover.style.left = Math.max(bounds.left, Math.min(rect.left, bounds.right - popover.getBoundingClientRect().width)) + "px";
      popover.style.top = Math.max(bounds.top, Math.min(preferred, bounds.bottom - height)) + "px";
    }

    function schedulePosition(event) {
      if (popover.hidden || frame !== null || (event && event.type === "scroll" && popover.contains(event.target))) return;
      frame = requestAnimationFrame(function () { frame = null; position(); });
    }

    function decorateCalendar(focusValue) {
      const title = calendarHost.querySelector("[data-calendar-title]").textContent.split(" ");
      const first = new Date(Number(title[1]), months.indexOf(title[0]), 1);
      const start = new Date(first);
      start.setDate(1 - (first.getDay() + 6) % 7);
      const days = Array.from(calendarHost.querySelectorAll(".calendar-day"));
      days.forEach(function (day, index) {
        const date = new Date(start);
        date.setDate(start.getDate() + index);
        day.dataset.cancellationDate = localDateValue(date);
        day.tabIndex = -1;
      });
      const current = days.find(day => day.dataset.cancellationDate === (focusValue || dateInput.value)) ||
        days.find(day => day.classList.contains("today")) || days.find(day => !day.classList.contains("outside"));
      current.tabIndex = 0;
      if (focusValue) current.focus({ preventScroll: true });
      apply.disabled = !dateInput.value;
      schedulePosition();
    }

    function open() {
      if (trigger.disabled) return;
      if (!popover.hidden) { close(); return; }
      // A fresh inline renderer keeps legacy picker state separate from the draft dialog.
      calendarHost.replaceChildren(template.content.cloneNode(true));
      dateInput = calendarHost.querySelector("input[type='hidden']");
      dateInput.value = input.value ? input.value.slice(0, 10) : "";
      const now = new Date();
      const hour = input.value ? Number(input.value.slice(11, 13)) : now.getHours();
      parts.hour.value = String(hour % 12 || 12);
      parts.minute.value = input.value ? input.value.slice(14, 16) : pad(now.getMinutes());
      parts.period.value = hour >= 12 ? "PM" : "AM";
      window.initDateTimePickers(calendarHost);
      dateInput.addEventListener("change", function () { decorateCalendar(dateInput.value); });
      decorateCalendar();
      popover.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      position();
      if (popover.hidden) return;
      calendarHost.querySelector(".calendar-day[tabindex='0']").focus({ preventScroll: true });
      if (typeof ResizeObserver !== "undefined") {
        observer = new ResizeObserver(schedulePosition);
        observer.observe(popover);
        observer.observe(trigger);
      }
    }

    calendarHost.addEventListener("click", function (event) {
      if (event.target.closest("[data-calendar-previous], [data-calendar-next]")) decorateCalendar();
    });
    calendarHost.addEventListener("keydown", function (event) {
      const day = event.target.closest(".calendar-day");
      if (!day || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End", "PageUp", "PageDown"].includes(event.key)) return;
      event.preventDefault();
      const [year, month, date] = day.dataset.cancellationDate.split("-").map(Number);
      const target = new Date(year, month - 1, date);
      const offsets = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7,
        Home: -(target.getDay() + 6) % 7, End: 6 - (target.getDay() + 6) % 7 };
      if (event.key === "PageUp" || event.key === "PageDown") {
        target.setDate(1);
        target.setMonth(target.getMonth() + (event.key === "PageUp" ? -1 : 1));
        target.setDate(Math.min(date, new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate()));
      } else target.setDate(target.getDate() + offsets[event.key]);
      const value = localDateValue(target);
      const title = calendarHost.querySelector("[data-calendar-title]").textContent.split(" ");
      const visibleMonth = Number(title[1]) * 12 + months.indexOf(title[0]);
      const targetMonth = target.getFullYear() * 12 + target.getMonth();
      if (targetMonth !== visibleMonth) {
        calendarHost.querySelector(targetMonth < visibleMonth ? "[data-calendar-previous]" : "[data-calendar-next]").click();
      }
      decorateCalendar(value);
    });

    function write(value) {
      input.value = value;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      syncDisplay();
      close();
    }

    trigger.addEventListener("click", open);
    apply.addEventListener("click", function () {
      if (dateInput && dateInput.value) write(composeDateTime(dateInput.value,
        parts.hour.value, parts.minute.value, parts.period.value));
    });
    root.querySelector("[data-cancellation-datetime-clear]").addEventListener("click", function () { write(""); });
    root.querySelector("[data-cancellation-datetime-cancel]").addEventListener("click", function () { close(); });
    root.querySelector("label[for]").addEventListener("click", function (event) {
      event.preventDefault();
      trigger.focus();
    });
    input.addEventListener("input", syncDisplay);
    input.addEventListener("change", syncDisplay);
    input.addEventListener("invalid", function (event) {
      event.preventDefault();
      invalid.textContent = input.validationMessage;
      invalid.hidden = false;
      trigger.setAttribute("aria-invalid", "true");
      close(false);
      // Do not steal focus from an earlier invalid field in the same native form.
      if (input.form.querySelector(":invalid") === input) trigger.focus();
    });
    input.addEventListener("focus", function () { trigger.focus(); });
    input.form.addEventListener("reset", function () {
      close(false);
      setTimeout(function () { invalid.hidden = true; syncDisplay(); }, 0);
    });
    document.addEventListener("pointerdown", function (event) {
      if (!popover.hidden && !popover.contains(event.target) && !trigger.contains(event.target)) close();
    });
    document.addEventListener("keydown", function (event) {
      if (popover.hidden) return;
      if (event.key === "Escape") { event.preventDefault(); close(); }
      if (event.key === "Tab") {
        const focusable = Array.from(popover.querySelectorAll("button:not(:disabled), select:not(:disabled)"))
          .filter(element => element.tabIndex >= 0 && element.getClientRects().length);
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });
    document.addEventListener("focusin", function (event) {
      if (!popover.hidden && !popover.contains(event.target) && event.target !== trigger) close();
    });
    window.addEventListener("resize", schedulePosition);
    window.addEventListener("scroll", schedulePosition, { capture: true, passive: true });
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", schedulePosition);
      window.visualViewport.addEventListener("scroll", schedulePosition);
    }
    input.tabIndex = -1;
    root.classList.add("is-enhanced");
    trigger.hidden = false;
    syncDisplay();
  });
})();
