# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.admin.models import LogEntry, ContentType
from django.contrib.sessions.models import Session

from scrum.projects.models import Project, Feature, Note, Sprint, Task, Problem, Release, Document, NoteTime, TaskTime, Meteo, Poker, History

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
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['titre']
    
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
        ('Statut', {
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
    list_display = ('titre', 'projet', 'priorite', 'termine', )
    list_filter = ('date_creation', 'priorite', 'termine', )
    search_fields = ('projet__titre', 'titre', 'description', )
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['projet', 'titre']
    
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
        ('Statut', {
            'fields': ('type', 'priorite', 'etat', 'effort', ),
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
    list_display = ('titre', 'feature', 'sprint', 'priorite', 'etat', 'type', 'effort', 'temps_realise', 'temps_estime', )
    list_filter = ('date_creation', 'date_modification', 'priorite', 'type', 'etat', 'effort', )
    search_fields = ('feature__titre', 'sprint__titre', 'titre', 'description', )
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['feature', 'titre']
    
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
    list_display = ('titre', 'projet', 'date_debut', 'date_fin', )
    list_filter = ('date_creation', 'date_modification', 'date_debut', 'date_fin', )
    search_fields = ('projet__titre', 'titre', 'but', )
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['projet', 'titre']
    
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
        ('Statut', {
            'fields': ('priorite', 'etat', 'effort', ),
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
    list_display = ('titre', 'sprint', 'priorite', 'etat', 'temps_realise', 'temps_estime', )
    list_filter = ('date_creation', 'date_modification', 'priorite', 'etat', 'temps_realise', 'temps_estime', )
    search_fields = ('sprint__titre', 'sprint__projet__titre', 'titre', 'description', )
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['sprint', 'titre']

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
        ('Statut', {
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
    list_display = ('titre', 'projet', 'priorite', 'resolu', )
    list_filter = ('date_creation', 'priorite', 'resolu', )
    search_fields = ('projet__titre', 'titre', 'description', )
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['projet', 'titre']
    
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
            'fields': ('note', 'statut', 'commentaire',  ),
            'classes': ('wide', ),
        }),
        ('Administration', {
            'fields': ('utilisateur', 'date_creation', ),
            'classes': ('wide', 'collapse', ),
        }),
    )
    list_display = ('note', 'statut', 'date_creation', 'utilisateur', 'commentaire', )
    list_filter = ('date_creation', 'statut', 'utilisateur', )
    search_fields = ('note__titre', 'note__feature__titre', 'commentaire', )
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['note']
    
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
    list_filter = ('date_creation', )
    search_fields = ('projet__titre', 'titre', 'fichier', )
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['titre']
    
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
    list_display = ('jour', 'temps', 'temps_fin', 'sprint', 'note', 'utilisateur', )
    list_filter = ('date_modification', 'jour', 'utilisateur', )
    search_fields = ('sprint__titre', 'sprint__projet__titre', 'note__titre', )
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['sprint', 'note', 'jour']
    
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
    list_display = ('jour', 'temps', 'temps_fin', 'sprint', 'task', 'utilisateur', )
    list_filter = ('date_modification', 'jour', 'utilisateur', )
    search_fields = ('sprint__titre', 'sprint__projet__titre', 'task__titre', )
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['sprint', 'task', 'jour']
    
    def queryset(self, request):
        if request.user.is_superuser:
            return TaskTime.objects.all()
        p = Project.objects.filter(membres__in = (request.user, ))
        return TaskTime.objects.filter(sprint__projet__in = p)      
    
    #def save_model(self, request, obj, form, change):
        #if not change:
            #obj.utilisateur = request.user
        #obj.save()

class MeteoAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('sprint', 'jour', 'utilisateur', 'meteo_projet', 'meteo_equipe', 'meteo_avance', 'commentaire', ),
            'classes': ('wide', ),
        }),
    )
    list_display = ('sprint', 'jour', 'utilisateur', 'meteo_projet', 'meteo_equipe', 'meteo_avance', 'commentaire', )
    list_filter = ('jour', 'utilisateur', )
    search_fields = ('sprint__titre', 'sprint__projet__titre', 'commentaire', )
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['sprint', 'utilisateur', 'jour']
    
    def queryset(self, request):
        if request.user.is_superuser:
            return Meteo.objects.all()
        p = Project.objects.filter(membres__in = (request.user, ))
        return Meteo.objects.filter(sprint__projet__in = p)      
    
    #def save_model(self, request, obj, form, change):
        #if not change:
            #obj.utilisateur = request.user
        #obj.save()

class PokerAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informations', {
            'fields': ('note', 'utilisateur', 'effort' ),
            'classes': ('wide', ),
        }),
    )
    list_display = ('note', 'utilisateur', 'effort', )
    list_filter = ('effort', 'utilisateur', )
    search_fields = ('note__titre', 'note__feature__titre', )
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['note', 'utilisateur']
    
    def queryset(self, request):
        if request.user.is_superuser:
            return Poker.objects.all()
        p = Project.objects.filter(membres__in = (request.user, ))
        return Poker.objects.filter(note__feature__projet__in = p)      
    
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
    actions_on_top = False
    actions_on_bottom = True
    ordering = ['date_creation']
    
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
admin.site.register(Meteo, MeteoAdmin)
admin.site.register(Poker, PokerAdmin)
admin.site.register(History, HistoryAdmin)

#admin.site.register(LogEntry)
#admin.site.register(ContentType)
#admin.site.register(Session)