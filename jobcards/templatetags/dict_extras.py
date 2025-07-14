from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    if not d:
        return []
    return d.get(key, [])

@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return ""
    return dictionary.get(key.upper(), "")