from datetime import datetime
from django import template

register = template.Library()


@register.filter("parsetimestamp")
def timestamp(value):
    return datetime.fromtimestamp(value)


@register.filter
def price(value):
    return float(value) / 100


@register.filter
def choicefieldformat(value):
    return value.replace('_', ' ').title()


@register.filter
def index(indexable, i):
    return indexable[i]