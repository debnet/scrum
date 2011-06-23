# -*- coding: utf-8 -*-

import unittest, datetime
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

from scrum import settings
from scrum.projects.models import UserProfile, Project, Feature, Note, Sprint, Task, Problem

class SimpleTest(TestCase):
    def setUp(self):
        UserProfile.objects.create_superuser('admin', 'admin@test.fr', 'admin')
    
    def create_project(self):
        p = Project()
        p.titre = 'Un projet'
        p.save()
        p.membres.add(UserProfile.objects.get(pk = 1))
        p.save()
        self.assertTrue(p.id)
        return p
    
    def create_feature(self, project):
        f = Feature()
        f.titre = 'Une feature'
        f.utilisateur = UserProfile.objects.get(pk = 1)
        f.projet = project
        f.save()
        self.assertTrue(f.id)
        return f
    
    def create_note(self, feature):
        n = Note()
        n.titre = 'Une note'
        n.utilisateur = UserProfile.objects.get(pk = 1)
        n.feature = feature
        n.temps_realise = 0
        n.temps_estime = 0
        n.save()
        self.assertTrue(n.id)
        return n
    
    def create_sprint(self, project):
        s = Sprint()
        s.titre = 'Un sprint'
        s.utilisateur = UserProfile.objects.get(pk = 1)
        s.projet = project
        s.date_debut = datetime.date.today()
        s.date_fin = datetime.date.today() + datetime.timedelta(5)
        s.save()
        self.assertTrue(s.id)
        return s
    
    def create_task(self, sprint):
        t = Task()
        t.titre = 'Une tache'
        t.utilisateur = UserProfile.objects.get(pk = 1)
        t.sprint = sprint
        t.priorite = 0
        t.save()
        self.assertTrue(t.id)
        return t
    
    def create_problem(self, project):
        p = Problem()
        p.titre = 'Un probleme'
        p.utilisateur = UserProfile.objects.get(pk = 1)
        p.projet = project
        p.priorite = 0
        p.save()
        self.assertTrue(p.id)
        return p
    
    def test_login(self):
        is_authentified = self.client.login(username='admin', password='admin')
        self.assertTrue(is_authentified)
    
    # Project
    
    def test_get_projects(self):
        self.test_login()
        response = self.client.get('/projects/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/projects.html')
    
    def test_get_new_project(self):
        self.test_login()
        response = self.client.get('/projects/new/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/project_new.html')       
    
    def test_post_new_project(self):
        self.test_login()
        u = UserProfile.objects.get(pk = 1)
        response = self.client.post('/projects/new/', 
            {'titre': 'Un projet', 'utilisateur': u.id, })
        self.failUnlessEqual(response.status_code, 200)
    
    def test_get_project(self):
        self.test_login()
        self.create_project()
        response = self.client.get('/projects/1/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/project.html')
    
    # Feature
    
    def test_get_features(self):        
        self.test_login()
        self.create_project()
        response = self.client.get('/projects/1/features/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/features.html')

    def test_get_new_feature(self):        
        self.test_login()
        self.create_project()
        response = self.client.get('/projects/1/features/new/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/feature_new.html')
    
    def test_post_new_feature(self):
        self.test_login()
        u = UserProfile.objects.get(pk = 1)
        p = self.create_project()
        response = self.client.post('/projects/1/features/new/', 
            {'titre': 'Une feature', 'priorite': 0, 'utilisateur': u.id, 'projet': p.id, })
        self.failUnlessEqual(response.status_code, 302)
    
    def test_get_feature(self):
        self.test_login()
        p = self.create_project()
        f = self.create_feature(p)
        response = self.client.get('/projects/1/features/1/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/feature.html')
    
    def test_post_edit_feature(self):
        self.test_login()
        u = UserProfile.objects.get(pk = 1)
        p = self.create_project()
        f = self.create_feature(p)
        response = self.client.post('/projects/1/features/', {'id': 1, 'termine': '', })
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/features.html')
        self.assertContains(response, 'Fonctionnalité modifiée avec succès !')

    # Note
    
    def test_get_notes(self):
        self.test_login()
        p = self.create_project()
        f = self.create_feature(p)
        response = self.client.get('/projects/1/features/1/notes/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/notes.html')
    
    def test_get_new_note(self):
        self.test_login()
        p = self.create_project()
        f = self.create_feature(p)
        response = self.client.get('/projects/1/features/1/notes/new/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/note_new.html')
    
    def test_post_new_note(self):
        self.test_login()
        u = UserProfile.objects.get(pk = 1)
        p = self.create_project()
        f = self.create_feature(p)
        response = self.client.post('/projects/1/features/1/notes/new/', 
            {'titre': 'Une note', 'type': 0, 'priorite': 0, 'etat': 0, 'temps_realise': 0, 'temps_estime': 0, 'utilisateur': u.id, 'feature': f.id, })
        self.failUnlessEqual(response.status_code, 302)
    
    def test_get_note(self):
        self.test_login()
        p = self.create_project()
        f = self.create_feature(p)
        n = self.create_note(f)
        response = self.client.get('/projects/1/features/1/notes/1/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/note.html')
    
    def test_post_edit_note(self):
        self.test_login()
        p = self.create_project()
        f = self.create_feature(p)
        n = self.create_note(f)
        response = self.client.post('/projects/1/features/1/notes/', {'id': 1, 'temps': '0', 'sprint': '', })
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/notes.html')
        self.assertContains(response, 'Note de backlog modifiée avec succès !')
    
    # Sprint
    
    def test_get_sprints(self):
        self.test_login()
        p = self.create_project()
        response = self.client.get('/projects/1/sprints/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/sprints.html')
    
    def test_get_new_sprint(self):
        self.test_login()
        p = self.create_project()
        response = self.client.get('/projects/1/sprints/new/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/sprint_new.html')
    
    def test_post_new_sprint(self):
        self.test_login()
        u = UserProfile.objects.get(pk = 1)
        p = self.create_project()
        response = self.client.post('/projects/1/sprints/new/', 
            {'titre': 'Un sprint', 'date_debut': '2009-01-01', 'date_fin': '2009-01-05', 'utilisateur': u.id, 'projet': p.id, })
        self.failUnlessEqual(response.status_code, 302)
    
    def test_get_sprint(self):
        self.test_login()
        p = self.create_project()
        s = self.create_sprint(p)
        response = self.client.get('/projects/1/sprints/1/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/sprint.html')
    
    # Task
    
    def test_get_tasks(self):
        self.test_login()
        p = self.create_project()
        s = self.create_sprint(p)
        response = self.client.get('/projects/1/sprints/1/tasks/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/tasks.html')
    
    def test_get_new_task(self):
        self.test_login()
        p = self.create_project()
        s = self.create_sprint(p)
        response = self.client.get('/projects/1/sprints/1/tasks/new/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/task_new.html')
    
    def test_post_new_task(self):
        self.test_login()
        u = UserProfile.objects.get(pk = 1)
        p = self.create_project()
        s = self.create_sprint(p)
        response = self.client.post('/projects/1/sprints/1/tasks/new/', 
            {'titre': 'Une tache', 'priorite': 0, 'etat': 0, 'temps_realise': 0, 'temps_estime': 0, 'utilisateur': u.id, 'sprint': s.id, })
        self.failUnlessEqual(response.status_code, 302)
    
    def test_get_task(self):
        self.test_login()
        p = self.create_project()
        s = self.create_sprint(p)
        t = self.create_task(s)
        response = self.client.get('/projects/1/sprints/1/tasks/1/')
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/task.html')
    
    def test_post_edit_task(self):
        self.test_login()
        p = self.create_project()
        s = self.create_sprint(p)
        t = self.create_task(s)
        response = self.client.post('/projects/1/sprints/1/tasks/', {'id': 1, 'temps': '0', 'etat': '0', 'priorite': '0', })
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/tasks.html')
        self.assertContains(response, 'Tâche modifiée avec succès !')
