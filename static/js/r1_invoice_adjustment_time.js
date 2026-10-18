/* Drawer-only presentation adapter. Original named time inputs own all values and validation. */
(() => {
  "use strict";
  const shell = document.querySelector(".r1-admin-invoice-create");
  const drawer = shell && shell.querySelector("[data-billing-drawer]");
  if (!drawer || typeof drawer.showModal !== "function") return;
  const desktop = window.matchMedia("(min-width: 761px) and (hover: hover) and (pointer: fine)");
  const pad = value => String(value).padStart(2, "0");
  const controls = [];
  let active = null;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    node.className = className;
    if (text) node.textContent = text;
    return node;
  }
  function format(value) {
    if (!/^\d{2}:\d{2}$/.test(value)) return "Select time";
    const hour = Number(value.slice(0, 2));
    return `${pad(hour % 12 || 12)}:${value.slice(3)} ${hour < 12 ? "AM" : "PM"}`;
  }
  function close(returnFocus = true) {
    if (!active) return;
    const current = active;
    active = null;
    current.panel.hidden = true;
    current.trigger.setAttribute("aria-expanded", "false");
    if (returnFocus && current.trigger.getClientRects().length && !current.trigger.disabled) {
      current.trigger.focus({ preventScroll: true });
    }
  }
  function position() {
    if (!active) return;
    const { input, trigger, panel } = active;
    if (!drawer.open || trigger.disabled || !trigger.getClientRects().length) { close(false); return; }
    const rect = input.getBoundingClientRect();
    const bounds = drawer.getBoundingClientRect();
    const top = Math.max(8, drawer.querySelector("header").getBoundingClientRect().bottom + 6);
    const bottom = Math.min(window.innerHeight - 8, drawer.querySelector("footer").getBoundingClientRect().top - 6);
    if (rect.bottom <= top || rect.top >= bottom || bottom - top < 80) { close(false); return; }
    const left = Math.max(8, bounds.left + 12);
    const right = Math.min(document.documentElement.clientWidth - 8, bounds.right - 12);
    panel.style.width = Math.min(248, right - left) + "px";
    panel.style.maxHeight = (bottom - top) + "px";
    const height = panel.getBoundingClientRect().height;
    const below = bottom - rect.bottom - 6;
    const above = rect.top - top - 6;
    const preferred = height > below && above > below ? rect.top - height - 6 : rect.bottom + 6;
    panel.style.left = Math.max(left, Math.min(rect.left, right - panel.getBoundingClientRect().width)) + "px";
    panel.style.top = Math.max(top, Math.min(preferred, bottom - height)) + "px";
  }
  function syncAll() { controls.forEach(control => control.sync()); position(); }

  shell.querySelectorAll("[data-billing-time-fields] input[type=time]").forEach((input, index) => {
    const root = input.parentElement;
    root.classList.add("r1-invoice-time");
    const caption = root.querySelector("label").textContent.replace(/:\s*$/, "");
    const trigger = element("button", "r1-invoice-time-trigger");
    trigger.type = "button";
    trigger.hidden = true;
    trigger.setAttribute("aria-haspopup", "dialog");
    trigger.setAttribute("aria-expanded", "false");
    trigger.setAttribute("title", `Choose ${caption.toLowerCase()}`);
    const panel = element("div", "r1-invoice-time-panel");
    panel.dataset.r1TimePanel = "";
    panel.id = `r1-invoice-time-${index}`;
    panel.hidden = true;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", `Choose ${caption.toLowerCase()}`);
    trigger.setAttribute("aria-controls", panel.id);
    const describedBy = input.getAttribute("aria-describedby");
    if (describedBy) trigger.setAttribute("aria-describedby", describedBy);
    const serverInvalid = input.getAttribute("aria-invalid") === "true";
    const fields = element("div", "r1-invoice-time-parts");
    const parts = {};
    for (const [part, title, values] of [
      ["hour", "Hour", Array.from({ length: 12 }, (_, i) => pad(i + 1))],
      ["minute", "Minute", Array.from({ length: 60 }, (_, i) => pad(i))],
      ["period", "Period", ["AM", "PM"]],
    ]) {
      const label = element("label", "", title);
      const select = element("select", "");
      select.dataset.r1TimePart = part;
      values.forEach(value => select.add(new Option(value, value)));
      label.append(select);
      fields.append(label);
      parts[part] = select;
    }
    const actions = element("div", "r1-invoice-time-actions");
    const cancel = element("button", "r1-invoice-time-cancel", "Cancel");
    const apply = element("button", "r1-invoice-time-apply", "Apply");
    cancel.type = apply.type = "button";
    actions.append(cancel, apply);
    panel.append(fields, actions);
    root.append(trigger, panel);
    const control = { input, trigger, panel, sync() {
      const enhanced = desktop.matches;
      root.classList.toggle("is-enhanced", enhanced);
      trigger.hidden = !enhanced;
      trigger.disabled = input.disabled;
      trigger.setAttribute("aria-label", `Choose ${caption.toLowerCase()}, ${format(input.value)}`);
      trigger.setAttribute("aria-invalid", String(serverInvalid || (!input.disabled && !input.validity.valid)));
      if (active === control && (!enhanced || input.disabled || !drawer.open || !trigger.getClientRects().length)) close(false);
    } };
    controls.push(control);
    trigger.addEventListener("click", () => {
      control.sync();
      if (!desktop.matches || trigger.disabled || !drawer.open) return;
      if (active === control) { close(); return; }
      close(false);
      const hour = Number(input.value.slice(0, 2) || 9);
      parts.hour.value = pad(hour % 12 || 12);
      parts.minute.value = input.value.slice(3, 5) || "00";
      parts.period.value = hour < 12 ? "AM" : "PM";
      active = control;
      panel.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      position();
      if (active) parts.hour.focus({ preventScroll: true });
    });
    trigger.addEventListener("keydown", event => {
      if (event.key === "ArrowDown") { event.preventDefault(); trigger.click(); }
    });
    cancel.addEventListener("click", () => close());
    apply.addEventListener("click", () => {
      const hour = Number(parts.hour.value) % 12 + (parts.period.value === "PM" ? 12 : 0);
      input.value = `${pad(hour)}:${parts.minute.value}`;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      control.sync();
      close();
    });
    new MutationObserver(control.sync).observe(input, { attributes: true, attributeFilter: ["disabled", "required"] });
    control.sync();
  });
  new MutationObserver(syncAll).observe(drawer, { attributes: true, attributeFilter: ["open"], childList: true });
  shell.addEventListener("input", syncAll);
  shell.addEventListener("change", syncAll);
  shell.addEventListener("reset", () => { close(false); setTimeout(syncAll, 0); });
  desktop.addEventListener("change", () => { close(false); syncAll(); });
  document.addEventListener("pointerdown", event => {
    if (active && !active.panel.contains(event.target) && !active.trigger.contains(event.target)) close(false);
  });
  document.addEventListener("focusin", event => {
    if (active && !active.panel.contains(event.target) && event.target !== active.trigger) close(false);
  });
  drawer.addEventListener("keydown", event => {
    if (!active) return;
    if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); close(); }
    else if (event.key === "Tab") {
      const items = [...active.panel.querySelectorAll("select, button")];
      if (event.shiftKey && event.target === items[0]) { event.preventDefault(); items.at(-1).focus(); }
      else if (!event.shiftKey && event.target === items.at(-1)) { event.preventDefault(); items[0].focus(); }
    }
  }, true);
  drawer.addEventListener("close", () => { close(false); syncAll(); });
  window.addEventListener("resize", position);
  document.addEventListener("scroll", event => {
    if (active && !active.panel.contains(event.target)) close(false);
  }, true);
})();
