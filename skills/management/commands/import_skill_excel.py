# skills/management/commands/import_skill_excel.py
import pandas as pd
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from skills.models import SkillCategory, MainSkill, SubSkill, EmployeeSkill
from employee.models import EmployeeProfile

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Import skills and team skill matrix from an Excel file."

    def add_arguments(self, parser):
        parser.add_argument('xlsx_path', type=str, help="Path to the Excel file")

    def handle(self, *args, **options):
        path = options['xlsx_path']
        self.stdout.write(f"Loading {path}")
        xls = pd.ExcelFile(path)
        # Heuristic: first sheet contains "Matrix" — parse main skills/subskills
        # second contains 'Team with Skill' — parse employee rows
        if 'Matrix' in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name='Matrix', header=None)
            self._import_matrix(df)
        if 'Team with Skill' in xls.sheet_names:
            df2 = pd.read_excel(xls, sheet_name='Team with Skill', header=None)
            self._import_team(df2)
        self.stdout.write("Import completed.")

    def _import_matrix(self, df):
        # Naive parse: look for columns where a header exists and treat them as main skills
        # This should be adapted to your exact file structure.
        self.stdout.write("Parsing Matrix sheet...")
        for col in df.columns:
            col_vals = df[col].dropna().astype(str).tolist()
            if not col_vals:
                continue
            # Skip rows like 'Sr. No' etc — heuristics:
            head = col_vals[0].strip()
            if head.lower().startswith('sr') or head.lower().startswith('dept'):
                # find main skills appearing in rest of column
                for v in col_vals[1:]:
                    s = v.strip()
                    if not s:
                        continue
                    # entries can be comma separated subskills; split and create as mainskill if unique
                    subskills = [x.strip() for x in s.split(',') if x.strip()]
                    # If only one item, treat as mainskill name
                    if len(subskills) == 1:
                        ms_name = subskills[0]
                        ms, _ = MainSkill.objects.get_or_create(name=ms_name)
                    else:
                        # when multiple, create a generic category (use head or column index)
                        for ss in subskills:
                            # try to find existing main skill by substring match
                            ms, _ = MainSkill.objects.get_or_create(name=ss)
                    # We cannot reliably map main->sub here unless the sheet is well structured
        self.stdout.write("Matrix parsing finished. Please inspect created MainSkill/SubSkill records manually.")

    def _import_team(self, df):
        self.stdout.write("Parsing Team with Skill sheet...")
        # We're trying to find rows with employee names and skill lists. High variability.
        for idx, row in df.iterrows():
            vals = row.dropna().astype(str).tolist()
            if not vals:
                continue
            # Heuristic: if row has an email or person name pattern, try to map to EmployeeProfile
            # We'll search by full name in EmployeeProfile (assumes presence)
            possible_name = vals[1] if len(vals) > 1 else None
            if not possible_name:
                continue
            name = possible_name.strip().split('\\n')[0].strip()
            if not name:
                continue
            # Try match with EmployeeProfile user full name
            emp = None
            for e in EmployeeProfile.objects.select_related('user').all():
                fullname = e.user.get_full_name()
                if name.lower() in fullname.lower() or fullname.lower() in name.lower():
                    emp = e
                    break
            if not emp:
                self.stdout.write(f"Employee not found for name fragment: {name}, skipping.")
                continue
            # Try to detect skills in rest of row cols
            skill_text = ' '.join(vals[2:]) if len(vals) > 2 else ''
            if not skill_text.strip():
                continue
            # split by comma or newline
            parts = [p.strip() for p in skill_text.replace('\\n', ',').split(',') if p.strip()]
            for p in parts:
                # Try to match main skill or subskill by name
                sub = SubSkill.objects.filter(name__icontains=p).first()
                if sub:
                    EmployeeSkill.objects.get_or_create(employee=emp, main_skill=sub.main_skill, subskill=sub, defaults={'proficiency': 50})
                else:
                    main = MainSkill.objects.filter(name__icontains=p).first()
                    if main:
                        # create placeholder subskill
                        sub = SubSkill.objects.create(main_skill=main, name=p)
                        EmployeeSkill.objects.get_or_create(employee=emp, main_skill=main, subskill=sub, defaults={'proficiency': 50})
                    else:
                        # create main and sub
                        main = MainSkill.objects.create(name=p)
                        sub = SubSkill.objects.create(main_skill=main, name=p)
                        EmployeeSkill.objects.get_or_create(employee=emp, main_skill=main, subskill=sub, defaults={'proficiency': 50})

        self.stdout.write("Team with Skill parsing complete.")
