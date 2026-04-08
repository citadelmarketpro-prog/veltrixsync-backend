from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Usage: {{ my_dict|get_item:key }}"""
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)
