# skills/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.urls import reverse
import csv
import json
import logging
from collections import defaultdict
from django.db.models import Avg

from .models import (
    MainSkill, SubSkill, EmployeeSkill,
    SkillQuestion, EmployeeAnswer
)
# employee app
from employee.models import EmployeeProfile

logger = logging.getLogger(__name__)


# list overview views for quick verification
from django.contrib.auth.decorators import login_required

@login_required
def skill_overview(request):
    """
    Simple page listing SkillCategory, SkillMatrix and some EmployeeSkill samples.
    Useful to verify that models & migrations are active.
    """
    categories = SkillCategory.objects.all().order_by('order', 'name')
    matrices = SkillMatrix.objects.all().order_by('-created_at')[:20]
    sample_skills = EmployeeSkill.objects.select_related('employee__user', 'main_skill', 'subskill')[:100]
    return render(request, 'skills/overview.html', {
        'categories': categories,
        'matrices': matrices,
        'sample_skills': sample_skills,
    })


def _employee_skill_value(emp_skill):
    """
    Return the canonical rating value for display/aggregation:
    prefer `proficiency` if not None, else fall back to legacy `rating`.
    """
    if not emp_skill:
        return None
    if getattr(emp_skill, 'proficiency', None) is not None:
        try:
            return int(emp_skill.proficiency)
        except Exception:
            # if stored as decimal or string, coerce safely
            try:
                return int(float(emp_skill.proficiency))
            except Exception:
                return int(emp_skill.rating or 0)
    try:
        return int(emp_skill.rating or 0)
    except Exception:
        return 0


# fallback for access control helper if accounts.access_control not present
try:
    from accounts.access_control import is_manager
except Exception:
    def is_manager(user):
        return user.has_perm('timesheet.can_approve')


# ---------------------------
# Helper decorators / utils
# ---------------------------
def manager_required(view_func):
    return user_passes_test(lambda u: u.is_superuser or is_manager(u))(view_func)


def compute_skill_rating_for_employee(employee_profile, main_skill):
    """Return rounded float (2 decimals) average of manager_rating for questions for given main_skill, or None."""
    ratings = EmployeeAnswer.objects.filter(employee=employee_profile, question__main_skill=main_skill).values_list('manager_rating', flat=True)
    ratings = [r for r in ratings if r is not None]
    if not ratings:
        return None
    return round(sum(ratings) / len(ratings), 2)


# ---------------------------
# Views
# ---------------------------

@login_required
@permission_required('timesheet.can_approve')
def assign_skills(request):
    """
    Main skills page: assign subskills to employees, add main/sub skills,
    shows existing skills/subskills, skill matrix and add-question form.
    """
    try:
        from .forms import AssignSkillForm, MainSkillForm, SubSkillForm, SkillQuestionForm
    except Exception as e:
        logger.exception("Forms import error in assign_skills: %s", e)
        messages.error(request, "Forms configuration error.")
        return redirect('/dashboard/')

    try:
        form = AssignSkillForm()
        main_form = MainSkillForm()
        sub_form = SubSkillForm()

        # employee list scope: managers see their reportees; superuser sees all
        if request.user.is_superuser:
            employees = EmployeeProfile.objects.select_related("user").all().order_by("user__first_name", "user__last_name")
        else:
            if is_manager(request.user):
                employees = EmployeeProfile.objects.select_related("user").filter(reporting_manager=request.user).order_by("user__first_name", "user__last_name")
            else:
                employees = EmployeeProfile.objects.select_related("user").filter(user=request.user)

        if request.method == 'POST':
            # ASSIGN skill row
            if 'assign' in request.POST:
                form = AssignSkillForm(request.POST)
                if form.is_valid():
                    emp = form.cleaned_data.get('employee')
                    if not request.user.is_superuser and not (is_manager(request.user) and emp and emp.reporting_manager_id == request.user.pk):
                        messages.error(request, "You can assign skills only to your reportees.")
                    else:
                        form.save()
                        messages.success(request, "Skill assigned successfully.")
                        return redirect('skills:assign-skills')
                else:
                    messages.error(request, "Please correct errors in the assign form.")

            # ADD MAIN SKILL
            elif 'add_main' in request.POST:
                main_form = MainSkillForm(request.POST)
                if main_form.is_valid():
                    main_form.save()
                    messages.success(request, "Main skill added successfully.")
                    return redirect('skills:assign-skills')
                else:
                    messages.error(request, "Please correct errors in the main skill form.")

            # ADD SUB SKILL
            elif 'add_sub' in request.POST:
                sub_form = SubSkillForm(request.POST)
                if sub_form.is_valid():
                    sub_form.save()
                    messages.success(request, "Subskill added successfully.")
                    return redirect('skills:assign-skills')
                else:
                    messages.error(request, "Please correct errors in the subskill form.")

            # ADD QUESTION (from the Add Question form)
            elif 'add_question' in request.POST:
                q_main = request.POST.get('question_main_skill')
                q_sub = request.POST.get('question_subskill') or None
                q_text = request.POST.get('question_text', '').strip()
                q_order = request.POST.get('question_order', '').strip()

                if not q_main or not q_text:
                    messages.error(request, "Main skill and question text are required.")
                else:
                    try:
                        main_obj = MainSkill.objects.get(id=int(q_main))
                    except Exception:
                        messages.error(request, "Selected main skill not found.")
                        main_obj = None

                    sub_obj = None
                    if q_sub:
                        try:
                            sub_obj = SubSkill.objects.get(id=int(q_sub), main_skill=main_obj)
                        except Exception:
                            messages.error(request, "Selected subskill not found for the chosen main skill.")
                            sub_obj = None

                    if main_obj and q_text:
                        # determine order: prefer provided order but if it conflicts, pick next free order
                        try:
                            requested_order = int(q_order) if str(q_order).isdigit() else None
                        except Exception:
                            requested_order = None

                        # compute existing orders for this (main_skill, subskill) pair
                        existing_orders = list(SkillQuestion.objects.filter(
                            main_skill=main_obj,
                            subskill=sub_obj
                        ).values_list('order', flat=True))

                        existing_set = set(existing_orders)
                        if requested_order is None:
                            # pick next available (max+1 or 1)
                            if existing_orders:
                                next_order = max(existing_orders) + 1
                            else:
                                next_order = 1
                        else:
                            if requested_order in existing_set:
                                # find smallest positive integer not in set starting from requested_order
                                cand = requested_order
                                while cand in existing_set:
                                    cand += 1
                                next_order = cand
                            else:
                                next_order = requested_order

                        try:
                            SkillQuestion.objects.create(
                                main_skill=main_obj,
                                subskill=sub_obj,
                                text=q_text,
                                order=next_order
                            )
                            messages.success(request, f"Question added (order={next_order}).")
                            return redirect('skills:assign-skills')
                        except Exception as e:
                            logger.exception("Failed to create SkillQuestion: %s", e)
                            messages.error(request, "Failed adding question: " + str(e))

        # ------------------------
        # build matrix with aggregates
        # ------------------------
        # fetch assigned employee skills
        assigned_skills = EmployeeSkill.objects.select_related('employee__user', 'main_skill', 'subskill').filter(employee__in=employees)

        # compute aggregated manager_rating per (employee, main_skill)
        # ignore nulls by filtering and use DB aggregation
        from django.db.models import Avg
        answers_agg = EmployeeAnswer.objects.filter(employee__in=employees).values('employee_id', 'question__main_skill').annotate(avg_rating=Avg('manager_rating'))
        aggregated_map = {}
        for row in answers_agg:
            emp_id = row.get('employee_id')
            main_skill_id = row.get('question__main_skill')
            avg = row.get('avg_rating')
            if avg is not None:
                aggregated_map[(emp_id, main_skill_id)] = round(float(avg), 2)

        # prepare matrix rows
        employee_matrix = []
        # cache main skills and subskills to avoid DB inside loops
        main_skills = list(MainSkill.objects.all().order_by('name'))
        subskills = list(SubSkill.objects.select_related('main_skill').all().order_by('main_skill__name', 'name'))

        for emp in employees:
            skills = assigned_skills.filter(employee=emp)
            skill_dict = {}
            subskill_map = {}   # subskill_id -> rating (from EmployeeSkill)
            for skill in skills:
                if skill.main_skill and skill.subskill:
                    key = f"{skill.main_skill.name}|{skill.subskill.name}"
                    val = _employee_skill_value(skill)
                    skill_dict[key] = val
                    subskill_map[skill.subskill.id] = val


            # per main-skill aggregates (from EmployeeAnswer)
            per_main_aggregates = {}
            for ms in main_skills:
                agg = aggregated_map.get((emp.id, ms.id))
                if agg is not None:
                    per_main_aggregates[ms.id] = agg

            employee_matrix.append({
                'employee': emp,
                'skill_dict': skill_dict,
                'subskill_map': subskill_map,
                'aggregates': per_main_aggregates,
            })

        # --- Flags for template (avoid method calling in templates) ---
        can_evaluate = request.user.is_superuser or request.user.has_perm('timesheet.can_approve')
        employee_profile = getattr(request.user, 'employeeprofile', None)
        is_employee_user = False
        if employee_profile:
            is_employee_user = employees.filter(id=employee_profile.id).exists()

        return render(request, 'skills/assign_skills.html', {
            'form': form,
            'main_form': main_form,
            'sub_form': sub_form,
            'skill_matrix': employee_matrix,
            'main_skills': main_skills,
            'subskills': subskills,
            'employees': employees,
            'can_evaluate': can_evaluate,
            'is_employee_user': is_employee_user,
        })
    except Exception as e:
        logger.exception("Error in assign_skills: %s", e)
        messages.error(request, "An error occurred while processing your request")
        return redirect('/dashboard/')




@login_required
def my_skills(request):
    """
    Employee view: show answers and computed aggregated ratings for main skills.
    """
    try:
        profile = getattr(request.user, 'employeeprofile', None)
        if not profile:
            messages.error(request, "Employee profile not found.")
            return redirect('/dashboard/')
        # answers
        answers = EmployeeAnswer.objects.filter(employee=profile).select_related('question__main_skill', 'question__subskill')
        # compute aggregated per main_skill
        tmp = defaultdict(list)
        for a in answers:
            if a.manager_rating is not None:
                tmp[a.question.main_skill_id].append(a.manager_rating)
        skill_scores = {}
        for ms_id, ratings in tmp.items():
            if ratings:
                skill_scores[ms_id] = round(sum(ratings) / len(ratings), 2)

        emp_skills = EmployeeSkill.objects.filter(employee=profile).select_related('main_skill', 'subskill')

        return render(request, 'skills/my_skills.html', {
            'employee_profile': profile,
            'skills': emp_skills,
            'skill_scores': skill_scores,
        })
    except Exception as exc:
        logger.exception("Error in my_skills: %s", exc)
        messages.error(request, "Unable to load skills.")
        return redirect('/dashboard/')


@login_required
@permission_required('timesheet.can_approve')
def load_subskills(request):
    main_skill_id = request.GET.get('main_skill_id') or request.GET.get('main_skill')
    if not main_skill_id:
        return JsonResponse([], safe=False)
    subskills = SubSkill.objects.filter(main_skill_id=main_skill_id).values('id', 'name').order_by('name')
    return JsonResponse(list(subskills), safe=False)


@login_required
@permission_required('timesheet.can_approve')
def export_skill_matrix(request):
    """
    Export employee skills as CSV.

    By default this returns columns:
      Employee ID, Employee Name, Main Skill, Subskill, Rating

    If caller provides ?include_new=1 (or true/yes) then additional columns are appended:
      proficiency, years_experience, certified

    Examples:
      /skills/export-skill-matrix/                -> original CSV (backwards compatible)
      /skills/export-skill-matrix/?include_new=1  -> CSV with extra columns
    """
    include_new_raw = (request.GET.get('include_new') or request.GET.get('includeNew') or request.GET.get('include-new'))
    include_new = False
    if include_new_raw:
        include_new = str(include_new_raw).lower() in ("1", "true", "yes", "y")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="skill_matrix.csv"'
    writer = csv.writer(response)

    # Base headers (keep original order)
    headers = ['Employee ID', 'Employee Name', 'Main Skill', 'Subskill', 'Rating']

    # Extra headers for new columns (appended when requested)
    extra_headers = ['Proficiency', 'Years Experience', 'Certified']
    if include_new:
        headers.extend(extra_headers)

    writer.writerow(headers)

    # Query all skills
    all_skills = EmployeeSkill.objects.select_related('employee__user', 'main_skill', 'subskill').order_by('employee__id', 'main_skill__name', 'subskill__name')
    for skill in all_skills:
        employee_id = skill.employee.id
        employee_name = skill.employee.user.get_full_name() if getattr(skill.employee, 'user', None) else str(skill.employee)
        main_skill_name = skill.main_skill.name if skill.main_skill else ''
        subskill_name = skill.subskill.name if skill.subskill else ''
        rating = skill.rating if skill.rating is not None else ''

        row = [employee_id, employee_name, main_skill_name, subskill_name, rating]

        if include_new:
            # prefer explicit proficiency (new field), fall back to rating if proficiency is empty
            prof = getattr(skill, 'proficiency', None)
            if prof is None:
                prof_out = rating if rating != '' else ''
            else:
                # cast decimals to string nicely
                try:
                    prof_out = str(int(prof))
                except Exception:
                    prof_out = str(prof)
            years = getattr(skill, 'years_experience', '') if getattr(skill, 'years_experience', None) is not None else ''
            certified = getattr(skill, 'certified', False)
            certified_out = 'Yes' if certified else 'No'

            row.extend([prof_out, years, certified_out])

        writer.writerow(row)

    return response



@login_required
@permission_required('timesheet.can_approve')
def get_employee_skill_data(request):
    employee_id = request.GET.get('employee_id')
    if not employee_id:
        return JsonResponse([], safe=False)
    try:
        profile = EmployeeProfile.objects.get(id=employee_id)
    except EmployeeProfile.DoesNotExist:
        return JsonResponse([], safe=False)
    skills = EmployeeSkill.objects.filter(employee=profile).select_related('main_skill', 'subskill')
    data = [{
        'main_skill': skill.main_skill.name if skill.main_skill else '',
        'subskill': skill.subskill.name if skill.subskill else '',
        'subskill_id': skill.subskill.id if skill.subskill else None,
        'rating': _employee_skill_value(skill)
    } for skill in skills]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_POST
@login_required
@permission_required('timesheet.can_approve')
def edit_skill_assignment(request):
    try:
        if request.content_type and 'application/json' in request.content_type:
            payload = json.loads(request.body.decode('utf-8') or '{}')
            employee_id = payload.get('employee_id')
            ratings = payload.get('ratings', {}) or {}
        else:
            employee_id = request.POST.get('employee_id')
            ratings = {}
            for k, v in request.POST.items():
                if k.startswith('ratings[') and k.endswith(']'):
                    sid = k[len('ratings['):-1]
                    ratings[sid] = v
                elif k.isdigit():
                    ratings[k] = v
            maybe = request.POST.get('ratings')
            if maybe:
                try:
                    j = json.loads(maybe)
                    if isinstance(j, dict):
                        ratings = j
                except Exception:
                    pass
    except Exception as e:
        logger.exception("Failed to parse edit_skill_assignment payload: %s", e)
        return JsonResponse({'success': False, 'error': 'Invalid request payload'}, status=400)

    if not employee_id:
        return JsonResponse({'success': False, 'error': 'employee_id missing'}, status=400)

    try:
        profile = EmployeeProfile.objects.get(id=employee_id)
    except EmployeeProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Employee not found'}, status=404)

    if not request.user.is_superuser and not (is_manager(request.user) and profile.reporting_manager_id == request.user.pk):
        return JsonResponse({'success': False, 'error': 'You can update skills only for your reportees'}, status=403)

    updated = 0
    try:
        with transaction.atomic():
            for subskill_id_raw, rating_raw in ratings.items():
                try:
                    subskill_id = int(subskill_id_raw)
                    rating = int(rating_raw) if rating_raw is not None and str(rating_raw).strip() != '' else None
                except Exception:
                    continue

                if rating is None:
                    continue

                try:
                    subskill = SubSkill.objects.select_related('main_skill').get(id=subskill_id)
                except SubSkill.DoesNotExist:
                    continue

                # create or update: seed proficiency from rating when creating, and keep proficiency in sync if null
                emp_skill, created = EmployeeSkill.objects.get_or_create(
                    employee=profile,
                    main_skill=subskill.main_skill,
                    subskill=subskill,
                    defaults={'rating': rating, 'proficiency': rating}
                )
                if not created:
                    # if proficiency is None, populate it from rating; otherwise, update both rating and leave proficiency intact
                    changed = False
                    if emp_skill.rating != rating:
                        emp_skill.rating = rating
                        changed = True
                    if getattr(emp_skill, 'proficiency', None) is None:
                        emp_skill.proficiency = rating
                        changed = True
                    if changed:
                        # save both fields if changed
                        emp_skill.save(update_fields=['rating', 'proficiency', 'last_updated'] if hasattr(emp_skill, 'last_updated') else ['rating', 'proficiency'])
                        updated += 1
                else:
                    updated += 1
    except Exception as e:
        logger.exception("Error saving skill ratings: %s", e)
        return JsonResponse({'success': False, 'error': 'Database error'}, status=500)

    return JsonResponse({'success': True, 'updated': updated})


# ---------------------------
# Evaluation views (manager + employee flows)
# ---------------------------
@manager_required
def evaluate_skill_view(request, employee_id, main_skill_id, subskill_id=None):
    """
    Manager view: display questions for main_skill (or subskill specific), show employee answers,
    allow manager to rate each question (0-4) and enter/modify answer text. Aggregated rating is written back to EmployeeSkill.
    """
    try:
        profile = EmployeeProfile.objects.get(id=employee_id)
    except EmployeeProfile.DoesNotExist:
        messages.error(request, "Employee not found.")
        return redirect('skills:assign-skills')

    main_skill = get_object_or_404(MainSkill, id=main_skill_id)

    if not request.user.is_superuser and not (is_manager(request.user) and profile.reporting_manager_id == request.user.pk):
        messages.error(request, "You can view evaluations only for your reportees.")
        return redirect('skills:assign-skills')

    subskill = None
    if subskill_id:
        # if subskill_id passed as '0' in some flows, treat as None
        try:
            sid_int = int(subskill_id)
            if sid_int > 0:
                subskill = SubSkill.objects.get(id=sid_int, main_skill=main_skill)
        except (ValueError, SubSkill.DoesNotExist):
            subskill = None  # treat missing as None; we already verified permission for main_skill

    if subskill is not None:
        questions = SkillQuestion.objects.filter(main_skill=main_skill, subskill=subskill).order_by('order')
    else:
        questions = SkillQuestion.objects.filter(main_skill=main_skill, subskill__isnull=True).order_by('order')

    # ensure EmployeeAnswer rows exist
    for q in questions:
        EmployeeAnswer.objects.get_or_create(employee=profile, question=q)

    answers = EmployeeAnswer.objects.filter(employee=profile, question__in=questions).select_related('question').order_by('question__order')

    if request.method == 'POST':
        updated = 0
        for ans in answers:
            # answer text may be edited by manager to capture employee response (or manager enters on employee's behalf)
            answer_key = f"answer_{ans.question.id}"
            rating_key = f"rating_{ans.question.id}"
            notes_key = f"notes_{ans.question.id}"

            if answer_key in request.POST:
                ans.answer_text = request.POST.get(answer_key) or ''

            if rating_key in request.POST:
                try:
                    val = request.POST.get(rating_key)
                    if val == '':
                        val = None
                    else:
                        val = int(val)
                        if val < 0 or val > 4:
                            raise ValueError()
                except Exception:
                    val = None
                ans.manager_rating = val

            if notes_key in request.POST:
                ans.manager_notes = request.POST.get(notes_key) or ''

            ans.save()
            updated += 1

        # AGGREGATE (average of non-null ratings) and write back to EmployeeSkill
        ratings = [a.manager_rating for a in answers if a.manager_rating is not None]
        aggregated_float = None
        if ratings:
            avg = sum(ratings) / len(ratings)
            aggregated_float = round(avg, 2)
            aggregated_int = int(round(avg))
            # update or create EmployeeSkill (use first subskill if needed)
            emp_skills = EmployeeSkill.objects.filter(employee=profile, main_skill=main_skill)
            if emp_skills.exists():
                # update both legacy rating and new proficiency to reflect aggregation
                emp_skills.update(rating=aggregated_int, proficiency=aggregated_int)
            else:
                # choose a subskill to attach the aggregated rating; prefer the subskill we evaluated, else first available
                use_sub = subskill or SubSkill.objects.filter(main_skill=main_skill).first()
                if use_sub:
                    EmployeeSkill.objects.create(
                        employee=profile,
                        main_skill=main_skill,
                        subskill=use_sub,
                        rating=aggregated_int,
                        proficiency=aggregated_int
                    )

        messages.success(request, f"Saved ratings/answers for {updated} questions. Aggregated: {aggregated_float if aggregated_float is not None else 'N/A'}")
        # redirect back appropriately
        if subskill:
            return redirect('skills:evaluate-skill-sub', employee_id=profile.id, main_skill_id=main_skill.id, subskill_id=subskill.id)
        else:
            return redirect('skills:evaluate-skill', employee_id=profile.id, main_skill_id=main_skill.id)

    aggregated_display = compute_skill_rating_for_employee(profile, main_skill)

    return render(request, 'skills/evaluate_skills.html', {
        'employee': profile,
        'main_skill': main_skill,
        'answers': answers,
        'aggregated': aggregated_display,
    })


@manager_required
@require_http_methods(["POST"])
def save_evaluation(request, employee_id, main_skill_id):
    """AJAX POST endpoint to save ratings (optional)."""
    try:
        profile = EmployeeProfile.objects.get(id=employee_id)
    except EmployeeProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'employee not found'}, status=404)

    main_skill = get_object_or_404(MainSkill, id=main_skill_id)
    try:
        if request.content_type and 'application/json' in request.content_type:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        else:
            payload = request.POST.dict()
    except Exception:
        return JsonResponse({'success': False, 'error': 'invalid payload'}, status=400)

    updated = 0
    for qid, val in payload.items():
        try:
            if qid.startswith('rating_'):
                qid_num = int(qid.split('_', 1)[1])
                rating_val = None if val == '' else int(val)
            else:
                qid_num = int(qid)
                rating_val = None if val == '' else int(val)
        except Exception:
            continue
        try:
            ans = EmployeeAnswer.objects.get(employee=profile, question_id=qid_num)
            ans.manager_rating = rating_val
            ans.save(update_fields=['manager_rating', 'updated_at'])
            updated += 1
        except EmployeeAnswer.DoesNotExist:
            continue

    return JsonResponse({'success': True, 'updated': updated})


@login_required
def answer_skill_questions(request, main_skill_id, subskill_id=None):
    """
    Employee view: show questions for a main_skill (optionally subskill) so employee can submit answers.
    """
    try:
        profile = getattr(request.user, 'employeeprofile', None)
        if not profile:
            messages.error(request, "Employee profile not found.")
            return redirect('/dashboard/')

        main_skill = get_object_or_404(MainSkill, id=main_skill_id)
        subskill = None
        if subskill_id:
            try:
                subskill = SubSkill.objects.get(id=subskill_id, main_skill=main_skill)
            except SubSkill.DoesNotExist:
                messages.error(request, "Selected subskill not found for this main skill.")
                return redirect('/dashboard/')

        if subskill is not None:
            questions = SkillQuestion.objects.filter(main_skill=main_skill, subskill=subskill).order_by('order')
        else:
            questions = SkillQuestion.objects.filter(main_skill=main_skill, subskill__isnull=True).order_by('order')

        for q in questions:
            EmployeeAnswer.objects.get_or_create(employee=profile, question=q)

        answers = EmployeeAnswer.objects.filter(employee=profile, question__in=questions).select_related('question').order_by('question__order')

        if request.method == 'POST':
            for ans in answers:
                key = f"answer_{ans.question_id}"
                if key in request.POST:
                    ans.answer_text = request.POST.get(key) or ''
                    ans.save(update_fields=['answer_text', 'updated_at'])
            messages.success(request, "Your answers have been saved.")
            return redirect('skills:my-skills')

        return render(request, 'skills/answer_questions.html', {
            'main_skill': main_skill,
            'subskill_id': subskill_id,
            'answers': answers,
        })
    except Exception as e:
        logger.exception("Error in answer_skill_questions: %s", e)
        messages.error(request, "An error occurred.")
        return redirect('/dashboard/')
