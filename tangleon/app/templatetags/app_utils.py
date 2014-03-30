"""
Custom helper filters
"""

from django import template
from django.utils.timesince import timesince

register = template.Library()


@register.filter
def stripstr(value):
    """
    Strip spaces and new lines
    """
    return (value or '').strip()

@register.filter
def split_by_line(value):
    """
    Split string based on delimiter,
    """
    return value.split('\n\n')


@register.filter
def when(d, now=None):
    """
    Returns user friendly date difference with help of django timesince filter 
    """
    return timesince(d, now).split(',')[0]