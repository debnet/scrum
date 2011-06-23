# -*- coding: utf-8 -*-

import datetime
from django import forms
from django.db import models
from django.forms import widgets

class CustomDateField(models.DateField):
    
    def formfield(self, **kwargs):
        defaults = {'form_class': forms.DateField, 'input_formats': ['%d/%m/%Y', '%Y-%m-%d']}
        defaults.update(kwargs)
        return super(models.DateField, self).formfield(**defaults)

class CustomTimeField(models.TimeField):
    
    def formfield(self, **kwargs):
        defaults = {'form_class': forms.TimeField, 'input_formats': ['%Hh%M', '%Hh', '%H:%M', '%H:%M:%S']}
        defaults.update(kwargs)
        return super(models.TimeField, self).formfield(**defaults)
