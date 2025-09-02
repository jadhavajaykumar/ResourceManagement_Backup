function initExpenseForm() {
    const expenseType = document.getElementById('id_new_expense_type');
    if (!expenseType) return;
    const kilometersField = document.getElementById('kilometersField');
    const amountField = document.getElementById('amountField');
    const amountInput = document.getElementById('id_amount');
    const kilometersInput = document.getElementById('id_kilometers');
    const receiptInput = document.getElementById('id_receipt');
    const travelFromField = document.getElementById('travel-fields-from');
    const travelToField = document.getElementById('travel-fields-to');

    function updateFormFields() {
        const selected = expenseType.options[expenseType.selectedIndex];
        if (!selected) return;
        const requiresKm = selected.dataset.requiresKm === 'true';
        const requiresReceipt = selected.dataset.requiresReceipt === 'true';
        const requiresTravel = selected.dataset.requiresTravel === 'true';
        const rate = parseFloat(selected.dataset.rate || 0);

        kilometersField.style.display = requiresKm ? 'block' : 'none';
        amountField.style.display = requiresKm ? 'none' : 'block';
        travelFromField.style.display = requiresTravel ? 'block' : 'none';
        travelToField.style.display = requiresTravel ? 'block' : 'none';
        receiptInput.required = requiresReceipt;

        if (requiresKm && kilometersInput.value) {
            amountInput.value = (kilometersInput.value * rate).toFixed(2);
        }
    }

    function enforceMaxCap() {
        const selected = expenseType.options[expenseType.selectedIndex];
        const maxCap = parseFloat(selected.dataset.maxCap || 0);
        if (maxCap > 0 && parseFloat(amountInput.value) > maxCap) {
            alert(`Maximum allowed amount for this expense is ₹${maxCap}`);
            amountInput.value = maxCap.toFixed(2);
        }
    }

    expenseType.addEventListener('change', updateFormFields);
    kilometersInput.addEventListener('input', updateFormFields);
    amountInput.addEventListener('blur', enforceMaxCap);

    updateFormFields();
}

document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById('id_new_expense_type')) {
        initExpenseForm();
    }
});