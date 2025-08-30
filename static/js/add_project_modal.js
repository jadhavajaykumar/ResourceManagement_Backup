// Handle dynamic fields and validation for Add Project modal

document.addEventListener('DOMContentLoaded', function () {
  const modal = document.getElementById('addProjectModal');
  if (!modal) return;

  function toggleFields() {
    const projectType = document.getElementById('id_project_type');
    const locationType = document.getElementById('id_location_type');

    const rateTypeGroup = document.querySelector('.field-rate_type');
    const rateValueGroup = document.querySelector('.field-rate_value');
    const daRateGroup = document.querySelector('.field-da_rate_per_unit');
    const daTypeGroup = document.querySelector('.field-da_type');
    const extHoursThresholdGroup = document.querySelector('.field-extended_hours_threshold');
    const extHoursRateGroup = document.querySelector('.field-extended_hours_da_rate');
    const offdayDAGroup = document.querySelector('.field-off_day_da_rate');
    const budgetGroup = document.querySelector('.field-budget');
    const dailyRateGroup = document.querySelector('.field-daily_rate');

    const selectedLocation = locationType?.selectedOptions[0]?.text?.toLowerCase();

    if (projectType?.selectedOptions[0]?.text?.toLowerCase() === 'service') {
      rateTypeGroup?.classList.remove('d-none');
      rateValueGroup?.classList.remove('d-none');
      dailyRateGroup?.classList.remove('d-none');
      budgetGroup?.classList.add('d-none');
    } else {
      rateTypeGroup?.classList.add('d-none');
      rateValueGroup?.classList.add('d-none');
      dailyRateGroup?.classList.add('d-none');
      budgetGroup?.classList.remove('d-none');
    }

    daRateGroup?.classList.remove('d-none');

    if (selectedLocation === 'international') {
      daTypeGroup?.classList.remove('d-none');
      extHoursThresholdGroup?.classList.remove('d-none');
      extHoursRateGroup?.classList.remove('d-none');
      offdayDAGroup?.classList.remove('d-none');
    } else {
      daTypeGroup?.classList.add('d-none');
      extHoursThresholdGroup?.classList.add('d-none');
      extHoursRateGroup?.classList.add('d-none');
      offdayDAGroup?.classList.add('d-none');
    }
  }

  function validateBeforeSubmit() {
    const projectType = document.getElementById('id_project_type')?.selectedOptions[0]?.text?.toLowerCase();
    const locationText = document.getElementById('id_location_type')?.selectedOptions[0]?.text?.toLowerCase();
    const requiredFields = [];

    if (projectType === 'service') {
      requiredFields.push('rate_type', 'rate_value', 'daily_rate');
    }
    if (projectType === 'turnkey') {
      requiredFields.push('budget');
    }
    if (['local', 'domestic', 'international'].includes(locationText)) {
      requiredFields.push('da_rate_per_unit');
    }
    if (locationText === 'international') {
      requiredFields.push('da_type', 'extended_hours_threshold', 'extended_hours_da_rate', 'off_day_da_rate');
    }

    let valid = true;
    requiredFields.forEach(fieldName => {
      const field = document.getElementById(`id_${fieldName}`);
      const label = document.querySelector(`label[for="id_${fieldName}"]`);
      if (field && !field.value.trim()) {
        valid = false;
        field.classList.add('is-invalid');
        label?.classList.add('text-danger');
      } else {
        field?.classList.remove('is-invalid');
        label?.classList.remove('text-danger');
      }
    });

    if (!valid) {
      alert('Please fill all required fields based on project type and location.');
      return false;
    }
    return true;
  }

  function handleSubmit(e) {
    if (!validateBeforeSubmit()) e.preventDefault();
  }

  function onModalShown() {
    document.getElementById('id_project_type')?.addEventListener('change', toggleFields);
    document.getElementById('id_location_type')?.addEventListener('change', toggleFields);
    modal.querySelector('form')?.addEventListener('submit', handleSubmit);
    toggleFields();

    const focusTarget = modal.querySelector('input, select, textarea, .modal-content');
    focusTarget?.focus();
  }

  function onModalHidden() {
    document.getElementById('id_project_type')?.removeEventListener('change', toggleFields);
    document.getElementById('id_location_type')?.removeEventListener('change', toggleFields);
    modal.querySelector('form')?.removeEventListener('submit', handleSubmit);
  }

  modal.addEventListener('shown.bs.modal', onModalShown);
  modal.addEventListener('hidden.bs.modal', onModalHidden);
})