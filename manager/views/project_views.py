from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, FileResponse
from manager.utils import calculate_project_progress
from project.models import Project
from employee.models import EmployeeProfile
from timesheet.models import Timesheet
from expenses.models import Expense
from reportlab.pdfgen import canvas
from django.db.models import Sum
from datetime import datetime
import io, csv
from accounts.access_control import is_manager_or_admin, is_manager


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

    
    
    
    