from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from .forms import AssignSkillForm, MainSkillForm, SubSkillForm, TaskAssignmentForm
from .models import MainSkill, SubSkill, EmployeeSkill, TaskAssignment
from employee.models import EmployeeProfile
import logging
import csv
from project.models import Task
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
# manager/views.py
from expenses.models import ExpenseType

from django.db import transaction
# manager/views.py




logger = logging.getLogger(__name__)



def is_manager(user):
    """
    Enhanced manager check that:
    1. Handles missing profiles gracefully
    2. Maintains all existing logging
    3. Keeps backward compatibility
    """
    if not user.is_authenticated:
        logger.debug(f"Unauthenticated user access attempt")
        return False
        
    # Superusers should automatically be managers
    if user.is_superuser:
        logger.info(f"Superuser {user.email} granted manager access")
        return True
        
    try:
        # Get or create profile for staff users
        if user.is_staff and not hasattr(user, 'employee_profile'):
            from employee.models import EmployeeProfile
            EmployeeProfile.objects.create(user=user, role='Manager')
            logger.info(f"Created Manager profile for staff user {user.email}")
        
        # Original check with enhanced safety
        is_manager_role = hasattr(user, 'employee_profile') and user.employee_profile.role == 'Manager'
        logger.info(f"Manager check for {user.email}: role={getattr(user.employee_profile, 'role', 'No profile')}, result={is_manager_role}")
        return is_manager_role
        
    except Exception as e:
        logger.error(f"Error checking manager status for {user.email}: {str(e)}", exc_info=True)
        return False  # Fail securely












  # manager/views.py
@login_required
def manager_dashboard(request):
    logger.info(f"Manager dashboard accessed by {request.user.username}, authenticated: {request.user.is_authenticated}")
    return render(request, 'manager/manager_dashboard.html', {})
  


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
    main_skill_id = request.GET.get('main_skill')
    subskills = SubSkill.objects.filter(main_skill_id=main_skill_id).values('id', 'name')
    return JsonResponse(list(subskills), safe=False)
    




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





@login_required
@user_passes_test(is_manager)
def assign_task(request):
    assignments = TaskAssignment.objects.select_related('employee__user', 'project', 'task').order_by('-assigned_date')

    if request.method == "POST":
        # Unassign task
        if 'unassign_task' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            if assignment_id and assignment_id.isdigit():
                TaskAssignment.objects.filter(id=assignment_id).delete()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return redirect('manager:assign-task')
            else:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Invalid assignment ID'})
                return redirect('manager:assign-task')

        # Edit task assignment
        elif 'edit_task' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            assignment = get_object_or_404(TaskAssignment, id=assignment_id)
            form = TaskAssignmentForm(request.POST, instance=assignment)
            if form.is_valid():
                form.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return redirect('manager:assign-task')
            else:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': form.errors})
                # Re-render page if normal POST fails validation
                return render(request, 'manager/assign_task.html', {
                    'form': form,
                    'assignments': assignments,
                })

        # New task assignment
        else:
            form = TaskAssignmentForm(request.POST)
            if form.is_valid():
                form.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return redirect('manager:assign-task')
            else:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = TaskAssignmentForm()

    return render(request, 'manager/assign_task.html', {
        'form': form,
        'assignments': assignments,
    })



@login_required
def load_tasks(request):
    project_id = request.GET.get('project')
    tasks = Task.objects.filter(project_id=project_id).order_by('name')
    return JsonResponse(list(tasks.values('id', 'name')), safe=False)


@login_required
def load_assignments_ajax(request):
    assignments = TaskAssignment.objects.select_related('employee__user', 'project', 'task').order_by('-assigned_date')
    data = [
        {
            'id': a.id,
            'employee': a.employee.user.get_full_name(),
            'project': a.project.name if a.project else "-",
            'task': a.task.name if a.task else "-",
            'date': a.assigned_date.strftime('%Y-%m-%d'),
        }
        for a in assignments
    ]
    return JsonResponse({'assignments': data})





# Update the manage_expense_types view
@login_required
@user_passes_test(is_manager)
def manage_expense_types(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        requires_km = 'requires_kilometers' in request.POST
        requires_receipt = 'requires_receipt' in request.POST
        rate = request.POST.get('rate')
        
        try:
            ExpenseType.objects.create(
                name=name,
                requires_kilometers=requires_km,
                requires_receipt=requires_receipt,
                rate_per_km=rate if rate else None,
                created_by=request.user
            )
            messages.success(request, "Expense type created successfully!")
            return redirect('manager:manage-expense-types')
        except Exception as e:
            messages.error(request, f"Error creating expense type: {str(e)}")
    
    types = ExpenseType.objects.all()
    return render(request, 'manager/expense_types.html', {'types': types})