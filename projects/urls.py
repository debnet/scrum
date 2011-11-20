# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *

urlpatterns = patterns('scrum.projects.views',
    (r'^$', 'projects'),
    (r'^(?P<project_id>\d+)/$', 'project'),
    (r'^(?P<project_id>\d+)/documents/$', 'documents'),
    (r'^(?P<project_id>\d+)/scrumwall/$', 'scrumwall'),
    (r'^(?P<project_id>\d+)/velocity/$', 'velocity'),
    (r'^(?P<project_id>\d+)/summary/$', 'summary'),
    (r'^(?P<project_id>\d+)/poker/$', 'poker'),
    (r'^(?P<project_id>\d+)/pareto/$', 'pareto'),
    (r'^(?P<project_id>\d+)/features/$', 'features'),
    (r'^(?P<project_id>\d+)/features/(?P<feature_id>\d+)/$', 'feature'),
    (r'^(?P<project_id>\d+)/features/(?P<feature_id>\d+)/notes/$', 'notes'),
    (r'^(?P<project_id>\d+)/features/(?P<feature_id>\d+)/notes/(?P<note_id>\d+)/$', 'note'),
    (r'^(?P<project_id>\d+)/sprints/$', 'sprints'),
    (r'^(?P<project_id>\d+)/sprints/(?P<sprint_id>\d+)/$', 'sprint'),
    (r'^(?P<project_id>\d+)/sprints/(?P<sprint_id>\d+)/burndown/$', 'burndown'),
    (r'^(?P<project_id>\d+)/sprints/(?P<sprint_id>\d+)/meteo/$', 'meteo'),
    (r'^(?P<project_id>\d+)/sprints/(?P<sprint_id>\d+)/notes/$', 'snotes'),
    (r'^(?P<project_id>\d+)/sprints/(?P<sprint_id>\d+)/notes/(?P<note_id>\d+)/$', 'snote'),
    (r'^(?P<project_id>\d+)/sprints/(?P<sprint_id>\d+)/tasks/$', 'tasks'),
    (r'^(?P<project_id>\d+)/sprints/(?P<sprint_id>\d+)/tasks/(?P<task_id>\d+)/$', 'task'),
    (r'^(?P<project_id>\d+)/sprints/(?P<sprint_id>\d+)/releases/$', 'releases'),
    (r'^(?P<project_id>\d+)/sprints/(?P<sprint_id>\d+)/releases/(?P<release_id>\d+)/$', 'release'),
    (r'^(?P<project_id>\d+)/problems/$', 'problems'),
    (r'^(?P<project_id>\d+)/problems/(?P<problem_id>\d+)/$', 'problem'),
    (r'^user/$', 'new_user'),
    (r'^new/$', 'new_project'),
    (r'^(?P<project_id>\d+)/features/new/$', 'new_feature'),
    (r'^(?P<project_id>\d+)/features/(?P<feature_id>\d+)/notes/new/$', 'new_note'),
    (r'^(?P<project_id>\d+)/sprints/new/$', 'new_sprint'),
    (r'^(?P<project_id>\d+)/sprints/(?P<sprint_id>\d+)/tasks/new/$', 'new_task'),
    (r'^(?P<project_id>\d+)/problems/new/$', 'new_problem'),
    (r'^(?P<project_id>\d+)/features/(?P<feature_id>\d+)/notes/(?P<note_id>\d+)/sprint/$', 'add_sprint'),
    (r'^logs/$', 'logs'),
    (r'^history/$', 'history'),
    (r'^archives/$', 'archives'),
)
