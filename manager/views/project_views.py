from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
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


@login_required
@permission_required('timesheet.can_approve')
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
@permission_required('timesheet.can_approve')
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