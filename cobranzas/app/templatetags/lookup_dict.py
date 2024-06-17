from django import template

register = template.Library()


@register.simple_tag
def lookup_dict(d: dict, key):
    return d.get(key, None)