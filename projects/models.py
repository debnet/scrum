# -*- coding: utf-8 -*-

import datetime
from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.utils.translation import ugettext as _

from scrum import fields

PRIORITES = (
    ('0', _(u'Aucune')),
    ('1', _(u'Annulé')),
    ('2', _(u'Possible')),
    ('3', _(u'Souhaitable')),
    ('4', _(u'Indispensable')),
    ('5', _(u'À spécifier')),
)

ETATS = (
    ('0', _(u'Backlog')),
    ('1', _(u'À faire')),
    ('2', _(u'En cours')),
    ('3', _(u'Livré')),
    ('4', _(u'Terminé')),
)

TYPES = (
    ('0', _(u'User-story')),
    ('1', _(u'Feature')),
    ('2', _(u'Bug')),
    ('3', _(u'Spike')),
)

CONFIANCE = (
    ('0', _(u'Aucune')),
    ('1', _(u'Basse')),
    ('2', _(u'Moyenne')),
    ('3', _(u'Haute')),
)

STATUTS = (
    ('0', _(u'À livrer')),
    ('1', _(u'Livré')),
    ('2', _(u'Refusé')),
    ('3', _(u'Validé')),
)

EFFORTS = (
    (0,  u'0' ),
    (1,  u'1' ),
    (2,  u'2' ),
    (3,  u'3' ),
    (5,  u'5' ),
    (8,  u'8' ),
    (13, u'13'),
    (21, u'21'),
    (34, u'34'),
    (55, u'55'),
    (89, u'89'),
)

METEO = (
    ('1', _(u'Mauvais')),
    ('2', _(u'Mitigé')),
    ('3', _(u'Bon')),
)

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        profile, new = UserProfile.objects.get_or_create(user=instance)

class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    
    def __unicode__(self):
        if self.user.first_name and self.user.last_name:
            return u'%s %s' % (self.user.first_name, self.user.last_name, )
        elif self.user.first_name:
            return u'%s' % (self.user.first_name, )
        else:
            return u'%s' % (self.user.username, )
    
    class Meta:
        #proxy = True
        verbose_name = _(u'Utilisateur')
        verbose_name_plural = _(u'Utilisateurs')

class Project(models.Model):
    titre = models.CharField(_(u'Titre'), max_length=128, unique=True, help_text=_(u'Requis. Un titre représentant le projet.'))
    description = models.TextField(_(u'Description'), blank=True, null=True)
    membres = models.ManyToManyField(UserProfile, blank=True, null=True)
    
    date_creation = models.DateTimeField(_(u'Date de création'), default=datetime.datetime.now)
    
    def __unicode__(self):
        return u'%s' % (self.titre, )    
    
    class Meta:
        verbose_name = _(u'Projet')
        verbose_name_plural = _(u'Projets')
        ordering = ('titre', 'date_creation', )

class Feature(models.Model):
    projet = models.ForeignKey(Project, help_text=_(u'Requis. La fonctionnalité doit appartenir à un projet.'))
    titre = models.CharField(_(u'Titre'), max_length=128, help_text=_(u'Requis. Un titre pour identifier la fonctionnalité.'))
    description = models.TextField(_(u'Description'), blank=True, null=True)
    priorite = models.CharField(_(u'Priorité'), max_length=1, choices=PRIORITES, default='0', help_text=_(u'Priorité de développement de la fonctionnalité.'), db_index=True)
    termine = models.BooleanField(_(u'Terminé ?'), help_text=_(u'Précise si la fonctionnalité a été complétement terminée'))
    
    confiance_dev = models.CharField(_(u'Confiance Développeurs'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par l\'équipe de développeurs.'))
    confiance_sm = models.CharField(_(u'Confiance Scrum Master'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Scrum Master'))
    confiance_po = models.CharField(_(u'Confiance Product Owner'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Product Owner'))
    
    date_creation = models.DateTimeField(_(u'Date de création'), default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s - %s' % (self.projet.titre, self.titre, )
    
    class Meta:
        verbose_name = _(u'Fonctionnalité')
        verbose_name_plural = _(u'Fonctionnalités')
        ordering = ('projet', 'titre', '-priorite', 'date_creation', )
        unique_together = (('projet', 'titre'), )
    
class Sprint(models.Model):
    projet = models.ForeignKey(Project, help_text=_(u'Requis. Le sprint doit appartenir à un projet.'))
    titre = models.CharField(_(u'Titre'), max_length=128, help_text=_(u'Requis. Un titre pour identifier le sprint.'))
    objectif = models.TextField(_(u'Objectif'), blank=True, null=True)
    date_debut = fields.CustomDateField(_(u'Date de début'), default=datetime.date.today, help_text=_(u'Date à laquelle le sprint commence(ra).'), db_index=True)
    date_fin = fields.CustomDateField(_(u'Date de fin'), help_text=_(u'Date à laquelle le sprint finira. Normalement fixe une fois pour toutes.'), db_index=True)
    effort = models.PositiveSmallIntegerField(_(u'Effort estimé'), default=0, help_text=_(u'Effort estimé de l\'ensemble des notes du backlog à la création du sprint.'))
    
    confiance_dev = models.CharField(_(u'Confiance Développeurs'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par l\'équipe de développeurs.'))
    confiance_sm = models.CharField(_(u'Confiance Scrum Master'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Scrum Master'))
    confiance_po = models.CharField(_(u'Confiance Product Owner'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Product Owner')) 
    
    date_creation = models.DateTimeField(_(u'Date de création'), default=datetime.datetime.now)
    date_modification = models.DateTimeField(_(u'Date de modification'), default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s - %s' % (self.projet.titre, self.titre, )    
    
    class Meta:
        verbose_name = _(u'Sprint')
        verbose_name_plural = _(u'Sprints')
        ordering = ('projet', 'date_debut', 'titre', '-date_fin', 'date_creation', )
        unique_together = (('projet', 'titre'), )

class Note(models.Model):
    feature = models.ForeignKey(Feature, help_text=_(u'Requis. Une note doit appartenir à une fonctionnalité du backlog.'))
    sprint = models.ForeignKey(Sprint, blank=True, null=True, help_text=_(u'Définit le sprint dans laquelle la note est/sera traitée ou rien sinon.'))
    titre = models.CharField(_(u'Titre'), max_length=128, help_text=_(u'Requis. Un titre pour identifier la note.'))
    description = models.TextField(_(u'Description'), default=_(u'En tant que...\nje peux...\nafin de...'), blank=True, null=True, help_text=_(u'Une description de la réalisation, par défaut une user-story.'))
    type = models.CharField(_(u'Type'), max_length=1, choices=TYPES, default='0', help_text=_(u'User-story : description du point de vue utilisateur, à préconiser.<br />Feature : une fonctionnalité décrite côté fonctionnel, à éviter si possible.<br />Spike : Analyse sur une future réalisation dont le coût et l\'évaluation sont/seront traités pendant le sprint.'))
    priorite = models.CharField(_(u'Priorité'), max_length=1, choices=PRIORITES, default='0', help_text=_(u'Définit la priorité de réalisation de la note.'), db_index=True)
    etat = models.CharField(_(u'État'), max_length=1, choices=ETATS, default='0', help_text=_(u'Définit l\'état de progression de la note.'), db_index=True)
    effort = models.PositiveSmallIntegerField(_(u'Effort'), choices=EFFORTS, default='0', help_text=_(u'Valeur de l\'effort à déployer pour réaliser la tâche.'))
    temps_realise = models.IntegerField(_(u'Temps réalisé'), default=0, help_text=_(u'Quantité de temps déjà exécuté sur la réalisation. Evolutive avec le temps.'))
    temps_estime = models.IntegerField(_(u'Temps estimé'), default=0, help_text=_(u'Quantité de temps allouée à la réalisation. Normalement non modifiable.'))
    
    confiance_dev = models.CharField(_(u'Confiance Développeurs'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par l\'équipe de développeurs.'))
    confiance_sm = models.CharField(_(u'Confiance Scrum Master'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Scrum Master'))
    confiance_po = models.CharField(_(u'Confiance Product Owner'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Product Owner'))    
    
    date_creation = models.DateTimeField(_(u'Date de création'), default=datetime.datetime.now)
    date_modification = models.DateTimeField(_(u'Date de modification'), default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s - %s' % (self.feature.titre, self.titre, )
    
    class Meta:
        verbose_name = _(u'Note')
        verbose_name_plural = _(u'Notes')
        ordering = ('feature', 'titre', '-priorite', '-type', 'etat', 'date_creation', )
        unique_together = (('feature', 'titre'), )
    
class Task(models.Model):
    sprint = models.ForeignKey(Sprint, help_text=_(u'Requis. Une tâche doit appartenir à un sprint.'))
    titre = models.CharField(_(u'Titre'), max_length=128, help_text=_(u'Requis. Un titre pour identifier la tâche.'))
    description = models.TextField(_(u'Description'), blank=True, null=True)
    priorite = models.CharField(_(u'Priorité'), max_length=1, choices=PRIORITES, default='0', help_text=_(u'Définit la priorité de réalisation de la tâche.'), db_index=True)
    etat = models.CharField(_(u'État'), max_length=1, choices=ETATS, default='0', help_text=_(u'Définit l\'état de progression de la note.'), db_index=True)
    effort = models.PositiveSmallIntegerField(_(u'Effort'), choices=EFFORTS, default='0', help_text=_(u'Valeur de l\'effort à déployer pour réaliser la tâche.'))
    temps_realise = models.PositiveIntegerField(_(u'Temps réalisé'), default=0, help_text=_(u'Quantité de temps déjà exécuté sur la réalisation. Evolutive avec le temps.'))
    temps_estime = models.PositiveIntegerField(_(u'Temps estimé'), default=0, blank=True, null=True, help_text=_(u'Quantité de temps allouée à la tâche. Normalement non modifiable.'))
    
    confiance_dev = models.CharField(_(u'Confiance Développeurs'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par l\'équipe de développeurs.'))
    confiance_sm = models.CharField(_(u'Confiance Scrum Master'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Scrum Master'))
    confiance_po = models.CharField(_(u'Confiance Product Owner'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Product Owner'))    
    
    date_creation = models.DateTimeField(_(u'Date de création'), default=datetime.datetime.now)
    date_modification = models.DateTimeField(_(u'Date de modification'), default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)

    def __unicode__(self):
        return u'%s - %s' % (self.sprint.titre, self.titre, )
    
    class Meta:
        verbose_name = _(u'Tâche')
        verbose_name_plural = _(u'Tâches')
        ordering = ('sprint', 'titre', '-priorite', 'etat', 'date_creation', )
        unique_together = (('sprint', 'titre'), )
    
class Problem(models.Model):
    projet = models.ForeignKey(Project, help_text=_(u'Requis. Un problème doit appartenir à un projet.'))
    titre = models.CharField(_(u'Titre'), max_length=128, help_text=_(u'Requis. Un titre pour identifier le problème.'))
    description = models.TextField(_(u'Description'), blank=True, null=True)
    priorite = models.CharField(_(u'Priorité'), max_length=1, choices=PRIORITES, default='0', help_text=_(u'Définit la priorité d\'exécution du problème.'), db_index=True)
    effort = models.PositiveSmallIntegerField(_(u'Effort'), choices=EFFORTS, default='0', help_text=_(u'Valeur de l\'effort à déployer pour réaliser la tâche.'))
    resolu = models.BooleanField(_(u'Résolu ?'), help_text=_(u'Définit si le problème a été résolu ou non.'))
    
    confiance_dev = models.CharField(_(u'Confiance Développeurs'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par l\'équipe de développeurs.'))
    confiance_sm = models.CharField(_(u'Confiance Scrum Master'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Scrum Master'))
    confiance_po = models.CharField(_(u'Confiance Product Owner'), max_length=1, choices=CONFIANCE, default='0', help_text=_(u'Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Product Owner'))
    
    date_creation = models.DateTimeField(_(u'Date de création'), default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s' % (self.titre, )
    
    class Meta:
        verbose_name = _(u'Problème')
        verbose_name_plural = _(u'Problèmes')
        ordering = ('projet', 'titre', 'resolu', '-priorite', 'date_creation', )
        unique_together = (('projet', 'titre'), )

class Release(models.Model):
    note = models.ForeignKey(Note, help_text=_(u'Requis. Une livraison doit être lié à une note de backlog.'))
    statut = models.CharField(_(u'Statut'), max_length=1, choices=STATUTS, default='0', help_text=_(u'Définit le statut de livraison de la fonctionnalité.'), db_index=True)
    commentaire = models.CharField(_(u'Commentaire'), max_length=200, blank=True, null=True, help_text=_(u'Facultatif. Précise les raisons du changement de statut de la livraison.'))
    
    date_creation = models.DateTimeField(_(u'Date de création'), default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s' % (self.note.titre, )    
    
    class Meta:
        verbose_name = _(u'Livraison')
        verbose_name_plural = _(u'Livraisons')
        ordering = ('note', 'date_creation', )

class NoteTime(models.Model):
    sprint = models.ForeignKey(Sprint, help_text=_(u'Requis. Un temps de réalisation est lié à un sprint.'))
    note = models.ForeignKey(Note, help_text=_(u'Requis. Un temps de réalisation doit appartenir à une note de sprint.'))
    jour = fields.CustomDateField(_(u'Date'), help_text=_(u'La date à laquelle correspond la réalisation.'), db_index=True)
    temps = models.PositiveIntegerField(_(u'Temps réalisé'), default = 0, help_text=_(u'Quantité de temps exécuté sur la réalisation.'))
    temps_fin = models.IntegerField(_(u'Temps en excès'), default = 0, help_text=_(u'Quantité de temps en excès sur la réalisation.'))

    date_modification = models.DateTimeField(_(u'Date de modification'), blank=True, null=True)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s - %s' % (self.sprint.titre, self.note.titre, )
    
    class Meta:
        verbose_name = _(u'Temps de note')
        verbose_name_plural = _(u'Temps de note')
        ordering = ('note', 'jour', )
        unique_together = (('note', 'jour'), )

class TaskTime(models.Model):
    sprint = models.ForeignKey(Sprint, help_text=_(u'Requis. Un temps de réalisation est lié à un sprint.'))
    task = models.ForeignKey(Task, help_text=_(u'Requis. Un temps de réalisation doit appartenir à une tâche de sprint.'))
    jour = fields.CustomDateField(_(u'Date'), help_text=_(u'La date à laquelle correspond la réalisation.'), db_index=True)
    temps = models.PositiveIntegerField(_(u'Temps réalisé'), default = 0, help_text=_(u'Quantité de temps exécuté sur la réalisation.'))
    temps_fin = models.IntegerField(_(u'Temps en excès'), default = 0, help_text=_(u'Quantité de temps en excès sur la réalisation.'))
    
    date_modification = models.DateTimeField(_(u'Date de modification'), blank=True, null=True)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s - %s' % (self.sprint.titre, self.task.titre, )
    
    class Meta:
        verbose_name = _(u'Temps de tâche')
        verbose_name_plural = _(u'Temps de tâche')
        ordering = ('task', 'jour', )
        unique_together = (('task', 'jour'), )

class Meteo(models.Model):
    sprint = models.ForeignKey(Sprint, help_text='Requis. Une météo est liée à un sprint.')
    jour = fields.CustomDateField('Date', help_text='La date à laquelle correspond la météo.', db_index=True)
    utilisateur = models.ForeignKey(UserProfile, help_text='Requis. Une météo est liée à un utilisateur.')
    meteo_projet = models.CharField('Météo Projet', max_length=1, choices=METEO, default='0', help_text='Indique le niveau de satisfaction concernant le projet.')
    meteo_equipe = models.CharField('Météo Equipe', max_length=1, choices=METEO, default='0', help_text='Indique le niveau de satisfaction concernant l\'équipe.')
    meteo_avance = models.CharField('Météo Avancement', max_length=1, choices=METEO, default='0', help_text='Indique le niveau de satisfaction concernant l\'avancement.')    
    commentaire = models.CharField('Commentaire', max_length=200, blank=True, null=True, help_text='Facultatif. Permet de détailler plus précisément la journée.')
    
    def __unicode__(self):
        return u'%s - %s' % (self.sprint.titre, self.sprint.titre, )
    
    class Meta:
        verbose_name = _(u'Météo')
        verbose_name_plural = _(u'Météos')
        ordering = ('sprint', 'jour', )

class Poker(models.Model):
    note = models.ForeignKey(Note, help_text=_(u'Requis. Une estimation d\'effort est liée à une note.'))
    utilisateur = models.ForeignKey(UserProfile, help_text=_(u'Requis. Une estimation d\'effort est liée à un utilisateur.'))
    effort = models.PositiveSmallIntegerField('Effort', choices=EFFORTS, default='0', help_text=_(u'Valeur de l\'estimation d\'effort.'))
    
    def __unicode__(self):
        return u'%s' % (self.note.titre, )
    
    class Meta:
        verbose_name = _(u'Estimation')
        verbose_name_plural = _(u'Estimations')
        ordering = ('note', 'utilisateur', )

class Document(models.Model):
    projet = models.ForeignKey(Project, help_text=_(u'Requis. Un document est lié à un projet.'))
    titre = models.CharField(_(u'Titre'), max_length=256, blank=True, null=True, help_text=_(u'Facultatif. Une description du document.'))
    fichier = models.FileField(_(u'Fichier'), upload_to='files')
    
    date_creation = models.DateTimeField(_(u'Date de création'), default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)    
    
    def __unicode__(self):
        return u'%s - %s' % (self.projet.titre, self.titre, )
    
    class Meta:
        verbose_name = _(u'Document')
        verbose_name_plural = _(u'Documents')
        ordering = ('projet', 'titre', )

class History(models.Model):
    url = models.CharField(_(u'URL'), max_length=256)
    date_creation = models.DateTimeField(_(u'Date de création'), default=datetime.datetime.now, db_index=True)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    class Meta:
        verbose_name = _(u'Historique')
        verbose_name_plural = _(u'Historiques')
        ordering = ('-date_creation', )
        get_latest_by = 'date_creation'
