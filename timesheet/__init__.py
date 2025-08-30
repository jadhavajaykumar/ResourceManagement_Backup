from django.core.exceptions import ValidationError
from datetime import datetime, time, timedelta, date
from employee.models import EmployeeProfile
from project.models import Project, Task
from expenses.models import DailyAllowance
from timesheet.services.approval_service import approve_or_reject_timesheet
from timesheet.services.export_service import export_timesheets_to_csv
from project.services.da_service import calculate_da
from calendar import monthrange, monthcalendar
from django.utils.timezone import now
from django.db.models import Prefetch
from collections import defaultdict
from timesheet.utils.calculate_slot_hours import calculate_slot_hours
from django.utils.timezone import localdate
from timesheet.utils.styled_calendar import StyledCalendar
from django.db.models import Min, Max
from django.db import transaction
from timesheet.utils.time_utils import get_current_slot
from .models import CompOffApplication
from django.db.models import Q

from employee.models import LeaveBalance
from timesheet.utils.calendar_utils import get_timesheet_calendar_data
from timesheet.utils.calculate_attendance import calculate_attendance
from timesheet.utils.get_calendar_entries import get_calendar_entries
from manager.models import TaskAssignment
from employee.models import AuditLog
from .services.timesheet_service import process_timesheet_save
import json
import math
from django.forms import modelformset_factory
from datetime import datetime, timedelta, date as date_class, time as time_class
from django.http import JsonResponse  # if not already imported
from .forms import TimesheetForm, TimeSlotForm

from django.contrib.admin.views.decorators import staff_member_required

from timesheet.models import Timesheet, CompensatoryOff, CompOffBalance, TimeSlot, Attendance, Timesheet, TimeSlot

#from timesheet.utils import generate_time_slots  # ensure this is correct
import logging

# timesheet/views.py

@login_required
def load_tasks_for_employee(request):
    project_id = request.GET.get('project')
    employee = request.user.employeeprofile

    if not project_id:
        return JsonResponse([], safe=False)
        
        
     