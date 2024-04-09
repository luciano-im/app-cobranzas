from django import template

register = template.Library()


@register.simple_tag
def get_total_delivered(obj):
    return sum(item.collection.paid_amount for item in obj)