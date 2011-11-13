# -*- coding: utf-8 -*-

import unittest, datetime
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

from scrum import settings
from scrum.projects.models import UserProfile, Project, Feature, Note, Sprint, Task, Problem

class SimpleTest(TestCase):
    def setUp(self):
        User.objects.create_superuser('admin', 'admin@test.fr', 'admin')
        self.user = UserProfile.objects.get(user__username__exact = 'admin')
    
    def create_project(self):
        p = Project()
        p.titre = 'Un projet'
        p.save()
        p.membres.add(self.user)
        p.save()
        self.assertTrue(p.id)
        return p
    
    def create_feature(self, project):
        f = Feature()
        f.titre = 'Une feature'
        f.utilisateur = self.user
        f.projet = project
        f.save()
        self.assertTrue(f.id)
        return f
    
    def create_note(self, feature):
        n = Note()
        n.titre = 'Une note'
        n.utilisateur = self.user
        n.feature = feature
        n.effort = 0
        n.temps_realise = 0
        n.temps_estime = 0
        n.save()
        self.assertTrue(n.id)
        return n
    
    def create_sprint(self, project):
        s = Sprint()
        s.titre = 'Un sprint'
        s.utilisateur = self.user
        s.projet = project
        s.date_debut = datetime.date.today()
        s.date_fin = datetime.date.today() + datetime.timedelta(5)
        s.save()
        self.assertTrue(s.id)
        return s
    
    def create_task(self, sprint):
        t = Task()
        t.titre = 'Une tache'
        t.utilisateur = self.user
        t.sprint = sprint
        t.priorite = 0
        t.save()
        self.assertTrue(t.id)
        return t
    
    def create_problem(self, project):
        p = Problem()
        p.titre = 'Un probleme'
        p.utilisateur = self.user
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
        u = self.user
        response = self.client.post('/projects/new/', 
            {'titre': 'Un projet', 'utilisateur': u.id, })
        self.failUnlessEqual(response.status_code, 200)
    
    def test_get_project(self):
        self.test_login()
        p = self.create_project()
        response = self.client.get('/projects/%d/' % (p.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/project.html')
    
    # Feature
    
    def test_get_features(self):        
        self.test_login()
        p = self.create_project()
        response = self.client.get('/projects/%d/features/' % (p.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/features.html')

    def test_get_new_feature(self):        
        self.test_login()
        p = self.create_project()
        response = self.client.get('/projects/%d/features/new/' % (p.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/feature_new.html')
    
    def test_post_new_feature(self):
        self.test_login()
        u = self.user
        p = self.create_project()
        response = self.client.post('/projects/%d/features/new/' % (p.id, ), 
            {'titre': 'Une feature', 'priorite': 0, 'utilisateur': u.id, 'projet': p.id, })
        self.failUnlessEqual(response.status_code, 302)
    
    def test_get_feature(self):
        self.test_login()
        p = self.create_project()
        f = self.create_feature(p)
        response = self.client.get('/projects/%d/features/%d/' % (p.id, f.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/feature.html')
    
    def test_post_edit_feature(self):
        self.test_login()
        u = self.user
        p = self.create_project()
        f = self.create_feature(p)
        response = self.client.post('/projects/%d/features/' % (p.id, ), 
            {'id': f.id, 'termine': '', })
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/features.html')
        self.assertContains(response, 'Fonctionnalité modifiée avec succès !')

    # Note
    
    def test_get_notes(self):
        self.test_login()
        p = self.create_project()
        f = self.create_feature(p)
        response = self.client.get('/projects/%d/features/%d/notes/' % (p.id, f.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/notes.html')
    
    def test_get_new_note(self):
        self.test_login()
        p = self.create_project()
        f = self.create_feature(p)
        response = self.client.get('/projects/%d/features/%d/notes/new/' % (p.id, f.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/note_new.html')
    
    def test_post_new_note(self):
        self.test_login()
        u = self.user
        p = self.create_project()
        f = self.create_feature(p)
        response = self.client.post('/projects/%d/features/%d/notes/new/' % (p.id, f.id, ), 
            {'titre': 'Une note', 'type': 0, 'priorite': 0, 'etat': 0, 'effort': 0, 'temps_realise': 0, 'temps_estime': 0, 'utilisateur': u.id, 'feature': f.id, })
        self.failUnlessEqual(response.status_code, 302)
    
    def test_get_note(self):
        self.test_login()
        p = self.create_project()
        f = self.create_feature(p)
        n = self.create_note(f)
        response = self.client.get('/projects/%d/features/%d/notes/%d/' % (p.id, f.id, n.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/note.html')
    
    def test_post_edit_note(self):
        self.test_login()
        p = self.create_project()
        f = self.create_feature(p)
        n = self.create_note(f)
        response = self.client.post('/projects/%d/features/%d/notes/' % (p.id, f.id, ), 
            {'id': n.id, 'temps': '0', 'sprint': '', })
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/notes.html')
        self.assertContains(response, 'Note de backlog modifiée avec succès !')
    
    # Sprint
    
    def test_get_sprints(self):
        self.test_login()
        p = self.create_project()
        response = self.client.get('/projects/%d/sprints/' % (p.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/sprints.html')
    
    def test_get_new_sprint(self):
        self.test_login()
        p = self.create_project()
        response = self.client.get('/projects/%d/sprints/new/' % (p.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/sprint_new.html')
    
    def test_post_new_sprint(self):
        self.test_login()
        u = self.user
        p = self.create_project()
        response = self.client.post('/projects/%d/sprints/new/' % (p.id, ), 
            {'titre': 'Un sprint', 'date_debut': '2011-01-01', 'date_fin': '2011-01-05', 'utilisateur': u.id, 'projet': p.id, })
        self.failUnlessEqual(response.status_code, 302)
    
    def test_get_sprint(self):
        self.test_login()
        p = self.create_project()
        s = self.create_sprint(p)
        response = self.client.get('/projects/%d/sprints/%d/' % (p.id, s.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/sprint.html')
    
    # Task
    
    def test_get_tasks(self):
        self.test_login()
        p = self.create_project()
        s = self.create_sprint(p)
        response = self.client.get('/projects/%d/sprints/%d/tasks/' % (p.id, s.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/tasks.html')
    
    def test_get_new_task(self):
        self.test_login()
        p = self.create_project()
        s = self.create_sprint(p)
        response = self.client.get('/projects/%d/sprints/%d/tasks/new/' % (p.id, s.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/task_new.html')
    
    def test_post_new_task(self):
        self.test_login()
        u = self.user
        p = self.create_project()
        s = self.create_sprint(p)
        response = self.client.post('/projects/%d/sprints/%d/tasks/new/' % (p.id, s.id, ), 
            {'titre': 'Une tache', 'priorite': 0, 'etat': 0, 'temps_realise': 0, 'temps_estime': 0, 'utilisateur': u.id, 'sprint': s.id, })
        self.failUnlessEqual(response.status_code, 302)
    
    def test_get_task(self):
        self.test_login()
        p = self.create_project()
        s = self.create_sprint(p)
        t = self.create_task(s)
        response = self.client.get('/projects/%d/sprints/%d/tasks/%d/' % (p.id, s.id, t.id, ))
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/task.html')
    
    def test_post_edit_task(self):
        self.test_login()
        p = self.create_project()
        s = self.create_sprint(p)
        t = self.create_task(s)
        response = self.client.post('/projects/%d/sprints/%d/tasks/' % (p.id, s.id), 
            {'id': t.id, 'temps': '0', 'etat': '0', 'priorite': '0', })
        self.failUnlessEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'projects/tasks.html')
        self.assertContains(response, 'Tâche modifiée avec succès !')
