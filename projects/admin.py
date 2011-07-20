# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.admin.models import LogEntry, ContentType
from django.contrib.sessions.models import Session

from scrum.projects.models import Project, Feature, Note, Sprint, Task, Problem, Release, Document, NoteTime, TaskTime, History

class ProjectAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('titre', 'description', ),
            'classes': ('wide', ),
        }),
        ('Administration', {
            'fields': ('membres', 'date_creation', ),
            'classes': ('wide', 'collapse', ),
        }),
    )
    list_display = ('titre', 'date_creation', )
    list_filter = ('date_creation', )
    search_fields = ('title', 'description', )
    filter_horizontal = ('membres', )
    
    def queryset(self, request):
        if request.user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(membres__in = (request.user, )) 
    
class FeatureAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('titre', 'description', ),
            'classes': ('wide', ),
        }),
        ('Projet', {
            'fields': ('projet', ),
            'classes': ('wide', ),
        }),
        ('Status', {
            'fields': ('priorite', 'termine', ),
            'classes': ('wide', ),
        }),
        ('Confiance', {
            'fields': ('confiance_dev', 'confiance_sm', 'confiance_po', ),
            'classes': ('wide', ),
        }),
        ('Administration', {
            'fields': ('utilisateur', 'date_creation', ),
            'classes': ('wide', 'collapse', ),
        }),
    )
    list_display = ('titre', 'projet', 'priorite', 'termine', 'date_creation', 'utilisateur', )
    list_filter = ('date_creation', 'priorite', 'termine', )
    search_fields = ('projet', 'titre', 'description', )
    
    def queryset(self, request):
        if request.user.is_superuser:
            return Feature.objects.all()
        p = Project.objects.filter(membres__in = (request.user, ))
        return Feature.objects.filter(projet__in = p) 
    
    #def save_model(self, request, obj, form, change):
        #if not change:
            #obj.utilisateur = request.user
        #obj.save()  

class NoteAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('titre', 'description', ),
            'classes': ('wide', ),
        }),
        ('Projet', {
            'fields': ('feature', 'sprint', 'temps_realise', 'temps_estime', ),
            'classes': ('wide', ),
        }),
        ('Status', {
            'fields': ('type', 'priorite', 'etat', 'effort', ),
            'classes': ('wide', ),
        }),
        ('Confiance', {
            'fields': ('confiance_dev', 'confiance_sm', 'confiance_po', ),
            'classes': ('wide', ),
        }),
        ('Administration', {
            'fields': ('utilisateur', 'date_creation', ),
            'classes': ('wide', 'collapse', ),
        }),
    )
    list_display = ('titre', 'feature', 'sprint', 'priorite', 'etat', 'type', 'effort', 'temps_realise', 'temps_estime', 'date_creation', 'utilisateur', )
    list_filter = ('date_creation', 'priorite', 'type', 'etat', 'effort', 'sprint', )
    search_fields = ('feature', 'sprint', 'titre', 'description', )
    
    def queryset(self, request):
        if request.user.is_superuser:
            return Note.objects.all()
        p = Project.objects.filter(membres__in = (request.user, ))
        return Note.objects.filter(feature__projet__in = p)   
    
    #def save_model(self, request, obj, form, change):
        #if not change:
            #obj.utilisateur = request.user
        #obj.save()  

class SprintAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('titre', 'objectif', ),
            'classes': ('wide', ),
        }),
        ('Projet', {
            'fields': ('projet', 'date_debut', 'date_fin', 'effort', ),
            'classes': ('wide', ),
        }),
        ('Confiance', {
            'fields': ('confiance_dev', 'confiance_sm', 'confiance_po', ),
            'classes': ('wide', ),
        }),
        ('Administration', {
            'fields': ('utilisateur', 'date_creation', 'date_modification', ),
            'classes': ('wide', 'collapse', ),
        }),
    )
    list_display = ('titre', 'projet', 'date_debut', 'date_fin', 'date_creation', 'date_modification', 'utilisateur', )
    list_filter = ('date_creation', 'date_modification', 'date_debut', 'date_fin', )
    search_fields = ('projet', 'titre', 'but', )
    
    def queryset(self, request):
        if request.user.is_superuser:
            return Sprint.objects.all()
        p = Project.objects.filter(membres__in = (request.user, ))
        return Sprint.objects.filter(projet__in = p)  
    
    #def save_model(self, request, obj, form, change):
        #if not change:
            #obj.utilisateur = request.user
        #obj.save()  

class TaskAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('titre', 'description', ),
            'classes': ('wide', ),
        }),
        ('Projet', {
            'fields': ('sprint', 'temps_realise', 'temps_estime', ),
            'classes': ('wide', ),
        }),
        ('Status', {
            'fields': ('priorite', 'etat', 'effort', ),
            'classes': ('wide', ),
        }),
        ('Confiance', {
            'fields': ('confiance_dev', 'confiance_sm', 'confiance_po', ),
            'classes': ('wide', ),
        }),
        ('Administration', {
            'fields': ('utilisateur', 'date_creation', ),
            'classes': ('wide', 'collapse', ),
        }),
    )
    list_display = ('titre', 'sprint', 'priorite', 'etat', 'temps_realise', 'temps_estime', 'date_creation', 'utilisateur', )
    list_filter = ('date_creation', 'priorite', 'etat', 'temps_realise', 'temps_estime', )
    search_fields = ('sprint', 'titre', 'description', )

    def queryset(self, request):
        if request.user.is_superuser:
            return Task.objects.all()
        p = Project.objects.filter(membres__in = (request.user, ))
        return Task.objects.filter(sprint__projet__in = p) 
    
    #def save_model(self, request, obj, form, change):
        #if not change:
            #obj.utilisateur = request.user
        #obj.save()
    
class ProblemAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('titre', 'description',  ),
            'classes': ('wide', ),
        }),
        ('Projet', {
            'fields': ('projet', ),
            'classes': ('wide', ),
        }),
        ('Status', {
            'fields': ('priorite', 'resolu', ),
            'classes': ('wide', ),
        }),
        ('Confiance', {
            'fields': ('confiance_dev', 'confiance_sm', 'confiance_po', ),
            'classes': ('wide', ),
        }),
        ('Administration', {
            'fields': ('utilisateur', 'date_creation', ),
            'classes': ('wide', 'collapse', ),
        }),
    )
    list_display = ('titre', 'projet', 'priorite', 'resolu', 'date_creation', 'utilisateur', )
    list_filter = ('date_creation', 'priorite', 'resolu', )
    search_fields = ('projet', 'titre', 'description', )
    
    def queryset(self, request):
        if request.user.is_superuser:
            return Problem.objects.all()
        p = Project.objects.filter(membres__in = (request.user, ))
        return Problem.objects.filter(projet__in = p)    
    
    #def save_model(self, request, obj, form, change):
        #if not change:
            #obj.utilisateur = request.user
        #obj.save()

class ReleaseAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('note', 'status',  ),
            'classes': ('wide', ),
        }),
        ('Administration', {
            'fields': ('utilisateur', 'date_creation', ),
            'classes': ('wide', 'collapse', ),
        }),
    )
    list_display = ('note', 'status', 'date_creation', 'utilisateur', )
    list_filter = ('date_creation', 'status', )
    search_fields = ('note', )
    
    def queryset(self, request):
        if request.user.is_superuser:
            return Release.objects.all()
        p = Project.objects.filter(membres__in = (request.user, ))
        return Release.objects.filter(note__feature__projet__in = p)
    
    #def save_model(self, request, obj, form, change):
        #if not change:
            #obj.utilisateur = request.user
        #obj.save()

class DocumentAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('titre', 'fichier',  ),
            'classes': ('wide', ),
        }),
        ('Projet', {
            'fields': ('projet', ),
            'classes': ('wide', ),
        }),
        ('Administration', {
            'fields': ('utilisateur', 'date_creation', ),
            'classes': ('wide', 'collapse', ),
        }),
    )
    list_display = ('fichier', 'titre', 'projet', 'date_creation', 'utilisateur', )
    list_filter = ('date_creation', 'utilisateur', )
    search_fields = ('projet', 'titre', 'fichier', )
    
    def queryset(self, request):
        if request.user.is_superuser:
            return Document.objects.all()
        p = Project.objects.filter(membres__in = (request.user, ))
        return Document.objects.filter(projet__in = p)
    
    #def save_model(self, request, obj, form, change):
        #if not change:
            #obj.utilisateur = request.user
        #obj.save()

class NoteTimeAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('jour', 'temps', 'temps_fin', ),
            'classes': ('wide', ),
        }),
        ('Projet', {
            'fields': ('sprint', 'note', ),
            'classes': ('wide', ),
        }),
        ('Administration', {
            'fields': ('utilisateur', 'date_modification', ),
            'classes': ('wide', 'collapse', ),
        }),
    )
    list_display = ('date_modification', 'jour', 'temps', 'temps_fin', 'sprint', 'note', 'utilisateur', )
    list_filter = ('date_modification', )
    search_fields = ('sprint', 'note', )
    
    def queryset(self, request):
        if request.user.is_superuser:
            return NoteTime.objects.all()
        p = Project.objects.filter(membres__in = (request.user, ))
        return NoteTime.objects.filter(sprint__projet__in = p)    
    
    #def save_model(self, request, obj, form, change):
        #if not change:
            #obj.utilisateur = request.user
        #obj.save()

class TaskTimeAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('jour', 'temps', 'temps_fin', ),
            'classes': ('wide', ),
        }),
        ('Projet', {
            'fields': ('sprint', 'task', ),
            'classes': ('wide', ),
        }),
        ('Administration', {
            'fields': ('utilisateur', 'date_modification', ),
            'classes': ('wide', 'collapse', ),
        }),
    )
    list_display = ('date_modification', 'jour', 'temps', 'temps_fin', 'sprint', 'task', 'utilisateur', )
    list_filter = ('date_modification', )
    search_fields = ('sprint', 'task', )
    
    def queryset(self, request):
        if request.user.is_superuser:
            return TaskTime.objects.all()
        p = Project.objects.filter(membres__in = (request.user, ))
        return TaskTime.objects.filter(sprint__projet__in = p)      
    
    #def save_model(self, request, obj, form, change):
        #if not change:
            #obj.utilisateur = request.user
        #obj.save()

class HistoryAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('url', 'date_creation', ),
            'classes': ('wide', ),
        }),
        ('Administration', {
            'fields': ('utilisateur', ),
            'classes': ('wide', 'collapse', ),
        }),
    )
    list_display = ('url', 'date_creation', 'utilisateur', )
    list_filter = ('date_creation', 'utilisateur', )
    search_fields = ('url', )
    
admin.site.register(Project, ProjectAdmin)
admin.site.register(Feature, FeatureAdmin)
admin.site.register(Note, NoteAdmin)
admin.site.register(Sprint, SprintAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(Problem, ProblemAdmin)
admin.site.register(Release, ReleaseAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(NoteTime, NoteTimeAdmin)
admin.site.register(TaskTime, TaskTimeAdmin)
admin.site.register(History, HistoryAdmin)

#admin.site.register(LogEntry)
#admin.site.register(ContentType)
#admin.site.register(Session)