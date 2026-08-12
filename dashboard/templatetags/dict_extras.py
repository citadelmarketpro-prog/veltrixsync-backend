from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Usage: {{ my_dict|get_item:key }}"""
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)


@register.filter
def str_in(value, container):
    """
    Usage: {{ value|str_in:container }}
    Membership check that coerces both sides to str first — needed because
    BoundField.value() for a ModelMultipleChoiceField returns a list of int
    pks when the form is bound to an instance (GET) but a list of str pks
    when bound to POST data, so a plain `in` check breaks one case or the
    other depending on which type you compare against.
    """
    if not container:
        return False
    return str(value) in [str(v) for v in container]
