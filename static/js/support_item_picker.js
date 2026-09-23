(function () {
  "use strict";

  var pickerSequence = 0;

  function initSupportItemPicker(select) {
    if (!select || select.dataset.supportItemPickerReady === "true") {
      return;
    }

    var selectableOptions = Array.from(select.options).filter(function (option) {
      return option.value;
    });
    var emptyOption = Array.from(select.options).find(function (option) {
      return !option.value;
    });

    pickerSequence += 1;
    var pickerId = "support-item-picker-" + pickerSequence;
    var resultsId = pickerId + "-results";

    var picker = document.createElement("div");
    picker.className = "support-item-picker";

    var trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "support-item-picker-trigger";
    trigger.setAttribute("role", "combobox");
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    trigger.setAttribute("aria-controls", resultsId);

    var triggerLabel = document.createElement("span");
    triggerLabel.className = "support-item-picker-trigger-label";

    var chevron = document.createElement("span");
    chevron.className = "support-item-picker-chevron";
    chevron.setAttribute("aria-hidden", "true");

    trigger.append(triggerLabel, chevron);

    var panel = document.createElement("div");
    panel.className = "support-item-picker-panel";
    panel.hidden = true;

    var searchWrap = document.createElement("div");
    searchWrap.className = "support-item-picker-search-wrap";

    var search = document.createElement("input");
    search.type = "search";
    search.className = "support-item-picker-search";
    search.placeholder = "Search service name, item code, or rate period";
    search.setAttribute("aria-label", "Search support items");
    search.setAttribute("autocomplete", "off");

    var results = document.createElement("div");
    results.className = "support-item-picker-results";
    results.id = resultsId;
    results.setAttribute("role", "listbox");
    results.setAttribute("aria-label", "Support items");

    searchWrap.appendChild(search);
    panel.append(searchWrap, results);
    picker.append(trigger, panel);
    select.insertAdjacentElement("afterend", picker);

    select.dataset.supportItemPickerReady = "true";
    select.classList.add("support-item-picker-native");

    function selectedOption() {
      return select.options[select.selectedIndex] || emptyOption;
    }

    function updateTrigger() {
      var option = selectedOption();
      triggerLabel.textContent = option ? option.text : "Select support item";
      trigger.classList.toggle("is-placeholder", !option || !option.value);
    }

    function visibleOptionButtons() {
      return Array.from(
        results.querySelectorAll(".support-item-picker-option:not([hidden])")
      );
    }

    function closePicker(restoreFocus) {
      panel.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
      picker.classList.remove("is-open");
      search.value = "";
      renderOptions("");
      if (restoreFocus) {
        trigger.focus();
      }
    }

    function chooseOption(option) {
      select.value = option.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      updateTrigger();
      closePicker(true);
    }

    function createGroupHeading(category) {
      var heading = document.createElement("div");
      heading.className = "support-item-picker-group";
      heading.textContent = category;
      heading.setAttribute("role", "presentation");
      return heading;
    }

    function createOptionButton(option) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "support-item-picker-option";
      button.textContent = option.text;
      button.dataset.value = option.value;
      button.setAttribute("role", "option");
      button.setAttribute(
        "aria-selected",
        option.value === select.value ? "true" : "false"
      );
      button.addEventListener("click", function () {
        chooseOption(option);
      });
      button.addEventListener("keydown", function (event) {
        var buttons = visibleOptionButtons();
        var index = buttons.indexOf(button);
        if (event.key === "ArrowDown") {
          event.preventDefault();
          buttons[Math.min(index + 1, buttons.length - 1)].focus();
        } else if (event.key === "ArrowUp") {
          event.preventDefault();
          if (index === 0) {
            search.focus();
          } else {
            buttons[index - 1].focus();
          }
        } else if (event.key === "Escape") {
          event.preventDefault();
          closePicker(true);
        }
      });
      return button;
    }

    function renderOptions(query) {
      var normalizedQuery = query.trim().toLocaleLowerCase();
      var matchingOptions = selectableOptions.filter(function (option) {
        return option.text.toLocaleLowerCase().includes(normalizedQuery);
      });
      var fragment = document.createDocumentFragment();
      var currentCategory = null;

      matchingOptions.forEach(function (option) {
        var category = option.dataset.category || "Other support items";
        if (category !== currentCategory) {
          fragment.appendChild(createGroupHeading(category));
          currentCategory = category;
        }
        fragment.appendChild(createOptionButton(option));
      });

      if (!matchingOptions.length) {
        var empty = document.createElement("p");
        empty.className = "support-item-picker-empty";
        empty.textContent = "No support items match your search.";
        fragment.appendChild(empty);
      }

      results.replaceChildren(fragment);
    }

    function openPicker() {
      if (!panel.hidden) {
        return;
      }
      document.querySelectorAll(".support-item-picker.is-open").forEach(
        function (openPickerElement) {
          if (openPickerElement !== picker) {
            var openTrigger = openPickerElement.querySelector(
              ".support-item-picker-trigger"
            );
            var openPanel = openPickerElement.querySelector(
              ".support-item-picker-panel"
            );
            openPickerElement.classList.remove("is-open");
            if (openTrigger) {
              openTrigger.setAttribute("aria-expanded", "false");
            }
            if (openPanel) {
              openPanel.hidden = true;
            }
          }
        }
      );
      panel.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      picker.classList.add("is-open");
      renderOptions(search.value);
      picker.classList.remove("align-right", "open-up");
      if (panel.getBoundingClientRect().right > window.innerWidth - 12) {
        picker.classList.add("align-right");
      }
      var lowerBoundary = window.innerHeight - 12;
      var modalBody = picker.closest(".shift-modal-body");
      if (modalBody) {
        lowerBoundary = Math.min(
          lowerBoundary,
          modalBody.getBoundingClientRect().bottom - 8
        );
      }
      if (panel.getBoundingClientRect().bottom > lowerBoundary) {
        picker.classList.add("open-up");
      }
      search.focus();
    }

    trigger.addEventListener("click", function () {
      if (panel.hidden) {
        openPicker();
      } else {
        closePicker(false);
      }
    });

    trigger.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown" || event.key === "Enter") {
        event.preventDefault();
        openPicker();
      } else if (event.key === "Escape" && !panel.hidden) {
        event.preventDefault();
        closePicker(false);
      }
    });

    search.addEventListener("input", function () {
      renderOptions(search.value);
    });

    search.addEventListener("keydown", function (event) {
      var buttons = visibleOptionButtons();
      if (event.key === "ArrowDown" && buttons.length) {
        event.preventDefault();
        buttons[0].focus();
      } else if (event.key === "Enter" && buttons.length) {
        event.preventDefault();
        buttons[0].click();
      } else if (event.key === "Escape") {
        event.preventDefault();
        closePicker(true);
      }
    });

    select.addEventListener("change", updateTrigger);
    select.addEventListener("invalid", function () {
      trigger.classList.add("has-error");
      window.setTimeout(function () {
        trigger.focus();
      }, 0);
    });

    document.addEventListener("click", function (event) {
      if (!panel.hidden && !picker.contains(event.target)) {
        closePicker(false);
      }
    });

    renderOptions("");
    updateTrigger();
  }

  function initWithin(root) {
    if (root.matches && root.matches("select[data-support-item-picker]")) {
      initSupportItemPicker(root);
    }
    if (root.querySelectorAll) {
      root.querySelectorAll("select[data-support-item-picker]").forEach(
        initSupportItemPicker
      );
    }
  }

  function initPage() {
    initWithin(document);
    var observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        mutation.addedNodes.forEach(function (node) {
          if (node.nodeType === Node.ELEMENT_NODE) {
            initWithin(node);
          }
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPage);
  } else {
    initPage();
  }
})();
