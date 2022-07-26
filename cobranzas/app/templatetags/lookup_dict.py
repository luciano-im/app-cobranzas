from django import template

register = template.Library()


@register.filter
def lookup_dict(d: dict, key):
    return d.get(key, None)