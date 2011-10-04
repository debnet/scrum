# -*- coding: utf-8 -*-

import datetime
from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver

from scrum import fields

PRIORITES = (
    ('0', u'Aucune'),
    ('1', u'Éliminé(e)'),
    ('2', u'Possible'),
    ('3', u'Souhaitable'),
    ('4', u'Indispensable'),
    ('5', u'Reporté(e)'),
)

ETATS = (
    ('0', u'À faire'),
    ('1', u'En cours'),
    ('2', u'Terminé'),
)

TYPES = (
    ('0', u'User-story'),
    ('1', u'Feature'),
    ('2', u'Bug'),
    ('3', u'Spike'),
)

CONFIANCE = (
    ('0', u'Aucune'),
    ('1', u'Basse'),
    ('2', u'Moyenne'),
    ('3', u'Haute'),
)

STATUT = (
    ('0', u'À livrer'),
    ('1', u'Livré'),
    ('2', u'Refusé'),
    ('3', u'Validé'),
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
    ('1', u'Mauvais'),
    ('2', u'Mitigé'),
    ('3', u'Bon'),
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
        verbose_name = u'Utilisateur'
        verbose_name_plural = u'Utilisateurs'

class Project(models.Model):
    titre = models.CharField('Titre', max_length=128, unique=True, help_text='Requis. Un titre représentant le projet.')
    description = models.TextField('Description', blank=True, null=True)
    membres = models.ManyToManyField(UserProfile, blank=True, null=True)
    
    date_creation = models.DateTimeField('Date de création', default=datetime.datetime.now)
    
    def __unicode__(self):
        return u'%s' % (self.titre, )    
    
    class Meta:
        verbose_name = u'Projet'
        verbose_name_plural = u'Projets'
        ordering = ('titre', 'date_creation', )

class Feature(models.Model):
    projet = models.ForeignKey(Project, help_text='Requis. La fonctionnalité doit appartenir à un projet.')
    titre = models.CharField('Titre', max_length=128, help_text='Requis. Un titre pour identifier la fonctionnalité.')
    description = models.TextField('Description', blank=True, null=True)
    priorite = models.CharField('Priorité', max_length=1, choices=PRIORITES, default='0', help_text='Priorité de développement de la fonctionnalité.', db_index=True)
    termine = models.BooleanField('Terminé ?', help_text='Précise si la fonctionnalité a été complétement terminée')
    
    confiance_dev = models.CharField('Confiance Développeurs', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par l\'équipe de développeurs.')
    confiance_sm = models.CharField('Confiance Scrum Master', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Scrum Master');
    confiance_po = models.CharField('Confiance Product Owner', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Product Owner');
    
    date_creation = models.DateTimeField('Date de création', default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s' % (self.titre, )
    
    class Meta:
        verbose_name = u'Feature'
        verbose_name_plural = u'Features'
        ordering = ('titre', 'projet', '-priorite', 'date_creation', )
        unique_together = (('projet', 'titre'), )
    
class Sprint(models.Model):
    projet = models.ForeignKey(Project, help_text='Requis. Le sprint doit appartenir à un projet.')
    titre = models.CharField('Titre', max_length=128, help_text='Requis. Un titre pour identifier le sprint.')
    objectif = models.TextField('Objectif', blank=True, null=True)
    date_debut = fields.CustomDateField('Date début', default=datetime.date.today, help_text='Date à laquelle le sprint commence(ra).', db_index=True)
    date_fin = fields.CustomDateField('Date fin', help_text='Date à laquelle le sprint finira. Normalement fixe une fois pour toute.', db_index=True)
    effort = models.PositiveSmallIntegerField('Effort estimé', default=0, help_text='Effort estimé de l\'ensemble des notes du backlog à la création du sprint.')
    
    confiance_dev = models.CharField('Confiance Développeurs', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par l\'équipe de développeurs.')
    confiance_sm = models.CharField('Confiance Scrum Master', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Scrum Master');
    confiance_po = models.CharField('Confiance Product Owner', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Product Owner');    
    
    date_creation = models.DateTimeField('Date de création', default=datetime.datetime.now)
    date_modification = models.DateTimeField('Date de modification', default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s' % (self.titre, )    
    
    class Meta:
        verbose_name = u'Sprint'
        verbose_name_plural = u'Sprints'
        ordering = ('date_debut', 'titre', 'projet', '-date_fin', 'date_creation', )
        unique_together = (('projet', 'titre'), )

class Note(models.Model):
    feature = models.ForeignKey(Feature, help_text='Requis. Une note doit appartenir à une fonctionnalité du backlog.')
    sprint = models.ForeignKey(Sprint, blank=True, null=True, help_text='Définit le sprint dans laquelle la note est/sera traitée ou rien sinon.')
    titre = models.CharField('Titre', max_length=128, help_text='Requis. Un titre pour identifier la note.')
    description = models.TextField('Description', default='En tant que...\nje peux...\nafin de...', blank=True, null=True, help_text='Une description de la réalisation, par défaut une user-story.')
    type = models.CharField('Type', max_length=1, choices=TYPES, default='0', help_text='User-story : description du point de vue utilisateur.<br />Spike : Analyse sur une future réalisation dont le coût et l\'évaluation sont/seront traités pendant le sprint.<br />Feature : une fonctionnalité décrite côté fonctionnel.')
    priorite = models.CharField('Priorité', max_length=1, choices=PRIORITES, default='0', help_text='Définit la priorité d\'exécution de la note.', db_index=True)
    etat = models.CharField('État', max_length=1, choices=ETATS, default='0', help_text='Définit le statut d\'exécution de la note.', db_index=True)
    effort = models.PositiveSmallIntegerField('Effort', choices=EFFORTS, default='0', help_text='Valeur de l\'effort à déployer pour réaliser la tâche.')
    temps_realise = models.IntegerField('Temps réalisé', default=0, help_text='Quantité de temps déjà exécuté sur la réalisation. Evolutive avec le temps.')
    temps_estime = models.IntegerField('Temps estimé', default=0, help_text='Quantité de temps allouée à la réalisation. Normalement non modifiable.')
    
    confiance_dev = models.CharField('Confiance Développeurs', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par l\'équipe de développeurs.')
    confiance_sm = models.CharField('Confiance Scrum Master', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Scrum Master');
    confiance_po = models.CharField('Confiance Product Owner', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Product Owner');    
    
    date_creation = models.DateTimeField('Date de création', default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s' % (self.titre, )
    
    class Meta:
        verbose_name = u'Note'
        verbose_name_plural = u'Notes'
        ordering = ('titre', 'feature', '-priorite', '-type', 'etat', 'date_creation', )
        unique_together = (('feature', 'titre'), )
    
class Task(models.Model):
    sprint = models.ForeignKey(Sprint, help_text='Requis. Une tâche doit appartenir à un sprint.')
    titre = models.CharField('Titre', max_length=128, help_text='Requis. Un titre pour identifier la tâche.')
    description = models.TextField('Description', blank=True, null=True)
    priorite = models.CharField('Priorité', max_length=1, choices=PRIORITES, default='0', help_text='Définit la priorité d\'exécution de la tâche.', db_index=True)
    etat = models.CharField('État', max_length=1, choices=ETATS, default='0', help_text='Définit le statut d\'exécution de la note.', db_index=True)
    effort = models.PositiveSmallIntegerField('Effort', choices=EFFORTS, default='0', help_text='Valeur de l\'effort à déployer pour réaliser la tâche.')
    temps_realise = models.PositiveIntegerField('Temps réalisé', default=0, help_text='Quantité de temps déjà exécuté sur la réalisation. Evolutive avec le temps.')
    temps_estime = models.PositiveIntegerField('Temps estimé', default=0, blank=True, null=True, help_text='Quantité de temps allouée à la tâche. Normalement non modifiable.')
    
    confiance_dev = models.CharField('Confiance Développeurs', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par l\'équipe de développeurs.')
    confiance_sm = models.CharField('Confiance Scrum Master', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Scrum Master');
    confiance_po = models.CharField('Confiance Product Owner', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Product Owner');    
    
    date_creation = models.DateTimeField('Date de création', default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)

    def __unicode__(self):
        return u'%s' % (self.titre, )
    
    class Meta:
        verbose_name = u'Tâche'
        verbose_name_plural = u'Tâches'
        ordering = ('titre', 'sprint', '-priorite', 'etat', 'date_creation', )
        unique_together = (('sprint', 'titre'), )
    
class Problem(models.Model):
    projet = models.ForeignKey(Project, help_text='Requis. Un problème doit appartenir à un projet.')
    titre = models.CharField('Titre', max_length=128, help_text='Requis. Un titre pour identifier le problème.')
    description = models.TextField('Description', blank=True, null=True)
    priorite = models.CharField('Priorité', max_length=1, choices=PRIORITES, default='0', help_text='Définit la priorité d\'exécution du problème.', db_index=True)
    effort = models.PositiveSmallIntegerField('Effort', choices=EFFORTS, default='0', help_text='Valeur de l\'effort à déployer pour réaliser la tâche.')
    resolu = models.BooleanField('Résolu ?', help_text='Définit si le problème a été résolu ou non.')
    
    confiance_dev = models.CharField('Confiance Développeurs', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par l\'équipe de développeurs.')
    confiance_sm = models.CharField('Confiance Scrum Master', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Scrum Master');
    confiance_po = models.CharField('Confiance Product Owner', max_length=1, choices=CONFIANCE, default='0', help_text='Indique le niveau de confiance de la réalisabilité de la fonctionnalité par le Product Owner');    
    
    date_creation = models.DateTimeField('Date de création', default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s' % (self.titre, )
    
    class Meta:
        verbose_name = u'Problème'
        verbose_name_plural = u'Problèmes'
        ordering = ('titre', 'projet', 'resolu', '-priorite', 'date_creation', )
        unique_together = (('projet', 'titre'), )

class Release(models.Model):
    note = models.ForeignKey(Note, help_text='Requis. Une livraison doit être lié à une note de backlog.')
    statut = models.CharField('Statut', max_length=1, choices=STATUT, default='0', help_text='Définit le statut de livraison de la fonctionnalité.', db_index=True)
    commentaire = models.CharField('Commentaire', max_length=200, blank=True, null=True, help_text='Facultatif. Précise les raisons du changement de statut de la livraison.')
    
    date_creation = models.DateTimeField('Date de création', default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s' % (self.note.titre, )    
    
    class Meta:
        verbose_name = u'Livraison'
        verbose_name_plural = u'Livraisons'
        ordering = ('note', 'date_creation', )

class NoteTime(models.Model):
    sprint = models.ForeignKey(Sprint, help_text='Requis. Un temps de réalisation est lié à un sprint.')
    note = models.ForeignKey(Note, help_text='Requis. Un temps de réalisation doit appartenir à une note de sprint.')
    jour = fields.CustomDateField('Date', help_text='La date à laquelle correspond la réalisation.', db_index=True)
    temps = models.PositiveIntegerField('Temps réalisé', default = 0, help_text='Quantité de temps exécuté sur la réalisation.')
    temps_fin = models.IntegerField('Temps en excès', default = 0, help_text='Quantité de temps en excès sur la réalisation.')

    date_modification = models.DateTimeField('Date de modification', blank=True, null=True)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s' % (self.note.titre, )
    
    class Meta:
        verbose_name = u'Temps de note'
        verbose_name_plural = u'Temps de note'
        ordering = ('note', 'jour', )
        unique_together = (('note', 'jour'), )

class TaskTime(models.Model):
    sprint = models.ForeignKey(Sprint, help_text='Requis. Un temps de réalisation est lié à un sprint.')
    task = models.ForeignKey(Task, help_text='Requis. Un temps de réalisation doit appartenir à une tâche de sprint.')
    jour = fields.CustomDateField('Date', help_text='La date à laquelle correspond la réalisation.', db_index=True)
    temps = models.PositiveIntegerField('Temps réalisé', default = 0, help_text='Quantité de temps exécuté sur la réalisation.')
    temps_fin = models.IntegerField('Temps en excès', default = 0, help_text='Quantité de temps en excès sur la réalisation.')
    
    date_modification = models.DateTimeField('Date de modification', blank=True, null=True)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    def __unicode__(self):
        return u'%s' % (self.task.titre, )
    
    class Meta:
        verbose_name = u'Temps de tâche'
        verbose_name_plural = u'Temps de tâche'
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
        return u'%s' % (self.sprint.titre, )
    
    class Meta:
        verbose_name = u'Météo'
        verbose_name_plural = u'Météos'
        ordering = ('sprint', 'jour', )

class Poker(models.Model):
    note = models.ForeignKey(Note, help_text='Requis. Une estimation d\'effort est liée à une note.')
    utilisateur = models.ForeignKey(UserProfile, help_text='Requis. Une estimation d\'effort est liée à un utilisateur.')
    effort = models.PositiveSmallIntegerField('Effort', choices=EFFORTS, default='0', help_text='Valeur de l\'estimation d\'effort.')
    
    def __unicode__(self):
        return u'%s' % (self.note.titre, )
    
    class Meta:
        verbose_name = u'Estimation'
        verbose_name_plural = u'Estimations'
        ordering = ('note', 'utilisateur', )

class Document(models.Model):
    projet = models.ForeignKey(Project, help_text='Requis. Un document est rataché à un projet.')
    titre = models.CharField('Titre', max_length=256, blank=True, null=True, help_text='Facultatif. Une description du document.')
    fichier = models.FileField('Fichier', upload_to='files')
    
    date_creation = models.DateTimeField('Date de création', default=datetime.datetime.now)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)    
    
    def __unicode__(self):
        return u'%s' % (self.titre, )
    
    class Meta:
        verbose_name = u'Document'
        verbose_name_plural = u'Documents'
        ordering = ('projet', 'titre', )

class History(models.Model):
    url = models.CharField('URL', max_length=256)
    date_creation = models.DateTimeField('Date de création', default=datetime.datetime.now, db_index=True)
    utilisateur = models.ForeignKey(UserProfile, blank=True, null=True)
    
    class Meta:
        verbose_name = u'Historique'
        verbose_name_plural = u'Historiques'
        ordering = ('-date_creation', )
        get_latest_by = 'date_creation'
