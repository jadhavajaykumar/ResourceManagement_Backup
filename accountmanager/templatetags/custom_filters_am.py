from django import template
register = template.Library()

@register.filter
def get_employee(employee_map, emp_id):
    return employee_map.get(emp_id)
