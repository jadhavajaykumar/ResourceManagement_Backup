// static/js/expense_form.js
// Robust initializer for expense form UI. Call as:
//   initExpenseForm(rootElement)  -- rootElement can be a DOM element that contains the form (preferred)
//   initExpenseForm()             -- will default to document
(function () {
  function containerFor(el) {
    if (!el) return null;
    // Prefer known wrapper classes used in the templates, but fall back to parentElement
    return el.closest('.mb-2') || el.closest('.form-group') || document.querySelector('[id$="' + (el.id || '').replace(/(^.*?_)/, '') + 'Field"]') || el.parentElement || null;
  }

  // normalize truthy dataset values
  function truthy(val) {
    if (val === undefined || val === null) return false;
    if (typeof val === 'boolean') return val;
    var s = String(val).toLowerCase().trim();
    return s === '1' || s === 'true' || s === 'yes' || s === 'y';
  }

  window.initExpenseForm = function (root) {
    var container = root && root.nodeType === 1 ? root : document;

    // use "ends with" selectors so prefixed ids/names work (e.g. exp_369_new_expense_type)
    var expenseType = container.querySelector('[name$="new_expense_type"], [id$="_new_expense_type"]');
    if (!expenseType) return;

    var amountInput = container.querySelector('[name$="amount"], [id$="_amount"], [id$="id_amount"]');
    var kilometersInput = container.querySelector('[name$="kilometers"], [id$="_kilometers"], [id$="id_kilometers"]');
    var receiptInput = container.querySelector('[name$="receipt"], [id$="_receipt"], [id$="id_receipt"]');
    var travelFromInput = container.querySelector('[name$="from_location"], [id$="_from_location"], [id$="id_from_location"], [name$="travel_from"], [id$="id_travel_from"]');
    var travelToInput = container.querySelector('[name$="to_location"], [id$="_to_location"], [id$="id_to_location"], [name$="travel_to"], [id$="id_travel_to"]');

    var kilometersField = containerFor(kilometersInput);
    var amountField = containerFor(amountInput);
    var travelFromField = containerFor(travelFromInput);
    var travelToField = containerFor(travelToInput);

    function readOptionData(opt) {
      // read multiple possible data attribute names
      var data = {};
      if (!opt) return data;
      var ds = opt.dataset || {};
      data.requiresKm = truthy(ds.requiresKm || ds.requiresKm === 'true' ? ds.requiresKm : ds.requiresKm);
      // other possible attribute keys
      data.requiresKm = data.requiresKm || truthy(opt.getAttribute('data-requires-km'));
      data.rate = parseFloat(ds.rate || opt.getAttribute('data-rate') || opt.getAttribute('data-rate-per-km') || opt.getAttribute('data-rate_per_km') || 0) || 0;
      data.requiresReceipt = truthy(ds.requiresReceipt || opt.getAttribute('data-requires-receipt'));
      data.requiresTravel = truthy(ds.requiresTravel || opt.getAttribute('data-requires-travel'));
      data.maxCap = parseFloat(ds.maxCap || opt.getAttribute('data-max-cap') || opt.getAttribute('data-max_cap') || 0) || null;
      return data;
    }

    function optionIndicatesKm(opt) {
      if (!opt) return false;
      var d = readOptionData(opt);
      if (d.requiresKm) return true;
      // fallback: check option value or text for known slugs
      var v = (opt.value || '').toString().toLowerCase();
      var t = (opt.textContent || '').toString().toLowerCase();
      if (v.indexOf('travel-bike') !== -1 || v.indexOf('travel-car') !== -1) return true;
      if (t.indexOf('travel-bike') !== -1 || t.indexOf('travel-car') !== -1) return true;
      // broader fallback: if label contains 'travel' and 'car' or 'bike'
      if (t.indexOf('travel') !== -1 && (t.indexOf('car') !== -1 || t.indexOf('bike') !== -1)) return true;
      return false;
    }

    function getSelectedOption() {
      if (!expenseType) return null;
      if (expenseType.tagName === 'SELECT') {
        return expenseType.options[expenseType.selectedIndex];
      }
      // if it's not a select (edge case), try to find matching option element by value
      var val = expenseType.value;
      var sel = container.querySelector('[id$="_new_expense_type"] option[value="' + val + '"]') || container.querySelector('option[value="' + val + '"]');
      return sel || null;
    }

    function updateFormFields() {
      var opt = getSelectedOption();
      var d = readOptionData(opt);
      var requiresKm = optionIndicatesKm(opt);
      var requiresReceipt = d.requiresReceipt;
      var requiresTravel = d.requiresTravel;
      var rate = d.rate || 0;

      if (kilometersField) kilometersField.style.display = requiresKm ? '' : 'none';
      if (amountField) amountField.style.display = requiresKm ? 'none' : '';
      if (travelFromField) travelFromField.style.display = requiresTravel ? '' : 'none';
      if (travelToField) travelToField.style.display = requiresTravel ? '' : 'none';
      if (receiptInput) receiptInput.required = !!requiresReceipt;

      // if kms required and kms input has value, compute amount
      if (requiresKm && kilometersInput && amountInput) {
        var kmVal = parseFloat(kilometersInput.value) || 0;
        if (!isNaN(rate)) {
          amountInput.value = (kmVal * rate).toFixed(2);
        }
      }
    }

    function enforceMaxCap() {
      if (!amountInput) return;
      var opt = getSelectedOption();
      var d = readOptionData(opt);
      var maxCap = d.maxCap;
      var current = parseFloat(amountInput.value) || 0;
      if (maxCap && !isNaN(maxCap) && current > maxCap) {
        try { alert('Maximum allowed amount for this expense is ₹' + maxCap); } catch (e) {}
        amountInput.value = maxCap.toFixed(2);
      }
    }

    // Attach events (scoped to this container)
    if (expenseType && expenseType.tagName === 'SELECT') {
      expenseType.addEventListener('change', updateFormFields);
    } else if (expenseType) {
      expenseType.addEventListener('input', updateFormFields);
    }
    if (kilometersInput) {
      kilometersInput.addEventListener('input', updateFormFields);
    }
    if (amountInput) {
      amountInput.addEventListener('blur', enforceMaxCap);
    }

    // init initial state
    try {
      updateFormFields();
    } catch (e) {
      // be defensive; do not break page if something unexpected
      console.debug("initExpenseForm updateFormFields error:", e);
    }
  };

  // Auto-init for the static page when there's an expense form on DOM
  document.addEventListener('DOMContentLoaded', function () {
    if (document.querySelector('[name$="new_expense_type"], [id$="_new_expense_type"]')) {
      if (typeof window.initExpenseForm === 'function') {
        window.initExpenseForm(document);
      }
    }
  });
})();
