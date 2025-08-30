document.addEventListener("DOMContentLoaded", function () {
  // Toggle dynamic fields in project form
  function toggleFields() {
    const projectTypeEl = document.getElementById("id_project_type");
    const locationEl = document.getElementById("id_location_type");

    const rateTypeGroup = document.getElementById("div_rate_type");
    const rateValueGroup = document.getElementById("div_rate_value");
    const dailyRateGroup = document.getElementById("div_daily_rate");
    const budgetGroup = document.getElementById("div_budget");

    const daRateGroup = document.getElementById("div_da_rate_per_unit");
    const daTypeGroup = document.getElementById("div_da_type");
    const extHoursThresholdGroup = document.getElementById("div_extended_hours_threshold");
    const extHoursRateGroup = document.getElementById("div_extended_hours_da_rate");
    const offDayDAGroup = document.getElementById("div_off_day_da_rate");

    const countryGroup = document.getElementById("div_country");
    const currencyGroup = document.getElementById("div_currency");

    const projectType = projectTypeEl?.selectedOptions[0]?.text?.toLowerCase();
    const location = locationEl?.selectedOptions[0]?.text?.toLowerCase();

    if (projectType === "service") {
      rateTypeGroup?.classList.remove("d-none");
      rateValueGroup?.classList.remove("d-none");
      dailyRateGroup?.classList.remove("d-none");
      budgetGroup?.classList.add("d-none");
    } else {
      rateTypeGroup?.classList.add("d-none");
      rateValueGroup?.classList.add("d-none");
      dailyRateGroup?.classList.add("d-none");
      budgetGroup?.classList.remove("d-none");
    }

    daRateGroup?.classList.remove("d-none");

    if (location === "international") {
      daTypeGroup?.classList.remove("d-none");
      extHoursThresholdGroup?.classList.remove("d-none");
      extHoursRateGroup?.classList.remove("d-none");
      offDayDAGroup?.classList.remove("d-none");
      countryGroup?.classList.remove("d-none");
      currencyGroup?.classList.remove("d-none");
    } else {
      daTypeGroup?.classList.add("d-none");
      extHoursThresholdGroup?.classList.add("d-none");
      extHoursRateGroup?.classList.add("d-none");
      offDayDAGroup?.classList.add("d-none");
      countryGroup?.classList.add("d-none");
      currencyGroup?.classList.add("d-none");
    }
  }

  // Bind toggle triggers
  document.getElementById("id_location_type")?.addEventListener("change", toggleFields);
  document.getElementById("id_project_type")?.addEventListener("change", toggleFields);
  toggleFields(); // Initial call

    // Skill mapping section
  const mainSkillDropdown = document.getElementById('main_skill');
  const subskillDropdown = document.getElementById('subskill');
  const addSkillBtn = document.getElementById('add-skill-btn');
  const addedSkillsList = document.getElementById('added-skills-list');
  const selectedSkillsInput = document.getElementById('selected_skills');
  let selectedSkills = [];

  mainSkillDropdown?.addEventListener('change', function () {
    const mainSkillId = this.value;
    if (!mainSkillId) {
      subskillDropdown.innerHTML = '<option value="">-- Select Subskill --</option>';
      subskillDropdown.disabled = true;
      return;
    }

    fetch(`/manager/load-subskills/?main_skill=${mainSkillId}`)
      .then(response => response.json())
      .then(data => {
        subskillDropdown.disabled = false;
        subskillDropdown.innerHTML = '<option value="">-- Select Subskill --</option>';
        data.forEach(sub => {
          subskillDropdown.innerHTML += `<option value="${sub.id}">${sub.name}</option>`;
        });
      });
  });

  addSkillBtn?.addEventListener('click', function () {
    const mainSkillText = mainSkillDropdown.options[mainSkillDropdown.selectedIndex]?.text;
    const mainSkillId = mainSkillDropdown.value;
    const subskillText = subskillDropdown.options[subskillDropdown.selectedIndex]?.text;
    const subskillId = subskillDropdown.value;

    if (!mainSkillId || !subskillId) {
      alert("Please select both main skill and subskill");
      return;
    }

    const skillObj = { main_skill_id: mainSkillId, main_skill_name: mainSkillText, subskill_id: subskillId, subskill_name: subskillText };
    selectedSkills.push(skillObj);

    const li = document.createElement('li');
    li.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center');
    li.innerHTML = `${mainSkillText} → ${subskillText} <button type="button" class="btn btn-sm btn-danger remove-skill">Remove</button>`;

    li.querySelector('.remove-skill').addEventListener('click', function () {
      const index = Array.from(addedSkillsList.children).indexOf(li);
      selectedSkills.splice(index, 1);
      li.remove();
      selectedSkillsInput.value = JSON.stringify(selectedSkills);
    });

    addedSkillsList.appendChild(li);
    selectedSkillsInput.value = JSON.stringify(selectedSkills);

    mainSkillDropdown.value = "";
    subskillDropdown.innerHTML = '<option value="">-- Select Subskill --</option>';
    subskillDropdown.disabled = true;
  });
});
