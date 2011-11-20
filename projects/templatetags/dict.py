# -*- coding: utf-8 -*-

from django import template

register = template.Library()

def values(value, arg):
    if (isinstance(value, list) or isinstance(value, tuple)) and isinstance(arg, int):
        return value[arg]
    return dict(value)[arg]

def keys(value):
    if isinstance(value, list):
        return (v[0] for v in value)
    elif isinstance(value, dict):
        return value.keys()
    return None

register.filter('values', values)
register.filter('keys', keys)
