# -*- coding: utf-8 -*-

from django import template

register = template.Library()

def dict(value, arg):
    return value[arg]

register.filter('dict', dict)