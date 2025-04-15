from django import template

register = template.Library()



@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, "-")





# Example of your custom filter
@register.filter
def get_skill_rating(skills_dict, subskill_name):
    return skills_dict.get(subskill_name, None)
