from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import csv
import logging
from accounts.access_control import is_manager_or_admin, is_manager


from manager.forms import AssignSkillForm, MainSkillForm, SubSkillForm
from manager.models import MainSkill, SubSkill, EmployeeSkill
from employee.models import EmployeeProfile

logger = logging.getLogger(__name__)



@login_required
@user_passes_test(is_manager)
def assign_skills(request):
    try:
        form = AssignSkillForm()
        main_form = MainSkillForm()
        sub_form = SubSkillForm()

        if request.method == 'POST':
            if 'assign' in request.POST:
                form = AssignSkillForm(request.POST)
                if form.is_valid():
                    form.save()
                    messages.success(request, "Skill assigned successfully.")
                    return redirect('manager:assign-skills')

            elif 'add_main' in request.POST:
                main_form = MainSkillForm(request.POST)
                if main_form.is_valid():
                    main_form.save()
                    messages.success(request, "Main skill added successfully.")
                    return redirect('manager:assign-skills')

            elif 'add_sub' in request.POST:
                sub_form = SubSkillForm(request.POST)
                if sub_form.is_valid():
                    sub_form.save()
                    messages.success(request, "Subskill added successfully.")
                    return redirect('manager:assign-skills')

        employees = EmployeeProfile.objects.all()
        assigned_skills = EmployeeSkill.objects.select_related('employee', 'main_skill', 'subskill')
        
        # Calculate percentage for each skill for progress bar
        for skill in assigned_skills:
            skill.percentage = (skill.rating / 4) * 100  # 🟢 Attach computed field

        # Build dynamic matrix
        main_skills = MainSkill.objects.prefetch_related('subskills').all()
        employee_matrix = []
        for emp in employees:
            skills = assigned_skills.filter(employee=emp)
            skill_dict = {}
            for skill in skills:
                key = f"{skill.main_skill.name}|{skill.subskill.name}"
                skill_dict[key] = skill.rating
            employee_matrix.append({
                'employee': emp,
                'skill_dict': skill_dict
            })

        return render(request, 'manager/assign_skills.html', {
            'form': form,
            'main_form': main_form,
            'sub_form': sub_form,
            'skill_matrix': employee_matrix,
            'main_skills': main_skills,
        })
    except Exception as e:
        logger.error(f"Error in assign_skills: {str(e)}")
        messages.error(request, "An error occurred while processing your request")
        return redirect('manager:manager-dashboard')

@login_required
@user_passes_test(is_manager)
def load_subskills(request):
    main_skill_id = request.GET.get('main_skill_id') or request.GET.get('main_skill')
    subskills = SubSkill.objects.filter(main_skill_id=main_skill_id).values('id', 'name')
    return JsonResponse(list(subskills), safe=False)  # ✅ This returns a pure array


@login_required
@user_passes_test(is_manager)
def export_skill_matrix(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="skill_matrix.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee ID', 'Employee Name', 'Main Skill', 'Subskill', 'Rating'])

    all_skills = EmployeeSkill.objects.select_related('employee__user', 'main_skill', 'subskill')
    for skill in all_skills:
        writer.writerow([
            skill.employee.id,
            skill.employee.user.get_full_name(),
            skill.main_skill.name,
            skill.subskill.name,
            skill.rating,
        ])
    return response

@login_required
@user_passes_test(is_manager)
def get_employee_skill_data(request):
    employee_id = request.GET.get('employee_id')
    try:
        profile = EmployeeProfile.objects.get(id=employee_id)
    except EmployeeProfile.DoesNotExist:
        return JsonResponse([], safe=False)

    skills = EmployeeSkill.objects.filter(employee=profile).select_related('main_skill', 'subskill')
    data = [{
        'main_skill': skill.main_skill.name,
        'subskill': skill.subskill.name,
        'subskill_id': skill.subskill.id,
        'rating': skill.rating
    } for skill in skills]

    return JsonResponse(data, safe=False)

@csrf_exempt  # Optional: Use only if your AJAX isn't including CSRF (ideally, fix that instead)
@require_POST
@login_required
@user_passes_test(is_manager)
def edit_skill_assignment(request):
    employee_id = request.POST.get('employee_id')
    ratings_dict = request.POST.getlist('ratings')

    try:
        profile = EmployeeProfile.objects.get(id=employee_id)
    except EmployeeProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Employee not found'})

    try:
        with transaction.atomic():
            for subskill_id, rating in request.POST.items():
                if subskill_id.startswith('ratings['):
                    clean_id = subskill_id.replace('ratings[', '').replace(']', '')
                    try:
                        subskill = SubSkill.objects.get(id=clean_id)
                        emp_skill, _ = EmployeeSkill.objects.get_or_create(
                            employee=profile,
                            main_skill=subskill.main_skill,
                            subskill=subskill
                        )
                        emp_skill.rating = int(rating)
                        emp_skill.save()
                    except (SubSkill.DoesNotExist, ValueError):
                        continue
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': True})
    
    