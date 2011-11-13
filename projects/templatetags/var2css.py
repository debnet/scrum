# -*- coding: utf-8 -*-

from django import template

ETATS = (
    ('0', 'todo'),
    ('1', 'todo'),
    ('2', 'run'),
    ('3', 'run'),
    ('4', 'done'),
)

PRIORITES = (
    ('0', 'none'),
    ('1', 'trivial'),
    ('2', 'minor'),
    ('3', 'major'),
    ('4', 'critical'),
    ('5', 'blocking'),
)

STATUT = (
    ('0', 'none'),
    ('1', 'major'),
    ('2', 'critical'),
    ('3', 'minor'),
)

register = template.Library()

def var2css(value, arg):
    if not isinstance(arg, unicode):
        return None
    if isinstance(value, dict):
        if arg in ('p', 'P', 'priorites'):
            return PRIORITES[int(value['item'].priorite)][1]
        if arg in ('e', 'E', 'etats'):
            return ETATS[int(value['item'].etat)][1]
        if arg in ('s', 'S', 'statut'):
            return STATUT[int(value['item'].statut)][1]
    else:
        if arg in ('p', 'P', 'priorites'):
            if value in str(range(0,6)):
                return PRIORITES[int(value)][1]
        if arg in ('e', 'E', 'etats'):
            if value in str(range(0,5)):
                return ETATS[int(value)][1]
        if arg in ('s', 'S', 'statut'):
            if value in str(range(0,4)):
                return STATUT[int(value)][1]
    return None

register.filter('var2css', var2css)