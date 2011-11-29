# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth.models import User
from django.forms.util import ErrorList

from scrum.projects.models import UserProfile, Project, Feature, Note, Sprint, Task, Problem, Document

class UserForm(forms.ModelForm):
    password = forms.CharField(max_length=100, widget=forms.PasswordInput)
    verify = forms.CharField(label='Verification', max_length=100, widget=forms.PasswordInput)
    
    def clean(self):
        cleaned_data = self.cleaned_data
        password = cleaned_data.get('password')
        verify = cleaned_data.get('verify')
        
        if password != verify:
            msg = u'Veuillez vérifier votre mot de passe.'
            self._errors["password"] = ErrorList([msg])
            self._errors["verify"] = ErrorList([msg])
            del cleaned_data['password']
        return cleaned_data
    
    class Meta:
        model = User
        exclude = ('password', 'last_login', 'date_joined', 'is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions', )

class ProjectForm(forms.ModelForm):
    membres = forms.ModelMultipleChoiceField(UserProfile.objects.all(), widget=forms.CheckboxSelectMultiple)
    
    class Meta:
        model = Project
        exclude = ('date_creation', )

class FeatureForm(forms.ModelForm):
    utilisateur = forms.ModelChoiceField(UserProfile.objects.all(), widget=forms.HiddenInput)
    projet = forms.ModelChoiceField(Project.objects.all(), widget=forms.HiddenInput)
    
    class Meta:
        model = Feature
        exclude = ('date_creation', 'etat', 'confiance_dev', 'confiance_sm', 'confiance_po', )

class NoteForm(forms.ModelForm):
    utilisateur = forms.ModelChoiceField(UserProfile.objects.all(), widget=forms.HiddenInput)
    feature = forms.ModelChoiceField(Feature.objects.all(), widget=forms.HiddenInput)
    sprint = forms.ModelChoiceField(Sprint.objects.all(), widget=forms.HiddenInput, required = False)
    
    class Meta:
        model = Note
        exclude = ('temps_realise', 'date_creation', 'confiance_dev', 'confiance_sm', 'confiance_po', )

class SprintForm(forms.ModelForm):
    utilisateur = forms.ModelChoiceField(UserProfile.objects.all(), widget=forms.HiddenInput)
    projet = forms.ModelChoiceField(Project.objects.all(), widget=forms.HiddenInput)
    effort = forms.IntegerField(widget=forms.HiddenInput)
    
    class Meta:
        model = Sprint
        exclude = ('date_creation', 'date_modification', 'confiance_dev', 'confiance_sm', 'confiance_po', )
        widgets = {
            'titre': forms.TextInput(attrs = {
                'readonly': True,
            }),
        }

class TaskForm(forms.ModelForm):
    utilisateur = forms.ModelChoiceField(UserProfile.objects.all(), widget=forms.HiddenInput)
    sprint = forms.ModelChoiceField(Sprint.objects.all(), widget=forms.HiddenInput)
    
    class Meta:
        model = Task
        exclude = ('temps_realise', 'etat', 'effort', 'date_creation', 'confiance_dev', 'confiance_sm', 'confiance_po', )

class ProblemForm(forms.ModelForm):
    utilisateur = forms.ModelChoiceField(UserProfile.objects.all(), widget=forms.HiddenInput)
    projet = forms.ModelChoiceField(Project.objects.all(), widget=forms.HiddenInput)
    
    class Meta:
        model = Problem
        exclude = ('date_creation', 'confiance_dev', 'confiance_sm', 'confiance_po', 'resolu', )

class DocumentForm(forms.ModelForm):
    utilisateur = forms.ModelChoiceField(UserProfile.objects.all(), widget=forms.HiddenInput)
    projet = forms.ModelChoiceField(Project.objects.all(), widget=forms.HiddenInput)
    
    class Meta:
        model = Document
        exclude = ('date_creation', )