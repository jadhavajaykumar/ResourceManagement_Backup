# expenses/views/reports.py
from datetime import datetime
from io import BytesIO
import os
import csv

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.utils.safestring import mark_safe

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, LongTable
)

from expenses.models import Expense, AdvanceRequest, DailyAllowance, AdvanceAdjustmentLog
from employee.models import EmployeeProfile
from project.models import Project


# -----------------------------
# Helpers
# -----------------------------
def _parse_date(arg):
    try:
        return datetime.strptime(arg, "%Y-%m-%d").date()
    except Exception:
        return None


def _fmt_money(x):
    try:
        return float(x or 0)
    except Exception:
        return 0.0


def _role_of(user):
    return getattr(getattr(user, "employeeprofile", None), "role", "") or ""


def _resolve_logo_path():
    """
    Resolve company logo path from static/images directory.
    Tries both logo.png and logo_1.png.
    Explicitly checks: ResourceManagement/static/images as you requested,
    then STATICFILES_DIRS, then BASE_DIR/static/images, then STATIC_ROOT/images.
    """
    candidates = ("logo.png", "logo_1.png")

    # 1) Explicit project path: ResourceManagement/static/images
    try:
        proj_images = os.path.join(settings.BASE_DIR, "ResourceManagement", "static", "images")
        for name in candidates:
            p = os.path.join(proj_images, name)
            if os.path.exists(p):
                return p
    except Exception:
        pass

    # 2) STATICFILES_DIRS
    for d in getattr(settings, "STATICFILES_DIRS", []):
        for name in candidates:
            p = os.path.join(d, "images", name)
            if os.path.exists(p):
                return p

    # 3) BASE_DIR/static/images
    base_static_images = os.path.join(settings.BASE_DIR, "static", "images")
    for name in candidates:
        p = os.path.join(base_static_images, name)
        if os.path.exists(p):
            return p

    # 4) STATIC_ROOT/images (after collectstatic)
    static_root = getattr(settings, "STATIC_ROOT", None)
    if static_root:
        for name in candidates:
            p = os.path.join(static_root, "images", name)
            if os.path.exists(p):
                return p

    return None


def _base_filters_and_scope(request):
    """
    Read filters from GET and enforce role-based scoping.
    - Employees: always limited to self (ignore employee filter).
    - Accountant/Manager/Account Manager: can filter by employee/project/date.
    """
    user = request.user
    role = (_role_of(user) or "").strip().lower()

    f = request.GET.get("from")
    t = request.GET.get("to")
    project = request.GET.get("project") or None
    employee = request.GET.get("employee") or None

    date_from = _parse_date(f)
    date_to = _parse_date(t)

    can_filter_by_employee = role in ["accountant", "manager", "account manager", "account-manager"]

    if not can_filter_by_employee:
        # force to self
        emp = getattr(user, "employeeprofile", None)
        employee = emp.id if emp else None

    # normalize "account-manager"
    if role == "account-manager":
        role = "account manager"

    return {
        "date_from": date_from,
        "date_to": date_to,
        "project_id": project,
        "employee_id": employee,
        "role": role,
        "can_filter_by_employee": can_filter_by_employee,
    }


def _querysets_filtered(scope):
    """Return filtered querysets for Expenses, Advances, DA, Adjustments."""
    date_from = scope["date_from"]
    date_to = scope["date_to"]
    project_id = scope["project_id"]
    employee_id = scope["employee_id"]

    exp = Expense.objects.select_related(
        "employee__user", "project", "new_expense_type", "advance_used"
    )
    adv = AdvanceRequest.objects.select_related("employee__user", "project")
    da = DailyAllowance.objects.select_related("employee__user", "project")
    adj = AdvanceAdjustmentLog.objects.select_related(
        "expense__employee__user", "expense__project",
        "advance__employee__user", "advance__project"
    )

    # Date filters (entity-native)
    if date_from:
        exp = exp.filter(date__gte=date_from)
        adv = adv.filter(date_requested__gte=date_from)   # list view uses request date
        da = da.filter(date__gte=date_from)
        adj = adj.filter(created_at__date__gte=date_from)  # logs use created_at date

    if date_to:
        exp = exp.filter(date__lte=date_to)
        adv = adv.filter(date_requested__lte=date_to)
        da = da.filter(date__lte=date_to)
        adj = adj.filter(created_at__date__lte=date_to)

    if project_id:
        exp = exp.filter(project_id=project_id)
        adv = adv.filter(project_id=project_id)
        da = da.filter(project_id=project_id)

    if employee_id:
        exp = exp.filter(employee_id=employee_id)
        adv = adv.filter(employee_id=employee_id)
        da = da.filter(employee_id=employee_id)
        adj = adj.filter(Q(expense__employee_id=employee_id) | Q(advance__employee_id=employee_id))

    return exp, adv, da, adj


# -----------------------------
# PDF building
# -----------------------------
def _header_footer(canvas, doc, title, subtitle, company_addr):
    canvas.saveState()

    # Header bar
    width, height = doc.pagesize
    header_h = 22 * mm
    canvas.setFillColorRGB(0.97, 0.97, 0.99)
    canvas.rect(0, height - header_h, width, header_h, fill=1, stroke=0)

    # Logo (if available)
    logo_path = _resolve_logo_path()
    if logo_path and os.path.exists(logo_path):
        try:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            max_w, max_h = 28*mm, 14*mm
            scale = min(max_w/iw, max_h/ih)
            w = iw * scale
            h = ih * scale
            canvas.drawImage(img, 12*mm, height - (h + 6*mm), width=w, height=h, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Titles
    canvas.setFillColorRGB(0.15, 0.15, 0.2)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(48*mm, height - 10*mm, title)
    canvas.setFont("Helvetica", 9)
    if subtitle:
        canvas.drawString(48*mm, height - 15*mm, subtitle)

    # Company address (right)
    if company_addr:
        canvas.setFont("Helvetica", 8)
        text = canvas.beginText()
        text.setTextOrigin(width - 80*mm, height - 10*mm)
        for line in company_addr.splitlines():
            text.textLine(line.strip())
        canvas.drawText(text)

    # Footer
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(width - 12*mm, 8*mm, f"Page {doc.page}")
    canvas.restoreState()


def _styled_title(text, styles):
    return Paragraph(f"<b>{text}</b>", styles["Heading2"])


def _kv_table(kvs, col1_w=50*mm, col2_w=110*mm):
    """
    Small key/value table used in summary blocks.
    """
    data = [[Paragraph(f"<b>{k}</b>", getSampleStyleSheet()["BodyText"]), Paragraph(str(v), getSampleStyleSheet()["BodyText"])] for k, v in kvs]
    t = Table(data, colWidths=[col1_w, col2_w])
    t.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 2),
    ]))
    return t


def _make_table(data, col_widths, header=True, zebra=True, small=False):
    """
    Create a nice, tight table that won’t overlap/cut columns.
    Uses LongTable so it flows across pages.
    """
    style = getSampleStyleSheet()
    head_style = ParagraphStyle("head", parent=style["BodyText"], fontName="Helvetica-Bold", fontSize=8 if small else 9)
    cell_style = ParagraphStyle("cell", parent=style["BodyText"], fontSize=8 if small else 9)

    # Convert strings to Paragraph for wrapping
    processed = []
    if header:
        processed.append([Paragraph(str(c), head_style) for c in data[0]])
        body = data[1:]
    else:
        body = data

    for row in body:
        processed.append([Paragraph(str(c), cell_style) if not isinstance(c, (Paragraph, Table)) else c for c in row])

    tbl = LongTable(processed, colWidths=col_widths, repeatRows=1 if header else 0)
    ts = [
        ("GRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke) if header else (),
    ]
    if zebra and len(processed) > 2:
        ts += [("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FBFBFD")) for i in range(1, len(processed)) if i % 2 == 0]
    tbl.setStyle(TableStyle([t for t in ts if t]))
    return tbl


# -----------------------------
# PDF Export (main endpoint)
# -----------------------------
@login_required
def export_report(request):
    """
    Branded PDF export with logo header & grouped sections.
    - Employees: only own data.
    - Accountant/Manager/Account Manager: can filter by employee/project/date.
    Add ?fmt=csv to get the CSV fallback for Expenses.
    """
    # CSV fallback kept for compatibility
    if (request.GET.get("fmt") or "").lower() == "csv":
        return export_report_csv(request)

    scope = _base_filters_and_scope(request)
    exp, adv, da, adj = _querysets_filtered(scope)

    # ---------- Correct summary semantics ----------
    # 1) Advance Credited in period: SETTLED advances filtered by settlement_date
    adv_credited_qs = AdvanceRequest.objects.select_related("employee__user", "project").filter(status="Settled")
    if scope["employee_id"]:
        adv_credited_qs = adv_credited_qs.filter(employee_id=scope["employee_id"])
    if scope["project_id"]:
        adv_credited_qs = adv_credited_qs.filter(project_id=scope["project_id"])
    if scope["date_from"]:
        adv_credited_qs = adv_credited_qs.filter(settlement_date__gte=scope["date_from"])
    if scope["date_to"]:
        adv_credited_qs = adv_credited_qs.filter(settlement_date__lte=scope["date_to"])
    total_advance_credited = _fmt_money(adv_credited_qs.aggregate(s=Sum("amount"))["s"] or 0)

    # 2) Used against expenses in period: sum of logs already date-scoped in `adj`
    total_deducted_in_period = _fmt_money(adj.aggregate(s=Sum("amount_deducted"))["s"] or 0)

    # 3) Cash-settled (no advance) in period: expense date semantics
    cash_settled_qs = exp.filter(reimbursed=True, status="Settled", advanceadjustmentlog__isnull=True)
    total_cash_settled = _fmt_money(cash_settled_qs.aggregate(s=Sum("amount"))["s"] or 0)

    # 4) Totals for sections (still by their natural dates)
    total_expenses = _fmt_money(exp.aggregate(s=Sum("amount"))["s"] or 0)
    total_da = _fmt_money(da.aggregate(s=Sum("da_amount"))["s"] or 0)

    # 5) Net advance delta (period change)
    advance_delta = total_advance_credited - total_deducted_in_period

    # Page setup
    buf = BytesIO()
    pagesize = landscape(A4)
    margin = 14 * mm
    doc = SimpleDocTemplate(
        buf,
        pagesize=pagesize,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=20*mm,
        bottomMargin=14*mm,
        title="Expense & Advance Report",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8))
    story = []

    # Header meta
    company_title = "Expense / Advance / DA Report"
    subtitle = ""
    if scope["date_from"] or scope["date_to"]:
        subtitle = f"Period: {scope['date_from'] or ''} to {scope['date_to'] or ''}"
    company_address = getattr(settings, "COMPANY_ADDRESS", "") or ""

    # SUMMARY
    story.append(_styled_title("Summary", styles))
    kvs = [
        ("Report Period", f"{scope['date_from'] or ''} to {scope['date_to'] or ''}"),
        ("Project Filter", scope["project_id"] or "All"),
        ("Employee Filter", scope["employee_id"] or "Self"),
        ("Total Expenses (this period)", f"{total_expenses:,.2f}"),
        ("Total DA (this period)", f"{total_da:,.2f}"),
        ("Advance Credited (Settled, by settlement date)", f"{total_advance_credited:,.2f}"),
        ("Used Against Expenses (logs in period)", f"{total_deducted_in_period:,.2f}"),
        ("Cash-Settled Expenses (no advance)", f"{total_cash_settled:,.2f}"),
        ("Advance Balance (this period delta)", f"{advance_delta:,.2f}"),
    ]
    story.append(_kv_table(kvs))
    story.append(Spacer(1, 6))

    # EXPENSES
    exp_headers = [
        "Date", "Employee", "Project", "Type",
        "Amount", "Status", "Stage", "Reimbursed", "Adv ID", "Remarks"
    ]
    exp_rows = []
    for e in exp.order_by("date", "id"):
        remarks = " / ".join(filter(None, [
            getattr(e, "accountant_remark", "") or "",
            getattr(e, "manager_remark", "") or "",
            getattr(e, "account_manager_remark", "") or "",
        ]))
        exp_rows.append([
            e.date.strftime("%Y-%m-%d") if e.date else "",
            e.employee.user.get_full_name() if e.employee_id else "",
            e.project.name if e.project_id else "",
            e.new_expense_type.name if e.new_expense_type_id else "",
            f"{_fmt_money(e.amount):,.2f}",
            e.status,
            e.current_stage,
            "Yes" if e.reimbursed else "No",
            f"#{e.advance_used_id}" if e.advance_used_id else "",
            remarks or "",
        ])
    if exp_rows:
        story.append(_styled_title("Expenses", styles))
        story.append(_make_table([exp_headers] + exp_rows,
                                 col_widths=[22*mm, 32*mm, 34*mm, 30*mm, 22*mm, 26*mm, 26*mm, 22*mm, 18*mm, 60*mm],
                                 small=True))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Total Expenses:</b> {total_expenses:,.2f}", styles["Small"]))
        story.append(Spacer(1, 8))
        story.append(PageBreak())

    # ADVANCES (list by request date; summary uses settlement date for credits)
    adv_headers = [
        "Requested", "Settled On", "Employee", "Project",
        "Amount", "Status", "Stage", "By Manager", "By Accountant", "Settled by AM", "Purpose", "Balance"
    ]
    adv_rows = []
    total_adv_list = 0.0
    for a in adv.order_by("date_requested", "id"):
        total_adv_list += _fmt_money(a.amount)
        adv_rows.append([
            a.date_requested.strftime("%Y-%m-%d") if a.date_requested else "",
            a.settlement_date.strftime("%Y-%m-%d") if a.settlement_date else "",
            a.employee.user.get_full_name() if a.employee_id else "",
            a.project.name if a.project_id else "",
            f"{_fmt_money(a.amount):,.2f}",
            a.status,
            a.current_stage,
            "Yes" if a.approved_by_manager else "No",
            "Yes" if a.approved_by_accountant else "No",
            "Yes" if a.settled_by_account_manager else "No",
            a.purpose or "",
            f"{_fmt_money(getattr(a, 'balance', 0)):,.2f}",
        ])
    if adv_rows:
        story.append(_styled_title("Advances", styles))
        story.append(_make_table([adv_headers] + adv_rows,
                                 col_widths=[22*mm, 22*mm, 32*mm, 32*mm, 22*mm, 24*mm, 22*mm, 18*mm, 22*mm, 22*mm, 40*mm, 22*mm],
                                 small=True))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Total Advances (listed by request date):</b> {total_adv_list:,.2f}", styles["Small"]))
        story.append(Spacer(1, 8))
        story.append(PageBreak())

    # DAILY ALLOWANCE
    da_headers = ["Date", "Employee", "Project", "DA Amount", "Currency", "Approved?", "Reimbursed?", "Extended?"]
    da_rows = []
    for d in da.order_by("date", "id"):
        da_rows.append([
            d.date.strftime("%Y-%m-%d") if d.date else "",
            d.employee.user.get_full_name() if d.employee_id else "",
            d.project.name if d.project_id else "",
            f"{_fmt_money(d.da_amount):,.2f}",
            d.currency or "",
            "Yes" if d.approved else "No",
            "Yes" if getattr(d, "reimbursed", False) else "No",
            "Yes" if getattr(d, "is_extended", False) else "No",
        ])
    if da_rows:
        story.append(_styled_title("Daily Allowance", styles))
        story.append(_make_table([da_headers] + da_rows,
                                 col_widths=[24*mm, 34*mm, 34*mm, 24*mm, 22*mm, 22*mm, 24*mm, 22*mm],
                                 small=True))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Total DA:</b> {total_da:,.2f}", styles["Small"]))
        story.append(Spacer(1, 8))
        story.append(PageBreak())

    # ADJUSTMENTS (detailed)
    adj_headers = [
        "Log Time", "Expense ID", "Expense Date", "Expense Type", "Expense Amt",
        "Advance ID", "Advance Date", "Advance Amt", "Deducted", "Employee", "Project"
    ]
    adj_rows = []
    total_adj = 0.0
    for lg in adj.order_by("created_at", "id"):
        e = lg.expense
        a = lg.advance
        total_adj += _fmt_money(lg.amount_deducted)
        adj_rows.append([
            lg.created_at.strftime("%Y-%m-%d %H:%M") if lg.created_at else "",
            f"#{e.id}" if e else "",
            e.date.strftime("%Y-%m-%d") if e and e.date else "",
            e.new_expense_type.name if e and e.new_expense_type_id else "",
            f"{_fmt_money(getattr(e, 'amount', 0)):,.2f}" if e else "0.00",
            f"#{a.id}" if a else "",
            a.date_requested.strftime("%Y-%m-%d") if a and a.date_requested else "",
            f"{_fmt_money(getattr(a, 'amount', 0)):,.2f}" if a else "0.00",
            f"{_fmt_money(lg.amount_deducted):,.2f}",
            (e.employee.user.get_full_name() if e and e.employee_id else (a.employee.user.get_full_name() if a and a.employee_id else "")),
            (e.project.name if e and e.project_id else (a.project.name if a and a.project_id else "")),
        ])

    if adj_rows:
        story.append(_styled_title("Advance Adjustments", styles))
        story.append(_make_table([adj_headers] + adj_rows,
                                 col_widths=[28*mm, 16*mm, 22*mm, 30*mm, 22*mm, 18*mm, 22*mm, 22*mm, 22*mm, 34*mm, 34*mm],
                                 small=True))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Total Deducted (logs in period):</b> {total_adj:,.2f}", styles["Small"]))
        story.append(Spacer(1, 8))

    # Build with branded header/footer on each page
    def on_page(canvas, doc_):
        _header_footer(canvas, doc_, company_title, subtitle, company_address)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    pdf = buf.getvalue()
    buf.close()

    fname = f"Report_{(scope['date_from'] or '')}_{(scope['date_to'] or '')}.pdf".replace(":", "-")
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{fname}"'
    return resp


# -----------------------------
# CSV fallback (kept)
# -----------------------------
@login_required
def export_report_csv(request):
    """
    Flat CSV of Expenses (kept as a fallback via ?fmt=csv)
    Honors the same role scoping and filters as the PDF.
    """
    scope = _base_filters_and_scope(request)
    exp, _, _, _ = _querysets_filtered(scope)

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="Expenses.csv"'
    w = csv.writer(resp)
    w.writerow([
        "Date","Employee","Project","Type","Amount","Status","Stage","Reimbursed","Advance ID",
        "Accountant Remark","Manager Remark","Account Manager Remark","From","To","Receipt"
    ])
    for e in exp.order_by("date","id"):
        w.writerow([
            e.date.strftime("%Y-%m-%d"),
            e.employee.user.get_full_name() if e.employee_id else "",
            e.project.name if e.project_id else "",
            e.new_expense_type.name if e.new_expense_type_id else "",
            _fmt_money(e.amount),
            e.status,
            e.current_stage,
            "Yes" if e.reimbursed else "No",
            e.advance_used_id or "",
            getattr(e, "accountant_remark", "") or "",
            getattr(e, "manager_remark", "") or "",
            getattr(e, "account_manager_remark", "") or "",
            e.from_location or "",
            e.to_location or "",
            "Yes" if e.receipt else ""
        ])
    return resp
