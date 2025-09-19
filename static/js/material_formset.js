document.addEventListener('DOMContentLoaded', function () {
  const container = document.getElementById('materials-formset'); // matches template id
  const addBtn = document.getElementById('add-material-btn'); // you'll add this button in template
  if (!container || !addBtn) return;

  const totalFormsInput = document.querySelector('#materials input[name$="-TOTAL_FORMS"], #id_materials-TOTAL_FORMS');
  if (!totalFormsInput) return;

  addBtn.addEventListener('click', function (e) {
    e.preventDefault();
    const totalForms = parseInt(totalFormsInput.value, 10);
    const emptyTemplate = document.getElementById('empty-material-form'); // hidden template element
    if (!emptyTemplate) return;

    let newHtml = emptyTemplate.innerHTML.replace(/__prefix__/g, totalForms);
    const wrapper = document.createElement('div');
    wrapper.className = 'row g-2 align-items-end material-form mb-2';
    wrapper.innerHTML = newHtml;
    container.appendChild(wrapper);
    totalFormsInput.value = totalForms + 1;
  });

  // delegate remove button clicks
  container.addEventListener('click', function (e) {
    if (e.target && e.target.matches('.remove-material-btn')) {
      e.preventDefault();
      const row = e.target.closest('.material-form');
      if (!row) {
        // if you used different classes
        const containerRow = e.target.closest('.row');
        if (containerRow) containerRow.remove();
      } else {
        row.remove();
      }
      // update TOTAL_FORMS
      const current = container.querySelectorAll('.material-form, .row.material-form').length;
      totalFormsInput.value = current;
    }
  });
});
