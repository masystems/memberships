from datetime import datetime
from django import template

register = template.Library()


@register.filter("parsetimestamp")
def timestamp(value):
    return datetime.fromtimestamp(value)


@register.filter
def price(value):
    return value / 100