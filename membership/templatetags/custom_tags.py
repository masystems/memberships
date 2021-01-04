from datetime import datetime
from django import template

register = template.Library()


@register.filter("parsetimestamp")
def timestamp(value):
    return datetime.fromtimestamp(value)


@register.filter
def price(value):
    return int(value) / 100


@register.filter
def choicefieldformat(value):
    return value.replace('_', ' ').title()