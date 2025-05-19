from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse, FileResponse
from .forms import AssignSkillForm, MainSkillForm, SubSkillForm, TaskAssignmentForm
from .models import MainSkill, SubSkill, EmployeeSkill, TaskAssignment
from employee.models import EmployeeProfile
import logging
import csv, io
from project.models import Task
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
# manager/views.py
from expenses.models import ExpenseType

from django.db import transaction
# manager/views.py

from django.contrib.auth.decorators import login_required
from expenses.models import Expense
from django.core.mail import send_mail

import os
from django.conf import settings
from django.http import FileResponse
from django.core.files.storage import FileSystemStorage

import urllib.parse

from django.core.files.storage import default_storage
from django.utils.text import slugify
from project.models import Project
from .utils import calculate_project_progress


from django.utils import timezone
from timesheet.models import Timesheet

from django.db.models import Sum, Count, F
from datetime import date, datetime, timedelta

from django.utils.timezone import now


from reportlab.pdfgen import canvas


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


    


@login_required
def expense_approval_dashboard(request):
    expenses = Expense.objects.select_related('employee__user', 'project', 'new_expense_type').filter(status='Forwarded to Manager')
    return render(request, 'manager/expense_approval_dashboard.html', {'expenses': expenses})
    
def expense_approvals(request):
    pending_exp = Expense.objects.filter(status='SUBMITTED')  # all pending expenses
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        html_snippet = render_to_string('manager/partials/expense_table_rows.html', 
                                        {'expenses': pending_exp})
        return HttpResponse(html_snippet)
    context = {'expenses': pending_exp, 'current_page': 'expenses'}
    return render(request, 'manager/expense_approvals.html', context)    

@login_required
def handle_expense_action(request, expense_id, action):
    expense = get_object_or_404(Expense, id=expense_id)

    if request.method == 'POST':
        remark = request.POST.get('manager_remark', '').strip()

        if not remark:
            messages.error(request, "Remark is required.")
            return redirect('manager:expense-approval')

        if action == 'approve':
            expense.status = 'Approved'
            expense.manager_remark = remark
            messages.success(request, "Expense approved.")
            notify_employee(expense, 'Approved', remark)

        elif action == 'reject':
            expense.status = 'Rejected'
            expense.manager_remark = remark
            messages.success(request, "Expense rejected.")
            notify_employee(expense, 'Rejected', remark)

        else:
            messages.error(request, "Invalid action.")
            return redirect('manager:expense-approval')

        expense.save()
        return redirect('manager:expense-approval')
    else:
        return redirect('manager:expense-approval')




def notify_employee(expense, action, remark):
    subject = f"Your expense has been {action}"
    message = f"""
Dear {expense.employee.user.get_full_name()},

Your expense submitted on {expense.date} for project '{expense.project.name}' has been {action.lower()} by your manager.

Manager Remark:
{remark or 'No remarks provided.'}

Regards,
Accounts Team
"""
    send_mail(
        subject,
        message,
        'noreply@yourcompany.com',  # Update this with your valid sender email
        [expense.employee.user.email],
        fail_silently=True,
    )


from timesheet.models import Timesheet

@login_required
@user_passes_test(is_manager)
def timesheet_approval_dashboard(request):
    timesheets = Timesheet.objects.select_related('employee__user', 'project', 'task') \
                                  .filter(status='Pending') \
                                  .order_by('-date', 'time_from')
    return render(request, 'manager/timesheet_approval_dashboard.html', {'timesheets': timesheets})
    
    
from django.template.loader import render_to_string

def timesheet_approvals(request):
    pending_ts = Timesheet.objects.filter(status='SUBMITTED')  # all pending timesheets
    # If AJAX request (XHR), return a partial HTML (table rows) 
    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        html_snippet = render_to_string('manager/partials/timesheet_table_rows.html', 
                                        {'timesheets': pending_ts})
        return HttpResponse(html_snippet)
    # Otherwise, render full page
    context = {'timesheets': pending_ts, 'current_page': 'timesheets'}
    return render(request, 'manager/timesheet_approvals.html', context)    


@login_required
@user_passes_test(is_manager)
@require_POST
def handle_timesheet_action(request, timesheet_id, action):
    timesheet = get_object_or_404(Timesheet, id=timesheet_id)

    remark = request.POST.get('manager_remark', '').strip()
    if not remark:
        messages.error(request, "Manager remark is required.")
        return redirect('manager:timesheet-approval')

    if action == 'approve':
        timesheet.status = 'Approved'
        messages.success(request, "Timesheet approved.")
    elif action == 'reject':
        timesheet.status = 'Rejected'
        messages.success(request, "Timesheet rejected.")
    else:
        messages.error(request, "Invalid action.")
        return redirect('manager:timesheet-approval')

    timesheet.manager_remark = remark
    timesheet.save()
    return redirect('manager:timesheet-approval')




@login_required
@user_passes_test(is_manager)
def project_tracking_dashboard(request):
    projects = Project.objects.all()
    project_data = []

    for project in projects:
        data = calculate_project_progress(project)
        project_data.append({
            'project': project,
            'expenses': data['total_expense'],
            'earnings': data['earnings'],
            'days_worked': data['days_worked'],
            'budget_utilized': data['budget_utilized'],
        })

    return render(request, 'manager/project_tracking_dashboard.html', {
        'projects': project_data,
    })







@login_required
@user_passes_test(is_manager)
def project_summary_dashboard(request):
    projects = Project.objects.all()
    project_data = []

    for project in projects:
        timesheets = Timesheet.objects.filter(project=project, status='Approved')
        expenses = Expense.objects.filter(project=project, status='Approved')

        

        total_hours = sum(
            (datetime.combine(t.date, t.time_to) - datetime.combine(t.date, t.time_from)).total_seconds() / 3600
            for t in timesheets
)

        
        total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0

        project.total_hours = total_hours
        project.total_expenses = total_expenses

        project_data.append(project)

    # Extract labels and datasets for Chart.js
    labels = [p.name for p in project_data]
    hours = [p.total_hours for p in project_data]
    expenses = [p.total_expenses for p in project_data]

    export_fmt = request.GET.get('export')
    if export_fmt == 'csv':
        response = HttpResponse(content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="project_summary.csv"'
        writer = csv.writer(response)
        writer.writerow(["Project", "Total Hours", "Total Expenses"])
        for p in project_data:
            writer.writerow([p.name, p.total_hours, p.total_expenses])
        return response

    if export_fmt == 'pdf':
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        p.drawString(50, 800, "Project Summary Report")
        p.drawString(50, 780, "Project - Total Hours - Total Expenses")
        y = 760
        for proj in project_data:
            line = f"{proj.name} - {proj.total_hours}h - ₹{proj.total_expenses}"
            p.drawString(50, y, line)
            y -= 20
        p.showPage()
        p.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename="project_summary.pdf")

    context = {
        'projects': project_data,
        'chart_labels': labels,
        'chart_hours': hours,
        'chart_expenses': expenses,
        'current_page': 'summary'
    }
    return render(request, 'manager/project_summary_dashboard.html', context)




def project_detail(request, project_id):
    project = Project.objects.get(id=project_id)
    # Base queryset for related records (e.g., timesheet entries or tasks for this project)
    records = Timesheet.objects.filter(project=project)  # or whatever model represents project detail entries

    # 1. Apply filters if provided in GET parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    employee_id = request.GET.get('employee')
    if start_date:
        records = records.filter(date__gte=start_date)
    if end_date:
        records = records.filter(date__lte=end_date)
    if employee_id:
        records = records.filter(employee_id=employee_id)
    # Now 'records' contains only entries matching the filter criteria.

    # 2. Handle export request (similar pattern as summary view)
    export_fmt = request.GET.get('export')
    if export_fmt == 'csv':
        response = HttpResponse(content_type="text/csv")
        response['Content-Disposition'] = f'attachment; filename="project_{project.id}_detail.csv"'
        writer = csv.writer(response)
        writer.writerow(["Date", "Employee", "Task/Description", "Hours", "Expense"])
        for rec in records:
            writer.writerow([rec.date, rec.employee.name, rec.description, rec.hours, rec.expense_amount])
        return response
    if export_fmt == 'pdf':
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        title = f"Project {project.name} Detail Report"
        p.drawString(50, 800, title)
        header = "Date       Employee       Description       Hours   Expense"
        p.drawString(50, 780, header)
        y = 760
        for rec in records:
            line = f"{rec.date}  {rec.employee.name}  {rec.description[:15]}...  {rec.hours}h   ${rec.expense_amount}"
            p.drawString(50, y, line)
            y -= 15
            if y < 50:  # simple page break logic
                p.showPage(); y = 800
        p.showPage()
        p.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f"project_{project.id}_detail.pdf")

    # 3. Render the detail page with filtered records
    employees = EmployeeProfile.objects.filter(taskassignment__project=project).distinct()  # ✅  # employees involved in this project
    context = {
        'project': project,
        'records': records,
        'employees': employees,
        'current_page': 'detail'
    }
    return render(request, 'manager/project_detail.html', context)

