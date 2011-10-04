# -*- coding: utf-8 -*-

from django import template

from scrum.projects.models import PRIORITES, ETATS, TYPES, STATUT

register = template.Library()

def var2txt(value, arg):
    if not isinstance(arg, unicode):
        return None
    if isinstance(value, dict):
        if arg in ('p', 'P', 'priorites'):
            if value in str(range(0,6)):
                return PRIORITES[int(value['item'].priorite)][1]
        if arg in ('e', 'E', 'etats'):
            if value in str(range(0,3)):
                return ETATS[int(value['item'].etat)][1]
        if arg in ('t', 'T', 'types'):
            if value in str(range(0,4)):
                return ETATS[int(value['item'].type)][1]
        if arg in ('s', 'S', 'statut'):
            if value in str(range(0,4)):
                return STATUT[int(value['item'].statut)][1]
    else:
        if arg in ('p', 'P', 'priorites'):
            if value in str(range(0,6)):
                return PRIORITES[int(value)][1]
        if arg in ('e', 'E', 'etats'):
            if value in str(range(0,3)):
                return ETATS[int(value)][1]
        if arg in ('t', 'T', 'types'):
            if value in str(range(0,4)):
                return TYPES[int(value)][1]
        if arg in ('s', 'S', 'statut'):
            if value in str(range(0,4)):
                return STATUT[int(value)][1]
    return None

register.filter('var2txt', var2txt)