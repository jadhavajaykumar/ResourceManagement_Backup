document.addEventListener("DOMContentLoaded", function () {
  // Toggle dynamic fields in project form
  function toggleFields() {
    const location = document.getElementById("id_location")?.value;
    const projectType = document.getElementById("id_project_type")?.value;

    const intlFields = ["country_rate", "currency", "da_rate_per_hour", "extra_hour_rate"];
    const billingDiv = document.getElementById("div_billing_method");
    const budgetDiv = document.getElementById("div_budget");
    const statusDiv = document.getElementById("div_status");

    intlFields.forEach(field => {
      const div = document.getElementById("div_" + field);
      if (div) div.style.display = (location === "International") ? "block" : "none";
    });

    if (billingDiv) billingDiv.style.display = projectType === "Service" ? "block" : "none";
    if (budgetDiv) budgetDiv.style.display = projectType === "Turnkey" ? "block" : "none";
    if (statusDiv) statusDiv.style.display = (projectType === "Turnkey" || location === "International") ? "block" : "none";
  }

  // Bind toggle triggers
  document.getElementById("id_location")?.addEventListener("change", toggleFields);
  document.getElementById("id_project_type")?.addEventListener("change", toggleFields);
  toggleFields(); // Initial call

  // Fetch and populate country DA rate values
  document.getElementById("id_country_rate")?.addEventListener("change", function () {
    const countryId = this.value;
    if (!countryId) return;

    fetch(`/project/ajax/get-country-rates/?country_id=${countryId}`)
      .then(res => res.json())
      .then(data => {
        document.getElementById("id_da_rate_per_hour").value = data.da_rate_per_hour || '';
        document.getElementById("id_extra_hour_rate").value = data.extra_hour_rate || '';
        document.getElementById("id_currency").value = data.currency || '';
      });
  });

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
