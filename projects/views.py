# -*- coding: utf-8 -*-

import os
import time
import codecs
import datetime
from xml.dom.minidom import parse

import logging
logging.basicConfig (
    level = logging.DEBUG, 
    format = '%(asctime)s %(levelname)s %(message)s', 
)

from django.db.models import Count, Sum, Avg
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.models import LogEntry, ContentType
from django.contrib.auth.models import User
from django.template import RequestContext

from scrum import settings
from scrum.projects.models import UserProfile, Project, Feature, Note, Sprint, Task, Problem, Release, Document, NoteTime, TaskTime, History
from scrum.projects.models import ETATS, PRIORITES, STATUS
from scrum.projects.forms import UserForm, ProjectForm, FeatureForm, NoteForm, SprintForm, TaskForm, ProblemForm, DocumentForm

NOT_MEMBER_MSG = u'Accès refusé : l\'utilisateur n\'est pas membre du projet !'
NOTES_PAR_LIGNE = 5

root = settings.DEFAULT_DIR
home = settings.DEFAULT_HOME
theme = settings.MEDIA_URL

# ------------------------------------------------
def get_nb_notes(request):
    if request.method == 'POST' and request.POST.__contains__('nb_notes'):
        request.session['nb_notes'] = request.POST['nb_notes']
    if request.session.__contains__('nb_notes'):
        return int(request.session['nb_notes'])
    else:
        return NOTES_PAR_LIGNE

# ------------------------------------------------
def get_holidays(year):
    holidays = list()
    if (os.path.exists(root + str(year) + '.xml')):
        dom = parse(root + str(year) + '.xml')
        for node in dom.getElementsByTagName('day'):
            day = time.strptime(node.firstChild.nodeValue, "%Y-%m-%d")
            holidays.append(datetime.date(day[0], day[1], day[2]))
    return holidays

# ------------------------------------------------
def create_note_days(sprint, note):
    holidays = get_holidays(sprint.date_debut.year)
    d = sprint.date_debut
    first = True
    while d <= sprint.date_fin:
        if d.strftime('%w') not in ('0', '6', ) and d not in holidays:
            time = NoteTime()
            time.sprint = sprint
            time.note = note
            time.jour = d
            time.temps = 0
            if first:
                time.temps_fin = note.temps_realise
                first = False
            time.save()
        d += datetime.timedelta(1)

# ------------------------------------------------
def create_task_days(sprint, task):
    holidays = get_holidays(sprint.date_debut.year)
    d = sprint.date_debut
    while d <= sprint.date_fin:
        if d.strftime('%w') not in ('0', '6', ) and d not in holidays:
            time = TaskTime()
            time.sprint = sprint
            time.task = task
            time.jour = d
            time.temps = 0
            time.save()
        d += datetime.timedelta(1)

# ------------------------------------------------
def add_log(user, model_name, model, flag, message = u''):
    l = LogEntry()
    l.user = user.user
    l.change_message = message
    l.content_type = ContentType.objects.get(app_label = 'projects', model = model_name)
    l.object_id = model.id
    l.object_repr = model
    l.action_flag = flag
    l.save()

# ------------------------------------------------
def add_history(user, url):
    try:
        h = History.objects.latest()
        if h.utilisateur == user and h.url == url:
            pass
        else:
            h = History()
            h.utilisateur = user
            h.url = url
            h.save()
    except Exception:
        h = History()
        h.utilisateur = user
        h.url = url
        h.save()

# ------------------------------------------------
def write_logs():
    file = False
    date = datetime.date.today()
    history = History.objects.filter(date_creation__lt = datetime.date.today() - datetime.timedelta(settings.ARCHIVE_DAYS)).order_by('date_creation');
    for h in history:
        current = h.date_creation.date()
        path1 = root + 'logs' + os.sep + 'urls-' + current.strftime('%Y%m%d') + '.html'
        path2 = root + 'logs' + os.sep + 'urls-' + date.strftime('%Y%m%d') + '.html'
        if date != current and os.path.exists(path2):
            file = codecs.open(path2, mode='a', encoding='utf-8')
            file.write(u'</tbody></table></body></html>')
            file.close()
        if not os.path.exists(path1):
            file = codecs.open(path1, mode='w', encoding='utf-8')
            file.write(u'<html><head><meta http-equiv="content-type" content="text/html; charset=utf-8" /><title>Historiques de navigation (%s)</title><style>* { font-family: "Verdana"; } th { text-align: left; }</style></head><body><h1>Historiques de navigation (%s)</h1><br />' % (current.strftime('%d/%m/%Y'), current.strftime('%d/%m/%Y'), ));
            file.write(u'<table><thead><tr><th width="100">Heure</th><th width="400">Utilisateur</th><th>URL</th></tr></thead><tbody>')
        else:
            file = codecs.open(path1, mode='a', encoding='utf-8')
        file.write(u'<tr><td>%s</td><td>%s %s (%s)</td><td><a href="http://%s">%s</a></td></tr>' 
                   % (h.date_creation.strftime('%H:%m:%S'), h.utilisateur.user.first_name, h.utilisateur.user.last_name, h.utilisateur.user.username, settings.DEFAULT_URL + h.url, h.url, ))
        file.close()
        h.delete()
        date = current
    file = False
    date = datetime.date.today()
    actions = ['', 'Ajout', 'Modification', 'Suppression']
    logs = LogEntry.objects.filter(action_time__lt = datetime.date.today() - datetime.timedelta(7)).order_by('action_time')
    for l in logs:
        current = l.action_time.date()
        path1 = root + 'logs' + os.sep + 'logs-' + l.action_time.strftime('%Y%m%d') + '.html'
        path2 = root + 'logs' + os.sep + 'logs-' + date.strftime('%Y%m%d') + '.html'
        if date != current and os.path.exists(path2):
            file = codecs.open(path2, mode='a', encoding='utf-8')
            file.write(u'</tbody></table></body></html>')
            file.close()
        if not os.path.exists(path1):
            file = codecs.open(path1, mode='w', encoding='utf-8')
            file.write(u'<html><head><meta http-equiv="content-type" content="text/html; charset=utf-8" /><title>Historiques de gestion (%s)</title><style>* { font-family: "Verdana"; } th { text-align: left; }</style></head><body><h1>Historiques de gestion (%s)</h1><br />' % (current.strftime('%d/%m/%Y'), current.strftime('%d/%m/%Y'), ))
            file.write(u'<table><thead><tr><th width="100">Heure</th><th width="400">Utilisateur</th><th width="400">Objet</th><th width="150">Type</th><th width="150">Action</th><th width="500">Message</th></tr></thead><tbody>')
        else :
            file = codecs.open(path1, mode='a', encoding='utf-8')
        file.write(u'<tr><td>%s</td><td>%s %s (%s)</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' 
            % (l.action_time.strftime('%H:%m:%S'), l.user.first_name, l.user.last_name, l.user.username, l.object_repr, l.content_type, actions[l.action_flag], l.change_message, ))    
        file.close()
        l.delete()
        date = current

# ------------------------------------------------
def list_users(membres):
    pass

# ------------------------------------------------
def list_projects(nb_notes = NOTES_PAR_LIGNE):
    tmp = Project.objects.all()
    projects = list()
    projects.append(list())
    i = 1
    j = 0
    for t in tmp:
        t.running = False
        sprint = Sprint.objects.filter(projet__id__exact = t.id, date_debut__lte = datetime.date.today(), date_fin__gte = datetime.date.today())
        if sprint:
            t.running = True
            t.sprint = sprint[0].id

        if i > nb_notes :
            projects.append(list())
            i = 1
            j += 1
        projects[j].append(t)
        i += 1
    return projects

# ------------------------------------------------
def list_features(project_id, sort = ['-priorite'], all = False, todo = True, max = 0, target = None, nb_notes = NOTES_PAR_LIGNE):
    tmp = Feature.objects.filter(projet__id__exact = project_id)
    tmp = tmp.order_by(*sort) if sort else tmp
    if not all:
        tmp = tmp.exclude(termine__exact = 1) if todo else tmp.filter(termine__exact = 1)

    features = list()
    features.append(list())
    i = 1
    j = 0
    n = 0
    for t in tmp:
        if target != None and target == t.id:
            t.target = True
        else:
            t.target = False

        notes = Note.objects.filter(feature__id__exact = t.id)
        t.temps_realise = 0
        t.temps_estime = 0
        for note in notes:
            t.temps_realise += note.temps_realise
            t.temps_estime += note.temps_estime

        t.notes = notes.count()

        if i > nb_notes :
            features.append(list())
            i = 1
            j += 1
        features[j].append(t)
        i += 1
        n += 1
        if not max == 0 and n == max:
            break

    return features

# ------------------------------------------------
def list_notes(feature_id, sort = ['-priorite'], all = False, todo = True, toset = False, max = 0, target = None, nb_notes = NOTES_PAR_LIGNE):
    tmp = Note.objects.filter(feature__id__exact = feature_id)
    tmp = tmp.order_by(*sort) if sort else tmp
    if not all:
        tmp = tmp.exclude(etat__exact = 2) if todo else tmp.filter(etat__exact = 2)
        tmp = tmp.exclude(sprint__id__isnull = False) if toset else tmp.filter(sprint__id__isnull = False)

    notes = list()
    notes.append(list())
    i = 1
    j = 0
    n = 0
    for t in tmp:
        if target != None and target == t.id:
            t.target = True
        else:
            t.target = False

        if i > nb_notes :
            notes.append(list())
            i = 1
            j += 1
        notes[j].append(t)
        i += 1
        n += 1
        if not max == 0 and n == max:
            break

    return notes

# ------------------------------------------------
def list_sprints(project_id, sort = ['-date_debut'], all = False, todo = True, max = 0, target = None, nb_notes = NOTES_PAR_LIGNE):
    tmp = Sprint.objects.filter(projet__id__exact = project_id)
    tmp = tmp.order_by(*sort) if sort else tmp
    if not all:    
        tmp = tmp.exclude(date_fin__lt = datetime.date.today()) if todo else tmp.filter(date_fin__lt = datetime.date.today())

    sprints = list()
    sprints.append(list())
    i = 1
    j = 0
    n = 0
    for t in tmp:
        if target != None and target == t.id:
            t.target = True
        else:
            t.target = False

        notes = Note.objects.filter(sprint__id__exact = t.id)
        tasks = Task.objects.filter(sprint__id__exact = t.id)

        t.temps_realise = 0
        t.temps_estime = 0
        for note in notes:
            if note.etat == '2' and note.temps_estime >= note.temps_realise:
                t.temps_realise += note.temps_estime
            else:
                t.temps_realise += note.temps_realise
            t.temps_estime += note.temps_estime
        for task in tasks:
            if task.etat == 2 and task.temps_estime >= task.temps_realise:
                t.temps_realise += task.temps_estime
            else:
                t.temps_realise += task.temps_realise
            t.temps_estime += task.temps_estime

        t.notes = notes.count() + tasks.count()

        nbn = Note.objects.filter(sprint__id__exact = t.id, etat__in = ('0', '1', )).count()
        nbt = Task.objects.filter(sprint__id__exact = t.id, etat__in = ('0', '1', )).count()
        nb = nbn + nbt
        if t.date_debut > datetime.date.today():
            t.etat = 'todo'
            t.urgence = 'minor'
        elif t.date_debut <= datetime.date.today() and t.date_fin >= datetime.date.today() and nb == 0:
            t.etat = 'done'
            t.urgence = 'major'
        elif t.date_debut <= datetime.date.today() and t.date_fin >= datetime.date.today() and nb > 0:
            t.etat = 'todo'
            t.urgence = 'major'
        elif t.date_fin < datetime.date.today() and nb > 0:
            t.etat = 'todo'
            t.urgence = 'critical'
        else:
            t.etat = 'done'
            t.urgence = 'none'

        if t.etat == 'done':
            value1 = '1'
        else:
            if t.temps_estime > 0:
                value1 = str(float(t.temps_realise) / t.temps_estime)
            else:
                value1 = '0'

        holidays = get_holidays(t.date_debut.year)

        nbd1 = 0
        d = t.date_debut
        while d <= datetime.date.today():
            if d.strftime('%w') in ('0', '6', ) or d in holidays:
                nbd1 += 1
            d += datetime.timedelta(1)

        nbd2 = 0
        d = t.date_debut
        while d <= t.date_fin:
            if d.strftime('%w') in ('0', '6', ) or d in holidays:
                nbd2 += 1
            d += datetime.timedelta(1)

        value2 = ((datetime.date.today() - t.date_debut).days -nbd1 +1) / float((t.date_fin - t.date_debut).days -nbd2 +1)
        if value2 > 1:
            value2 = str(1)
        else:
            value2 = str(value2)

        url  = "http://chart.apis.google.com/chart"
        url += "?cht=bhg"
        url += "&chs=200x100"
        url += "&chds=0,1"
        url += "&chl=0%|100%"
        url += "&chdl=Réalisé|Théorique"
        url += "&chdlp=b"
        url += "&chm=N*p0*,000000,-1,-1,11"
        url += "&chd=t:" + value1 + "," + value2
        url += "&chco=4d89f9|c6d9fd"
        url += "&chbh=20"
        t.url = url

        if i > nb_notes :
            sprints.append(list())
            i = 1
            j += 1
        if todo and t.etat == 'todo':
            sprints[j].append(t)
            i += 1
            n += 1
        else:
            sprints[j].append(t)
            i += 1
            n += 1
        if not max == 0 and n == max:
            break

    return sprints

# ------------------------------------------------
def list_snotes(sprint_id, sort = ['-priorite'], all = False, todo = True, work = False, max = 0, target = None, nb_notes = NOTES_PAR_LIGNE):
    tmp = Note.objects.select_related().filter(sprint__id__exact = sprint_id)
    tmp = tmp.order_by(*sort) if sort else tmp
    if not all:
        tmp = tmp.filter(etat__exact = 0) if todo else tmp.filter(etat__exact = 1) if work else tmp.filter(etat__exact = 2)

    notes = list()
    notes.append(list())
    i = 1
    j = 0
    n = 0
    for t in tmp:
        if target != None and target == t.id:
            t.target = True
        else:
            t.target = False

        if i > nb_notes :
            notes.append(list())
            i = 1
            j += 1
        notes[j].append(t)
        i += 1
        n += 1
        if not max == 0 and n == max:
            break

    return notes

# ------------------------------------------------
def list_tasks(sprint_id, sort = ['-priorite'], all = False, todo = True, work = False, max = 0, target = None, nb_notes = NOTES_PAR_LIGNE):
    tmp = Task.objects.filter(sprint__id__exact = sprint_id)
    tmp = tmp.order_by(*sort) if sort else tmp
    if not all:
        tmp = tmp.filter(etat__exact = 0) if todo else tmp.filter(etat__exact = 1) if work else tmp.filter(etat__exact = 2)

    tasks = list()
    tasks.append(list())
    i = 1
    j = 0
    n = 0
    for t in tmp:
        if target != None and target == t.id:
            t.target = True
        else:
            t.target = False

        if i > nb_notes :
            tasks.append(list())
            i = 1
            j += 1
        tasks[j].append(t)
        i += 1
        n += 1
        if not max == 0 and n == max:
            break

    return tasks

# ------------------------------------------------
def list_problems(project_id, sort = ['-priorite'], all = False, todo = True, max = 0, target = None, nb_notes = NOTES_PAR_LIGNE):
    tmp = Problem.objects.filter(projet__id__exact = project_id)
    tmp = tmp.order_by(*sort) if sort else tmp
    if not all:
        tmp = tmp.exclude(resolu__exact = 1) if todo else tmp.filter(resolu__exact = 1)

    problems = list()
    problems.append(list())
    i = 1
    j = 0
    n = 0
    for t in tmp:
        if target != None and target == t.id:
            t.target = True
        else:
            t.target = False

        if i > nb_notes :
            problems.append(list())
            i = 1
            j += 1
        problems[j].append(t)
        i += 1
        n += 1
        if not max == 0 and n == max:
            break

    return problems

# ------------------------------------------------
def list_releases(sprint_id, status = None):
    notes = Note.objects.select_related().filter(sprint__id__exact = sprint_id).exclude(etat__exact = 2)
    notes = notes.order_by('-priorite')
    
    releases = list()
    for n in notes:
        release = Release.objects.select_related().filter(note__id__exact = n.id)
        if release.count() == 0:    
            release = Release()
            release.note = n
            release.status = 0
            release.date_creation = n.date_creation
            release.utilisateur = n.utilisateur
            release.save()
        else:
            release = release.order_by('-date_creation')[0]
        if status:
            if release.status == str(status):
                releases.append(release)
        else:
            releases.append(release)
    return releases

# ------------------------------------------------
@login_required
@csrf_protect
def projects(request):
    user = request.user.get_profile()
    title = u'Projets'
    messages = list()

    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = home + 'projects'

    write_logs()
    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    projects = list_projects(nb_notes)

    membres = dict()
    for p in Project.objects.all():
        membres[p.id] = list()
        for m in p.membres.all():
            if not m.user.is_superuser:
                membres[p.id].append(m.user.username)

    return render_to_response('projects/projects.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 
         'projects': projects, 'membres': membres, 'nb_notes': nb_notes, })

# ------------------------------------------------
@login_required
@csrf_protect
def project(request, project_id):
    project = get_object_or_404(Project, pk = project_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Projet - "' + unicode(project.titre) + '"'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    f_all = Feature.objects.filter(projet__id__exact = project_id)
    f_done = f_all.filter(termine__gt = 0)

    s_all = Sprint.objects.filter(projet__id__exact = project_id)
    s_done = s_all.filter(date_fin__lt = datetime.date.today())

    p_all = Problem.objects.filter(projet__id__exact = project_id)
    p_done = p_all.filter(resolu__gt = 0)

    n_all = Note.objects.filter(feature__projet__id__exact = project.id, priorite__in = ('0', '2', '3', '4', '5'))
    n_done = n_all.filter(etat__exact = 2)

    na = 0
    for n in n_all:
        na += n.effort
    nd = 0
    for n in n_done:
        nd += n.effort

    features = list_features(project_id, max = nb_notes, nb_notes = nb_notes)
    sprints = list_sprints(project_id, max = nb_notes, nb_notes = nb_notes)
    problems = list_problems(project_id, max = nb_notes, nb_notes = nb_notes)

    return render_to_response('projects/project.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'nbf': '%d / %d' % (f_done.count(), f_all.count()), 'nbs': '%d / %d' % (s_done.count(), s_all.count()), 
         'nbp': '%d / %d' % (p_done.count(), p_all.count()), 'nbn': '%d / %d' % (nd, na),
         'features': features, 'sprints': sprints, 'problems': problems, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def features(request, project_id):
    project = get_object_or_404(Project, pk = project_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Fonctionnalités - Projet "' + unicode(project.titre) + '"'
    messages = list()
    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = home + 'projects/' + project_id + '/features'

    if request.method == 'GET':
        confiance = False
        if request.GET.__contains__('d'):
            feature = Feature.objects.get(pk = int(request.GET['d']))
            feature.confiance_dev = int(feature.confiance_dev) +1
            if int(feature.confiance_dev) > 3:
                feature.confiance_dev = '0'
            feature.save()
            confiance = True
        elif request.GET.__contains__('s'):
            feature = Feature.objects.get(pk = int(request.GET['s']))
            feature.confiance_sm = int(feature.confiance_sm) +1
            if int(feature.confiance_sm) > 3:
                feature.confiance_sm = '0'
            feature.save()
            confiance = True
        elif request.GET.__contains__('p'):
            feature = Feature.objects.get(pk = int(request.GET['p']))
            feature.confiance_po = int(feature.confiance_po) +1
            if int(feature.confiance_po) > 3:
                feature.confiance_po = '0'
            feature.save()
            confiance = True
        if confiance:
            return redirect('%s/#%d' % (request.session['url'], feature.id))    
    
    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)
    
    if request.method == 'POST':
        changes = list()
        if request.POST.__contains__('id'):
            feature = Feature.objects.get(pk = int(request.POST['id']))
            if request.POST.__contains__('priorite'):
                feature.priorite = int(request.POST['priorite'])
                changes.append(u'priorité = ' + PRIORITES[feature.priorite][1])
            if request.POST.__contains__('termine'):
                feature.termine = True
                changes.append(u'terminé = Oui')
            else:
                feature.termine = False
                changes.append(u'terminé = Non')
            feature.utilisateur = user
            feature.save()
            add_log(user, 'feature', feature, 2, ', '.join(changes))
            messages.append(u'Fonctionnalité modifiée avec succès !')

    sort = ['-priorite', 'termine']
    all = True
    todo = False
    target = None
    if request.method == 'GET':
        if request.GET.__contains__('sort'):
            sort = request.GET['sort'].split(',')
        if request.GET.__contains__('todo'):
            todo = True
            all = False
        if request.GET.__contains__('done'):
            todo = False
            all = False
        if request.GET.__contains__('target'):
            target = int(request.GET['target'])

    features = list_features(project_id, sort = sort, all = all, todo = todo, max = 0, target = target, nb_notes = nb_notes)

    return render_to_response('projects/features.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'features': features, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def feature(request, project_id, feature_id):
    project = get_object_or_404(Project, pk = project_id)
    feature = get_object_or_404(Feature, pk = feature_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Fonctionnalité - "' + unicode(feature.titre) + '"'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/features/' + feature_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    n_all = Note.objects.filter(feature__id__exact = feature_id)
    n_done = n_all.filter(etat__exact = 2)

    notes = list_notes(feature_id, max = nb_notes, nb_notes = nb_notes)

    return render_to_response('projects/feature.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'feature': feature, 'nbn': '%d / %d' % (n_done.count(), n_all.count()), 
         'notes': notes, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def notes(request, project_id, feature_id):
    project = get_object_or_404(Project, pk = project_id)
    feature = get_object_or_404(Feature, pk = feature_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Notes de backlog - Fonctionnalité "' + unicode(feature.titre) + '"'
    messages = list()
    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = home + 'projects/' + project_id + '/features/' + feature_id + '/notes'    

    if request.method == 'GET':
        confiance = False
        if request.GET.__contains__('d'):
            note = Note.objects.get(pk = int(request.GET['d']))
            note.confiance_dev = int(note.confiance_dev) +1
            if int(note.confiance_dev) > 3:
                note.confiance_dev = '0'
            note.save()
            confiance = True
        elif request.GET.__contains__('s'):
            note = Note.objects.get(pk = int(request.GET['s']))
            note.confiance_sm = int(note.confiance_sm) +1
            if int(note.confiance_sm) > 3:
                note.confiance_sm = '0'
            note.save()
            confiance = True
        elif request.GET.__contains__('p'):
            note = Note.objects.get(pk = int(request.GET['p']))
            note.confiance_po = int(note.confiance_po) +1
            if int(note.confiance_po) > 3:
                note.confiance_po = '0'
            note.save()
            confiance = True
        if confiance:
            return redirect('%s/#%d' % (request.session['url'], note.id))
    
    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)
    
    if request.method == 'POST':
        changes = list()
        if request.POST.__contains__('id'):
            note = Note.objects.get(pk = int(request.POST['id']))
            if request.POST.__contains__('priorite'):
                note.priorite = int(request.POST['priorite'])
                changes.append(u'priorité = ' + PRIORITES[note.priorite][1])
            if request.POST.__contains__('sprint'):
                if request.POST['sprint'] == '':
                    #note.temps_realise = 0
                    note.sprint = None
                    times = NoteTime.objects.filter(note__id__exact = note.id)
                    times.delete()
                    changes.append(u'sprint = <Aucun>')
                else:
                    sprint = Sprint.objects.get(pk = int(request.POST['sprint']))
                    if not note.sprint == sprint:
                        #note.temps_realise = 0
                        times = NoteTime.objects.filter(note__id__exact = note.id)
                        times.delete()
                        create_note_days(sprint, note)
                    note.sprint = sprint
                    changes.append(u'sprint = ' + note.sprint.titre)
            if request.POST.__contains__('temps'):
                note.temps_estime = int(request.POST['temps'])
                changes.append(u'temps = ' + str(note.temps_estime))
            note.utilisateur = user
            note.save()
            add_log(user, 'note', note, 2, ', '.join(changes))
            messages.append(u'Note de backlog modifiée avec succès !')

    sort = ['-priorite', 'etat']
    all = True
    todo = False
    toset = False
    target = None
    if request.method == 'GET':
        if request.GET.__contains__('sort'):
            sort = request.GET['sort'].split(',')
        if request.GET.__contains__('todo'):
            todo = True
            toset = False
            all = False
        elif request.GET.__contains__('done'):
            todo = False
            toset = False
            all = False
        elif request.GET.__contains__('toset'):
            todo = True
            toset = True
            all = False
        if request.GET.__contains__('target'):
            target = int(request.GET['target'])

    notes = list_notes(feature_id, sort = sort, all = all, todo = todo, toset = toset, max = 0, target = target, nb_notes = nb_notes)
    sprints = Sprint.objects.filter(projet__id__exact = project_id)

    return render_to_response('projects/notes.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'feature': feature, 'notes': notes, 'sprints': sprints, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def note(request, project_id, feature_id, note_id):
    project = get_object_or_404(Project, pk = project_id)
    feature = get_object_or_404(Feature, pk = feature_id)
    note = get_object_or_404(Note, pk = note_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Note de backlog - "' + unicode(note.titre) + '"'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/features/' + feature_id + '/notes/' + note_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    return render_to_response('projects/note.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'feature': feature, 'note': note, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def sprints(request, project_id):
    project = get_object_or_404(Project, pk = project_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Sprints - Projet "' + unicode(project.titre) + '"'
    messages = list()
    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = home + 'projects/' + project_id + '/sprints'  

    if request.method == 'GET':
        confiance = False
        if request.GET.__contains__('d'):
            sprint = Sprint.objects.get(pk = int(request.GET['d']))
            sprint.confiance_dev = int(sprint.confiance_dev) +1
            if int(sprint.confiance_dev) > 3:
                sprint.confiance_dev = '0'
            sprint.save()
            confiance = True
        elif request.GET.__contains__('s'):
            sprint = Sprint.objects.get(pk = int(request.GET['s']))
            sprint.confiance_sm = int(sprint.confiance_sm) +1
            if int(sprint.confiance_sm) > 3:
                sprint.confiance_sm = '0'
            sprint.save()
            confiance = True
        elif request.GET.__contains__('p'):
            sprint = Sprint.objects.get(pk = int(request.GET['p']))
            sprint.confiance_po = int(sprint.confiance_po) +1
            if int(sprint.confiance_po) > 3:
                sprint.confiance_po = '0'
            sprint.save()
            confiance = True
        if confiance:
            return redirect('%s/#%d' % (request.session['url'], sprint.id))    
    
    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)
    
    if request.method == 'POST' and request.POST.__contains__('id'):
        id = int(request.POST['id'])
        sprint = Sprint.objects.get(pk = id)
        tmp = time.strptime(request.POST['date_debut'], '%Y-%m-%d')
        date_debut = datetime.date(tmp[0], tmp[1], tmp[2])
        tmp = time.strptime(request.POST['date_fin'], '%Y-%m-%d')
        date_fin = datetime.date(tmp[0], tmp[1], tmp[2])
        # ------------------------------------------------------------
        holidays = get_holidays(date_debut.year)
        d = date_debut
        while d <= date_fin:
            if d.strftime('%w') not in ('0', '6', ) and d not in holidays:
                notes = Note.objects.filter(sprint__id__exact = id)
                for note in notes:
                    if NoteTime.objects.filter(sprint__id__exact = id, jour__exact = d, note__id__exact = note.id).count() == 0:   
                        time = NoteTime()
                        time.sprint = sprint
                        time.note = note
                        time.jour = d
                        time.temps = 0
                        time.save()
                tasks = Task.objects.filter(sprint__id__exact = id)
                for task in tasks:
                    if TaskTime.objects.filter(sprint__id__exact = id, jour__exact = d, task__id__exact = task.id).count() == 0:
                        time = TaskTime()
                        time.sprint = sprint
                        time.task = task
                        time.jour = d
                        time.temps = 0
                        time.save()
            d += datetime.timedelta(1)
        # ------------------------------------------------------------
        notes = NoteTime.objects.filter(sprint__id__exact = id, jour__lt = date_debut)
        for note in notes:
            note.delete()
        notes = NoteTime.objects.filter(sprint__id__exact = id, jour__gt = date_fin)
        for note in notes:
            note.delete()
        tasks = TaskTime.objects.filter(sprint__id__exact = id, jour__lt = date_debut)
        for task in tasks:
            task.delete()
        tasks = TaskTime.objects.filter(sprint__id__exact = id, jour__gt = date_fin)
        for task in tasks:
            task.delete()
        # ------------------------------------------------------------
        sprint.date_debut = date_debut
        sprint.date_fin = date_fin
        sprint.save()
        messages.append(u'Sprint modifié avec succès !')
        add_log(user, 'sprint', sprint, 2, u'date début = %s, date fin = %s' % (date_debut, date_fin))

    sort = ['-date_debut']
    all = True
    todo = False
    target = None
    if request.method == 'GET':
        if request.GET.__contains__('sort'):
            sort = request.GET['sort'].split(',')
        if request.GET.__contains__('todo'):
            todo = True
            all = False
        elif request.GET.__contains__('done'):
            todo = False
            all = False
        if request.GET.__contains__('target'):
            target = int(request.GET['target'])

    sprints = list_sprints(project_id, sort = sort, all = all, todo = todo, max = 0, target = target, nb_notes = nb_notes)

    return render_to_response('projects/sprints.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'sprints': sprints, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def sprint(request, project_id, sprint_id):
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Sprint - "' + unicode(sprint.titre) + '"'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/sprints/' + sprint_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    n_all = Note.objects.filter(sprint__id__exact = sprint_id)
    t_all = Task.objects.filter(sprint__id__exact = sprint_id)
    n_done = n_all.filter(etat__exact = 2)
    t_done = t_all.filter(etat__exact = 2)

    notes = list_snotes(sprint_id, max = nb_notes, nb_notes = nb_notes)
    tasks = list_tasks(sprint_id, max = nb_notes, nb_notes = nb_notes)

    return render_to_response('projects/sprint.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'sprint': sprint, 'nbn': '%d / %d' % (n_done.count(), n_all.count()), 'nbt': '%d / %d' % (t_done.count(), t_all.count()), 
         'notes': notes, 'tasks': tasks, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def snotes(request, project_id, sprint_id):
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Notes de sprint - Sprint "' + unicode(sprint.titre) + '"'
    messages = list()
    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = home + 'projects/' + project_id + '/sprints/' + sprint_id + '/notes'

    if request.method == 'GET':
        confiance = False
        if request.GET.__contains__('d'):
            note = Note.objects.get(pk = int(request.GET['d']))
            note.confiance_dev = int(note.confiance_dev) +1
            if int(note.confiance_dev) > 3:
                note.confiance_dev = '0'
            note.save()
            confiance = True
        elif request.GET.__contains__('s'):
            note = Note.objects.get(pk = int(request.GET['s']))
            note.confiance_sm = int(note.confiance_sm) +1
            if int(note.confiance_sm) > 3:
                note.confiance_sm = '0'
            note.save()
            confiance = True
        elif request.GET.__contains__('p'):
            note = Note.objects.get(pk = int(request.GET['p']))
            note.confiance_po = int(note.confiance_po) +1
            if int(note.confiance_po) > 3:
                note.confiance_po = '0'
            note.save()  
            confiance = True
        if confiance:
            return redirect('%s/#%d' % (request.session['url'], note.id))

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'POST':
        changes = list()
        if request.POST.__contains__('id'):
            note = Note.objects.get(pk = int(request.POST['id']))
            if request.POST.__contains__('priorite'):
                note.priorite = int(request.POST['priorite'])
                changes.append(u'priorité = ' + PRIORITES[note.priorite][1])
            if request.POST.__contains__('etat'):
                note.etat = int(request.POST['etat'])
                if note.etat == 2:
                    nts = NoteTime.objects.filter(note__in = (note, ))
                    nts = nts.order_by('-jour')
                    for nt in nts:
                        if nt.temps > 0:
                            fin = nt.note.temps_estime - nt.note.temps_realise
                            nt.temps_fin = fin
                            nt.save()
                            break
                else:
                    nts = NoteTime.objects.filter(note__in = (note, ))
                    for nt in nts:
                        nt.temps_fin = 0
                        nt.save()
                changes.append(u'état = ' + ETATS[note.etat][1])
            note.utilisateur = user
            note.save()
            add_log(user, 'note', note, 2, ', '.join(changes))
            messages.append(u'Note de sprint modifiée avec succès !')

    sort = ['-priorite', 'etat']
    all = True
    todo = False
    work = False
    target = None
    if request.method == 'GET':
        if request.GET.__contains__('sort'):
            sort = request.GET['sort'].split(',')
        if request.GET.__contains__('todo'):
            todo = True
            work = False
            all = False
        elif request.GET.__contains__('work'):
            todo = False
            work = True
            all = False
        elif request.GET.__contains__('done'):
            todo = False
            work = False
            all = False
        if request.GET.__contains__('target'):
            target = int(request.GET['target'])

    notes = list_snotes(sprint_id, sort = sort, all = all, todo = todo, work = work, max = 0, target = target, nb_notes = nb_notes)

    return render_to_response('projects/snotes.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'feature': feature, 'sprint': sprint, 'notes': notes, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def snote(request, project_id, sprint_id, note_id):
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)
    note = get_object_or_404(Note, pk = note_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Note de sprint - "' + unicode(note.titre) + '"'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/sprints/' + sprint_id + '/notes/' + note_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    return render_to_response('projects/snote.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'sprint': sprint, 'note': note, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def tasks(request, project_id, sprint_id):
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)    

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Tâches - Sprint "' + unicode(sprint.titre) + '"'
    messages = list()
    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = home + 'projects/' + project_id + '/sprints/' + sprint_id + '/tasks' 

    if request.method == 'GET':
        confiance = False
        if request.GET.__contains__('d'):
            task = Task.objects.get(pk = int(request.GET['d']))
            task.confiance_dev = int(task.confiance_dev) +1
            if int(task.confiance_dev) > 3:
                task.confiance_dev = '0'
            task.save()
            confiance = True
        elif request.GET.__contains__('s'):
            task = Task.objects.get(pk = int(request.GET['s']))
            task.confiance_sm = int(task.confiance_sm) +1
            if int(task.confiance_sm) > 3:
                task.confiance_sm = '0'
            task.save()
            confiance = True
        elif request.GET.__contains__('p'):
            task = Task.objects.get(pk = int(request.GET['p']))
            task.confiance_po = int(task.confiance_po) +1
            if int(task.confiance_po) > 3:
                task.confiance_po = '0'
            task.save() 
            confiance = True
        if confiance:
            return redirect('%s/#%d' % (request.session['url'], task.id))

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'POST':
        changes = list()
        if request.POST.__contains__('id'):
            task = Task.objects.get(pk = int(request.POST['id']))
            if request.POST.__contains__('priorite'):
                task.priorite = int(request.POST['priorite'])
            if request.POST.__contains__('etat'):
                task.etat = int(request.POST['etat'])
                if task.etat == 2:
                    tts = TaskTime.objects.filter(task__in = (task, ))
                    tts = tts.order_by('-jour')
                    for tt in tts:
                        if tt.temps > 0:
                            fin = tt.task.temps_estime - tt.task.temps_realise
                            tt.temps_fin = fin
                            tt.save()
                            break
                else:
                    tts = TaskTime.objects.filter(task__in = (task, ))
                    for tt in tts:
                        tt.temps_fin = 0
                        tt.save()
            if request.POST.__contains__('temps'):
                task.temps_estime = int(request.POST['temps'])
            task.utilisateur = user
            task.save()
            add_log(user, 'task', task, 2, ', '.join(changes))
            messages.append(u'Tâche modifiée avec succès !')

    sort = ['-priorite', 'etat']
    all = True
    todo = False
    work = False
    target = None
    if request.method == 'GET':
        if request.GET.__contains__('sort'):
            sort = request.GET['sort'].split(',')
        if request.GET.__contains__('todo'):
            todo = True
            work = False
            all = False
        elif request.GET.__contains__('work'):
            todo = False
            work = True
            all = False
        elif request.GET.__contains__('done'):
            todo = False
            work = False
            all = False
        if request.GET.__contains__('target'):
            target = int(request.GET['target'])

    tasks = list_tasks(sprint_id, sort = sort, all = all, todo = todo, max = 0, target = target, nb_notes = nb_notes)

    return render_to_response('projects/tasks.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'sprint': sprint, 'tasks': tasks, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def task(request, project_id, sprint_id, task_id):
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)
    task = get_object_or_404(Task, pk = task_id)    

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Tâche - Sprint "' + unicode(task.titre) + '"'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/sprints/' + sprint_id + '/tasks/' + task_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    return render_to_response('projects/task.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'sprint': sprint, 'task': task, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def releases(request, project_id, sprint_id):
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)   

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Livraisons - Sprint "' + unicode(sprint.titre) + '"'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/sprints/' + sprint_id + '/releases'

    status = '0'
    note = None
    details = list()
    if request.GET.__contains__('id'):
        note = int(request.GET['id'])
        details = Release.objects.filter(note__id__exact = note)
        details = details.order_by('date_creation')
    if request.GET.__contains__('status'):
        status = request.GET['status']    
    
    if request.method == 'POST':
        changes = list()
        if request.POST.__contains__('id'):
            id = request.POST['id']
            note = Note.objects.get(pk = id)
            release = Release()
            release.note = note
            release.utilisateur = user
            if request.POST.__contains__('livrer'):
                release.status = 1
                #status = release.status
                release.save()
                changes.append(u'status = ' + STATUS[release.status][1])
                add_log(user, 'release', release, 2, ', '.join(changes))
                messages.append(u'Livraison effectuée avec succès ! ( <a href=".?status=%d#%d">voir l\'élément</a> )' 
                    % (release.status, release.id))
            elif request.POST.__contains__('refuser'):
                release.status = 2
                #status = release.status
                release.save()
                changes.append(u'status = ' + STATUS[release.status][1])
                add_log(user, 'release', release, 2, ', '.join(changes))
                messages.append(u'Livraison refusée avec succès ! ( <a href=".?status=%d#%d">voir l\'élément</a> )' 
                    % (release.status, release.id))
            elif request.POST.__contains__('valider'):
                release.status = 3
                #status = release.status
                release.save()
                changes.append(u'status = ' + STATUS[release.status][1])
                add_log(user, 'release', release, 2, ', '.join(changes))
                messages.append(u'Livraison validée avec succès ! ( <a href=".?status=%d#%d">voir l\'élément</a> )'
                    % (release.status, release.id))
            elif request.POST.__contains__('terminer'):
                nts = NoteTime.objects.filter(note__in = (note, ))
                nts = nts.order_by('-jour')
                for nt in nts:
                    if nt.temps > 0:
                        fin = nt.note.temps_estime - nt.note.temps_realise
                        nt.temps_fin = fin
                        nt.save()
                        break
                note.etat = 2
                note.save()
                changes.append(u'etat = ' + ETATS[note.etat][1])
                add_log(user, 'note', note, 2, ', '.join(changes))
                messages.append(u'Note de backlog terminée avec succès !')

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    releases = list_releases(sprint_id, status)

    return render_to_response('projects/releases.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'sprint': sprint, 'releases': releases, 'note': note, 'details': details, 'nb_notes': nb_notes, 'status': status, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def release(request, project_id, sprint_id, release_id):
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id) 
    release = get_object_or_404(Release, pk = release_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Livraison - "' + unicode(release.note.titre) + '"'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/sprints/' + sprint_id + '/releases/' + release_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    return render_to_response('projects/releases.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'sprint': sprint, 'release': release, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def problems(request, project_id):
    project = get_object_or_404(Project, pk = project_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Problèmes - Projet "' + unicode(project.titre) + '"'
    messages = list()
    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = home + 'projects/' + project_id + '/problems'

    if request.method == 'GET':
        confiance = False
        if request.GET.__contains__('d'):
            problem = Problem.objects.get(pk = int(request.GET['d']))
            problem.confiance_dev = int(problem.confiance_dev) +1
            if int(problem.confiance_dev) > 3:
                problem.confiance_dev = '0'
            problem.save()
            confiance = True
        elif request.GET.__contains__('s'):
            problem = Problem.objects.get(pk = int(request.GET['s']))
            problem.confiance_sm = int(problem.confiance_sm) +1
            if int(problem.confiance_sm) > 3:
                problem.confiance_sm = '0'
            problem.save()
            confiance = True
        elif request.GET.__contains__('p'):
            problem = Problem.objects.get(pk = int(request.GET['p']))
            problem.confiance_po = int(problem.confiance_po) +1
            if int(problem.confiance_po) > 3:
                problem.confiance_po = '0'
            problem.save() 
            confiance = True
        if confiance:
            return redirect('%s/#%d' % (request.session['url'], problem.id))

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'POST':
        changes = list()
        if request.POST.__contains__('id'):
            problem = Problem.objects.get(pk = int(request.POST['id']))
            if request.POST.__contains__('priorite'):
                problem.priorite = int(request.POST['priorite'])
                changes.append(u'priorité = ' + PRIORITES[problem.priorite][1])
            if request.POST.__contains__('resolu'):
                problem.resolu = True
                changes.append(u'résolu = Oui')
            else:
                problem.resolu = False
                changes.append(u'résolu = Non')
            problem.utilisateur = user
            problem.save()
            add_log(user, 'problem', problem, 2, ', '.join(changes))
            messages.append(u'Problème modifié avec succès !')

    sort = ['-priorite', 'resolu']
    all = True
    todo = False
    target = None
    if request.method == 'GET':
        if request.GET.__contains__('sort'):
            sort = request.GET['sort'].split(',')
        if request.GET.__contains__('todo'):
            todo = True
            all = False
        elif request.GET.__contains__('done'):
            todo = False
            all = False
        if request.GET.__contains__('target'):
            target = int(request.GET['target'])

    problems = list_problems(project_id, sort = sort, all = all, todo = todo, max = 0, target = target, nb_notes = nb_notes)

    return render_to_response('projects/problems.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'problems': problems, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def problem(request, project_id, problem_id):
    project = get_object_or_404(Project, pk = project_id)
    problem = get_object_or_404(Problem, pk = problem_id)    

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Problème - "' + unicode(problem.titre) + '"'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/problems/' + problem_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    return render_to_response('projects/problem.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'problem': problem, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def burndown(request, project_id, sprint_id):
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)
    lock = sprint.date_modification.strftime('%d/%m/%Y %H:%M:%S')

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Burndown Chart - Sprint "' + unicode(sprint.titre) + '"'
    messages = list()
    erreurs = list()
    request.session['url'] = home + 'projects/' + project_id + '/sprints/' + sprint_id + '/burndown'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'POST':
        changes = list()
        if request.POST['lock'] == lock:
            for id in request.POST:
                if id[0:4] == 'Note':
                    time = NoteTime.objects.get(pk = int(id[4:]))
                    note = time.note
                    temps = int(request.POST[id])
                    if (temps == 0):
                        time.date_modification = None
                        time.utilisateur = None
                    elif (time.temps != temps):
                        note.etat = '1'
                        time.date_modification = datetime.datetime.now()
                        time.utilisateur = user
                    note.temps_realise = note.temps_realise - time.temps
                    time.temps = temps
                    note.temps_realise = note.temps_realise + time.temps
                    note.save()
                    time.save()
                elif id[0:5] == 'Tache':
                    time = TaskTime.objects.get(pk = int(id[5:]))
                    task = time.task
                    temps = int(request.POST[id])
                    if (temps == 0):
                        time.date_modification = None
                        time.utilisateur = None
                    elif (time.temps != temps):
                        task.etat = '1'
                        time.date_modification = datetime.datetime.now()
                        time.utilisateur = user
                    task.temps_realise = task.temps_realise - time.temps
                    time.temps = temps
                    task.temps_realise = task.temps_realise + time.temps
                    task.save()
                    time.save()
                elif id[0:5] == '_Note':
                    note = Note.objects.get(pk = int(id[5:]))
                    etat = '2' if request.POST[id] == 'oui' else '1'
                    if note.etat in ('0', '1') and etat == '2':
                        nts = NoteTime.objects.filter(note__in = (note, ))
                        nts = nts.order_by('-jour')
                        for nt in nts:
                            if nt.temps > 0:
                                fin = nt.note.temps_estime - nt.note.temps_realise
                                nt.temps_fin = fin
                                nt.save()
                                break
                    elif note.etat == '2' and etat == '1':
                        nts = NoteTime.objects.filter(note__in = (note, ))
                        etat = '0'
                        for nt in nts:
                            if nt.temps > 0:
                                etat = '1'
                            nt.temps_fin = 0
                            nt.save()
                    note.etat = etat
                    note.save()
                    changes.append(u'état = ' + ETATS[int(note.etat)][1])
                    add_log(user, 'note', note, 2, ', '.join(changes))
                elif id[0:6] == '_Tache':
                    task = Task.objects.get(pk = int(id[6:]))
                    etat = '2' if request.POST[id] == 'oui' else '1'
                    if task.etat in ('0', '1') and etat == 2:
                        tts = TaskTime.objects.filter(task__in = (task, ))
                        tts = tts.order_by('-jour')
                        for tt in tts:
                            if tt.temps > 0:
                                fin = tt.task.temps_estime - tt.task.temps_realise
                                tt.temps_fin = fin
                                tt.save()
                                break
                    elif task.etat == '2' and etat == '1':
                        tts = TaskTime.objects.filter(task__in = (task, ))
                        etat = '0'
                        for tt in tts:
                            if tt.temps > 0:
                                etat = '1'
                            tt.temps_fin = 0
                            tt.save()
                    task.etat = etat
                    task.save()
                    changes.append(u'état = ' + ETATS[int(task.etat)][1])
                    add_log(user, 'task', task, 2, ', '.join(changes))
                now = datetime.datetime.now()
                sprint.date_modification = now
                lock = now.strftime('%d/%m/%Y %H:%M:%S')
                sprint.save()
            messages.append(u'Saisie de temps enregistrée avec succès !')
        else:
            erreurs.append(u'Saisie annulée : les données ont été modifiées avant l\'enregistrement !')
    
    holidays = get_holidays(datetime.date.today().year)

    released = request.GET.__contains__('released')
    done = request.GET.__contains__('done')    

    days = list()
    times = list()
    total = 0

    notes = Note.objects.select_related().filter(sprint__id__exact = sprint_id)
    notes = notes.order_by('-priorite')

    for n in notes:
        d = dict()
        nt = NoteTime.objects.filter(sprint__id__exact = sprint_id, note__id__exact = n.id)
        nt = nt.exclude(jour__in = holidays)
        nt = nt.order_by('jour')
        d['id'] = n.id
        d['bid'] = n.feature.id
        d['base'] = n.feature.titre
        d['name'] = n.titre
        d['type'] = u'Note'
        d['item'] = n
        d['time'] = nt
        d['done'] = n.temps_realise
        d['todo'] = n.temps_estime
        d['test'] = (n.etat == '2')
        d['line'] = str(n.feature.id) + '_' + str(n.id)
        d['etat'] = '?done' if done else '?released' if released else '.'
        d['url'] = 'notes'
        releases = Release.objects.filter(note__id__exact = n.id).order_by('-date_creation')
        if releases.count() > 0:
            release = releases[0]
            if released:
                if release.status in ('1', '3') and n.etat != '2':
                    times.append(d)
            elif done and n.etat == '2':
                times.append(d)
            elif not done and release.status in ('0', '2') and n.etat != '2':
                times.append(d)
        else:
            if done and n.etat == '2':
                times.append(d)
            elif not done and n.etat != '2':
                times.append(d)
        for d in nt:
            days.append(d.jour)
        total += n.temps_estime

    tasks = Task.objects.filter(sprint__id__exact = sprint_id)
    tasks = tasks.order_by('-priorite')

    for t in tasks:
        d = dict()
        tt = TaskTime.objects.filter(sprint__id__exact = sprint_id, task__id__exact = t.id)
        tt = tt.exclude(jour__in = holidays)
        tt = tt.order_by('jour')
        d['id'] = t.id
        d['bid'] = 0
        d['base'] = ''
        d['name'] = t.titre
        d['type'] = u'Tache'
        d['item'] = t
        d['time'] = tt
        d['done'] = t.temps_realise
        d['todo'] = t.temps_estime
        d['test'] = (t.etat == '2')
        d['line'] = str(n.id)
        d['etat'] = '?done' if done else '.'
        d['url'] = 'tasks'
        if done and t.etat == '2':
            times.append(d)
        elif not done and t.etat != '2':
            times.append(d)
        for d in tt:
            days.append(d.jour)
        total += t.temps_estime

    days = list(set(days))
    days.sort()

    min = 0
    data1 = list()
    tmp = total
    data1.append(tmp)
    for day in days:
        nts = NoteTime.objects.filter(sprint__id__exact = sprint.id, jour__exact = day)
        tts = TaskTime.objects.filter(sprint__id__exact = sprint.id, jour__exact = day)
        for t in nts:
            tmp -= (t.temps + t.temps_fin)
        for t in tts:
            tmp -= (t.temps + t.temps_fin)
        if tmp < 0 and tmp < min:
            min = tmp
        data1.append(tmp)

    data2 = list()
    tmp = total
    data2.append(tmp)
    for day in days:
        tmp = tmp - (float(total) / (len(days)))
        if tmp < 0:
            tmp = 0
        data2.append(tmp)

    url  = 'http://chart.apis.google.com/chart'
    url += '?chs=800x350'
    url += '&cht=lxy'
    url += '&chg=' + str(100.0 / len(days)) + ',0'
    url += '&chdl=Temps restant|Temps estimé'
    url += '&chdlp=b'
    url += '&chxt=x,y'
    url += '&chxl=0:||' + '|'.join('%s' % (d.strftime('%d/%m')) for d in days)
    url += '&chxr=1,' + str(min) + ',' + str(total)
    url += '&chds=0,0,' + str(min) + ',' + str(total)
    url += '&chco=0000ff,ff0000,00aaaa'
    url += '&chls=2,4,2|2,0,0|2,0,0'
    url += '&chm=s,ff0000,0,-1,5|N*f0*,000000,0,-1,11|s,0000ff,1,-1,5|s,00aa00,2,-1,5'
    url += '&chf=c,lg,45,ffffff,0,76a4fb,0.75'
    url += '&chd=t:-1|' + ','.join('%s' % (x) for x in data1)
    url += '|-1|' + ','.join('%s' % (y) for y in data2)

    return render_to_response('projects/burndown.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'sprint': sprint, 'days': days, 'times': times, 'lock': lock,
         'url': url, 'date': datetime.date.today(), 'erreurs': erreurs, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

#-------------------------------------------------
@login_required
@csrf_protect
def velocity(request, project_id):
    project = get_object_or_404(Project, pk = project_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Velocité - Projet "' + unicode(project.titre) + '"'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/velocity'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    sprints = Sprint.objects.filter(projet__id__exact = project.id).order_by('date_debut')
    
    i = 0
    labels = list()
    for sprint in sprints:
        i += 1
        labels.append("Sprint %d" % (i))

    data = [list(), list(), list(), list()]
    for i in range(4):
        s = 0
        for sprint in sprints:
            notes = Note.objects.filter(sprint__id__exact = sprint.id, type__exact = i, etat__exact = 2)
            n = 0
            for note in notes:
                n += note.effort
            data[i].insert(s, n)
            s += 1

    max1 = 0
    for i in range(sprints.count()):
        n = 0
        for j in range(4):
            n += data[j][i]
        if n > max1:
            max1 = n

    url1  = 'http://chart.apis.google.com/chart'
    url1 += '?chs=800x350'
    url1 += '&cht=bvs'
    url1 += '&chbh=a'
    url1 += '&chdl=User-story|Feature|Bug|Spike'
    url1 += '&chdlp=t'
    url1 += '&chxt=x,y'
    url1 += '&chxl=0:|' + '|'.join(labels)
    url1 += '&chxr=1,0,' + str(max1)
    url1 += '&chds=0,' + str(max1)
    url1 += '&chco=ccffcc,ffffcc,ffcc99,cecaff'
    url1 += '&chm=N,ff0000,-1,,12,,e::11|N,000000,0,,11,,c|N,000000,1,,11,,c|N,000000,2,,10,,c|N,000000,3,,11,,c'
    url1 += '&chf=c,lg,45,ffffff,0,76a4fb,0.75'
    url1 += '&chd=t:' + '|'.join('%s' % (','.join('%s' % (v) for v in values)) for values in data)

    i = 0
    first = True
    cumul = 0
    max2 = 0
    charge1 = list()
    charge2 = list()
    labels = list()
    for sprint in sprints:
        i += 1
        labels.append("Sprint %d" % (i))
        notes = Note.objects.filter(sprint__id__exact = sprint.id, etat__exact = 2)
        n = 0
        for note in notes:
            n += note.effort
        charge1.append(cumul + n)
        cumul += n
        if first:
            charge2.append(sprint.effort)
            first = False
        charge2.append(sprint.effort)
        if sprint.effort > max2:
            max2 = sprint.effort
    avg = cumul / sprints.count()
    avgs = charge1[:]
    tmp = cumul
    while tmp < max2:
        tmp += avg
        avgs.append(tmp)
        labels.append("Sprint %d" % (len(labels) + 1))
        charge1.append(cumul)
        charge2.append(sprint.effort)
    l = [max(charge1), max(charge2), max(avgs)]
    max2 = max(l)

    url2  = 'http://chart.apis.google.com/chart'
    url2 += '?chs=800x350'
    url2 += '&cht=lxy'
    url2 += '&chg=' + str(100.0 / len(charge1)) + ',0'
    url2 += '&chdl=Charge réalisée|Charge totale|Charge estimée'
    url2 += '&chdlp=t'
    url2 += '&chxt=x,y'
    url2 += '&chxl=0:||' + '|'.join(labels)
    url2 += '&chxr=1,0,' + str(max2)
    url2 += '&chds=0,0,0,' + str(max2)
    url2 += '&chco=00aa00,ff0000,0000ff'
    url2 += '&chls=2,4,2|2,0,0|2,4,2'
    url2 += '&chm=s,ff0000,0,-1,5|N*f0*,000000,0,-1,11|s,0000ff,1,-1,5|N*f0*,ff0000,1,-1,11|s,ff0000,2,-1,5|N*f0*,000000,2,-1,11'
    url2 += '&chf=c,lg,45,ffffff,0,76a4fb,0.75'
    url2 += '&chd=t:-1|0,' + ','.join('%s' % (x) for x in charge1)
    url2 += '|-1|' + ','.join('%s' % (y) for y in charge2)
    url2 += '|-1|0,' + ','.join('%s' % (z) for z in avgs)

    return render_to_response('projects/velocity.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'url1': url1, 'url2': url2, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def summary(request, project_id):
    project = get_object_or_404(Project, pk = project_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Synthèse - Projet "' + unicode(project.titre) + '"'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/summary'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)
    
    id = request.GET['sprint'] if request.GET.__contains__('sprint') else 0
    sprints = Sprint.objects.filter(projet__id__exact = project.id).order_by('-date_debut')
    
    items = list()
    for sprint in sprints:
        item = dict()
        item['id'] = str(sprint.id)
        item['sprint'] = sprint
        done = NoteTime.objects.filter(note__sprint__id__exact = sprint.id).values('jour').annotate(done = Sum('temps'), more = Sum('temps_fin')).order_by('jour')
        todo = Note.objects.filter(sprint__id__exact = sprint.id).values('sprint').annotate(todo = Sum('temps_estime'))
        item['total_todo'] = todo[0]['todo'] if todo.count() > 0 else 0
        item['total_done'] = 0
        last = 0
        avg = list()
        rates = list()
        times_todo = list()
        times_done = list()
        for time in done:
            time['day'] = time['jour'].strftime('%d/%m')
            time_done = time['done'] + time['more']
            item['total_done'] += time_done
            time['todo'] = times_todo[-1] - time_done if len(times_todo) > 0 else item['total_todo'] - time_done if item['total_todo'] > 0 else 0
            times_todo.append(time['todo'])
            rate1 = int(round(100.0 * time_done / item['total_todo'])) if item['total_todo'] > 0 else 0
            time['rate1'] = rate1
            rate2 = rate1 + sum(rates)
            time['rate2'] = rate2
            if time['done'] > 0:
                times_done.append(time['done'])
                time['avg'] = int(round(1.0 * sum(times_done) / len(times_done)))
                last = time['avg']
            else:
                time['avg'] = last
            time['trend1'] = u'=' if len(rates) < 1 else u'+' if rates[-1] < rate1 else u'-' if rates[-1] > rate1 else u'='
            time['trend2'] = u'=' if len(avg) < 1 else u'+' if avg[-1] < time['avg'] else u'-' if avg[-1] > time['avg'] else u'='
            avg.append(time['avg'])
            rates.append(rate1)
        item['times'] = done
        
        days = list()
        chart1 = list()
        chart2 = list()
        for time in done:
            days.append(time['day'])
            chart1.append(time['done'])
            chart2.append(time['avg'])
        l = [max(chart1), max(chart2)]
        max1 = max(l)
        
        url1  = 'http://chart.apis.google.com/chart'
        url1 += '?chs=800x350'
        url1 += '&cht=lxy'
        url1 += '&chg=' + str(100.0 / len(days)) + ',0'
        url1 += '&chdl=Temps réalisé|Temps moyen estimé'
        url1 += '&chdlp=t'
        url1 += '&chxt=x,y'
        url1 += '&chxl=0:||' + '|'.join('%s' % (str(day)) for day in days)
        url1 += '&chxr=1,0,' + str(max1)
        url1 += '&chds=0,0,0,' + str(max1)
        url1 += '&chco=0000ff,ff0000,00aaaa'
        url1 += '&chls=2,4,2|2,0,0|2,0,0'
        url1 += '&chm=s,ff0000,0,-1,5|N*f0*,000000,0,-1,11|s,0000ff,1,-1,5|N*f0*,ff0000,1,-1,11|s,00aa00,2,-1,5'
        url1 += '&chf=c,lg,45,ffffff,0,76a4fb,0.75'
        url1 += '&chd=t:-1|0,' + ','.join('%s' % (x) for x in chart1)
        url1 += '|-1|0,' + ','.join('%s' % (y) for y in chart2)
        item['url1'] = url1
        
        days = list()
        chart1 = list()
        chart2 = list()
        chart3 = list()
        chart3.append(item['total_todo'])
        for time in done:
            days.append(time['day'])
            d1 = time['done']
            d1 += chart1[-1] if len(chart1) > 0 else 0
            chart1.append(d1)
            d2 = time['done'] if time['done'] > 0 else time['avg']
            d2 += chart2[-1] if len(chart2) > 0 else 0
            chart2.append(d2)
            chart3.append(item['total_todo'])
        l = [max(chart1), max(chart2), item['total_todo']]
        max2 = max(l)
        
        url2  = 'http://chart.apis.google.com/chart'
        url2 += '?chs=800x350'
        url2 += '&cht=lxy'
        url2 += '&chg=' + str(100.0 / len(days)) + ',0'
        url2 += '&chdl=Progression réelle|Progression estimée'
        url2 += '&chdlp=t'
        url2 += '&chxt=x,y'
        url2 += '&chxl=0:||' + '|'.join('%s' % (str(day)) for day in days)
        url2 += '&chxr=1,0,' + str(max2)
        url2 += '&chds=0,0,0,' + str(max2)
        url2 += '&chco=0000ff,ff0000,000000'
        url2 += '&chls=2,4,2|2,0,0|2,0,0'
        url2 += '&chm=s,ff0000,0,-1,5|N*f0*,000000,0,-1,11|s,0000ff,1,-1,5|N*f0*,ff0000,1,-1,11'
        url2 += '&chf=c,lg,45,ffffff,0,76a4fb,0.75'
        url2 += '&chd=t:-1|0,' + ','.join('%s' % (x) for x in chart1)
        url2 += '|-1|0,' + ','.join('%s' % (y) for y in chart2)
        url2 += '|-1|' + ','.join('%s' % (z) for z in chart3)
        item['url2'] = url2
        
        items.append(item)
    
    return render_to_response('projects/summary.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'items': items, 'date': datetime.datetime.today().strftime('%d/%m'), 'sprint': id, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

#-------------------------------------------------
@login_required
@csrf_protect
def documents(request, project_id):
    project = get_object_or_404(Project, pk = project_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Documents'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/documents'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.save()
            add_log(user, 'document', d, 1)
            messages.append(u'Document ajouté avec succès !')
    else:
        form = DocumentForm(initial={'utilisateur': user.id, 'projet': project.id, })

    if request.method == 'GET':
        if request.GET.__contains__('delete'):
            d = get_object_or_404(Document, pk = request.GET['delete'])
            d.delete()
            if os.path.exists(settings.MEDIA_ROOT + d.fichier.name):
                try:
                    os.remove(settings.MEDIA_ROOT + d.fichier.name)
                except Exception:
                    pass
            add_log(user, 'document', d, 3)

    documents = Document.objects.filter(projet__id__exact = project_id)
    documents = documents.order_by('fichier')

    return render_to_response('projects/documents.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'form': form, 
         'documents': documents, 'project': project, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def scrumwall(request, project_id):
    project = get_object_or_404(Project, pk = project_id)    

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Scrum Wall - Projet "' + unicode(project.titre) + '"'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/scrumwall'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)
    
    sprint = 0
    if request.method == 'GET':
        if request.GET.__contains__('sprint'):
            sprint = int(request.GET['sprint'])

    scrumwall = list()
    features = Feature.objects.filter(projet__id__exact = project_id)
    features = features.order_by('-priorite')
    for f in features:
        items = dict()
        items['id'] = f.id
        items['name'] = f.titre
        items['item'] = f
        todo = Note.objects.filter(feature__id__exact = f.id, etat__exact = 0)
        if sprint != 0:
            todo = todo.filter(sprint__id__exact = sprint)
        todo = todo.order_by('-priorite')
        items['todo'] = todo
        run  = Note.objects.filter(feature__id__exact = f.id, etat__exact = 1)
        if sprint != 0:
            run = run.filter(sprint__id__exact = sprint)
        run  = run.order_by('-priorite')
        items['run'] = run
        done = Note.objects.filter(feature__id__exact = f.id, etat__exact = 2)
        if sprint != 0:
            done = done.filter(sprint__id__exact = sprint)
        done = done.order_by('-priorite')
        items['done'] = done
        if todo.count() + run.count() + done.count() > 0:
            scrumwall.append(items)
    
    sprints = Sprint.objects.filter(projet__id__exact = project_id).order_by('date_debut')

    return render_to_response('projects/scrumwall.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'scrumwall': scrumwall, 
         'project': project, 'sprints': sprints, 'nb_notes': nb_notes, 'taille': nb_notes * 230, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def new_project(request):
    user = request.user.get_profile()
    title = u'Nouveau projet'
    messages = list()
    request.session['url'] = home + 'projects/new'

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            p = form.save()
            add_log(user, 'project', p, 1)
            messages.append(u'Projet ajouté avec succès !')
            request.session['messages'] = messages
            return HttpResponseRedirect(request.session['url'][0:-3])
    else:
        form = ProjectForm(initial={'membres': (1, user.id, ) })

    return render_to_response('projects/project_new.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'form': form, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def new_feature(request, project_id):
    project = get_object_or_404(Project, pk = project_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Nouvelle fonctionnalité'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/features/new'

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = FeatureForm(request.POST)
        if form.is_valid():
            f = form.save()
            add_log(user, 'feature', f, 1)
            messages.append(u'Fonctionnalité ajoutée avec succès !')
            request.session['messages'] = messages
            return HttpResponseRedirect(request.session['url'][0:-3])
    else:
        form = FeatureForm(initial={'utilisateur': user.id, 'projet': project.id, })

    return render_to_response('projects/feature_new.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'form': form, 'project': project, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def new_note(request, project_id, feature_id):
    project = get_object_or_404(Project, pk = project_id)
    feature = get_object_or_404(Feature, pk = feature_id)     

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG    

    user = request.user.get_profile()
    title = u'Nouvelle note de backlog'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/features/' + feature_id + '/notes/new'   

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            n = form.save()
            release = Release.objects.filter(note__id__exact = n.id)
            if release.count() == 0:    
                release = Release()
                release.note = n
                release.status = 0
                release.date_creation = n.date_creation
                release.utilisateur = n.utilisateur
                release.save()
            add_log(user, 'note', n, 1)
            messages.append(u'Note de backlog ajoutée avec succès !')
            request.session['messages'] = messages
            return HttpResponseRedirect(request.session['url'][0:-3])
    else:
        form = NoteForm(initial={'utilisateur': user.id, 'projet': project.id, 'feature': feature.id, })

    return render_to_response('projects/note_new.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'form': form, 'project': project, 'feature': feature, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def new_sprint(request, project_id):
    project = get_object_or_404(Project, pk = project_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Nouveau sprint'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/sprints/new'

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = SprintForm(request.POST)
        if form.is_valid():
            s = form.save()
            add_log(user, 'sprint', s, 1)
            messages.append(u'Sprint ajouté avec succès !')
            request.session['messages'] = messages
            return HttpResponseRedirect(request.session['url'][0:-3])
    else:
        notes = Note.objects.filter(feature__projet__id__exact = project.id, priorite__in = ('0', '2', '3', '4', '5'))
        effort = 0
        for note in notes:
            effort += note.effort
        form = SprintForm(initial={'utilisateur': user.id, 'projet': project.id, 'effort': effort })

    return render_to_response('projects/sprint_new.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'form': form, 'project': project, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def new_task(request, project_id, sprint_id):
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Nouvelle tâche'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/sprints/' + sprint_id + '/tasks/new'

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            t = form.save()
            create_task_days(sprint, t)
            add_log(user, 'task', t, 1)
            messages.append(u'Tâche ajoutée avec succès !')
            request.session['messages'] = messages
            return HttpResponseRedirect(request.session['url'][0:-3])
    else:
        form = TaskForm(initial={'utilisateur': user.id, 'projet': project.id, 'sprint': sprint.id, })

    return render_to_response('projects/task_new.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'form': form, 'project': project, 'sprint': sprint, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def new_problem(request, project_id):
    project = get_object_or_404(Project, pk = project_id)    

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Nouveau problème'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/problems/new'   

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = ProblemForm(request.POST)
        if form.is_valid():
            p = form.save()
            add_log(user, 'problem', p, 1)
            messages.append(u'Problème ajouté avec succès !')
            request.session['messages'] = messages
            return HttpResponseRedirect(request.session['url'][0:-3])
    else:
        form = ProblemForm(initial={'utilisateur': user.id, 'projet': project.id, })

    return render_to_response('projects/problem_new.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'form': form, 'project': project, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@csrf_protect
def new_user(request):
    user = request.user
    title = u'Nouvel utilisateur'
    messages = list()
    request.session['url'] = home + 'projects/user'

    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            u = form.save()
            u.set_password(request.POST['password'])
            u.is_active = True
            u.is_staff = False
            u.is_superuser = False
            u.save()
            messages.append(u'Utilisateur ajouté avec succès !')
            request.session['messages'] = messages
            return HttpResponseRedirect(request.session['url'][0:-4])
    else:
        form = UserForm()

    return render_to_response('projects/user_new.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'form': form, 'project': project, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def add_sprint(request, project_id, feature_id, note_id):
    project = get_object_or_404(Project, pk = project_id)
    feature = get_object_or_404(Feature, pk = feature_id)
    note = get_object_or_404(Note, pk = note_id)

    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG

    user = request.user.get_profile()
    title = u'Nouveau sprint'
    messages = list()
    request.session['url'] = home + 'projects/' + project_id + '/features/' + feature_id + '/notes/' + note_id + '/sprint'

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = SprintForm(request.POST)
        if form.is_valid():
            s = form.save()
            if not note.sprint == s:
                times = NoteTime.objects.filter(note__id__exact = note.id)
                times.delete()
            note.sprint = s
            note.save()
            create_note_days(s, note)
            add_log(user, 'sprint', s, 1)
            add_log(user, 'note', note, 2)
            messages.append(u'Sprint ajouté et associé avec succès !')
            request.session['messages'] = messages
            return HttpResponseRedirect(home + 'projects/' + project_id + '/features/' + feature_id + '/notes/')
    else:
        notes = Note.objects.filter(feature__projet__id__exact = project.id, priorite__in = ('0', '2', '3', '4', '5'))
        effort = 0
        for note in notes:
            effort += note.effort
        form = SprintForm(initial={'utilisateur': user.id, 'projet': project.id, 'effort': effort, })

    return render_to_response('projects/sprint_new.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'form': form, 'project': project, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def logs(request):
    user = request.user.get_profile()
    title = u'Historiques'
    messages = list()
    request.session['url'] = home + 'projects/logs'

    add_history(user, request.session['url'])

    lcount = LogEntry.objects.values('user').annotate(count = Count('id'))
    hcount = History.objects.values('utilisateur').annotate(count = Count('id'))
    
    users = UserProfile.objects.all()
    for u in users:
        setattr(u, 'lcount', 0)
        for l in lcount:
            if l['user'] == u.user.id:
                setattr(u, 'lcount', l['count'])
        setattr(u, 'hcount', 0)
        for h in hcount:
            if h['utilisateur'] == u.user.id:
                setattr(u, 'hcount', h['count'])

    logs = LogEntry.objects.all()
    logs = logs.order_by('-action_time')

    history = History.objects.all()
    history = history.order_by('-date_creation')

    luser = 0
    huser = 0   
    if request.method == 'POST':
        if request.POST.__contains__('lselect'):
            if request.POST['luser'] != '0':
                luser = int(request.POST['luser'])
                logs = logs.filter(user__id__exact = luser)
                logs = logs.order_by('-action_time')
            else:
                logs = LogEntry.objects.all()
                logs = logs.order_by('-action_time')
        if request.POST.__contains__('ldelete'):
            if request.POST['luser'] == '0':
                for l in logs:
                    l.delete()
                messages.append('Logs supprimés avec succès !')
            else:
                luser = int(request.POST['luser'])
                logs = LogEntry.objects.filter(user__id__exact = luser)
                for l in logs:
                    l.delete()
                messages.append('Logs de "%s" supprimés avec succès !' % (UserProfile.objects.get(pk = int(request.POST['luser'])), ))
            logs = LogEntry.objects.all()
            logs = logs.order_by('-action_time')
        if request.POST.__contains__('hselect'):
            if request.POST['huser'] != '0':
                huser = int(request.POST['huser'])
                history = History.objects.filter(utilisateur__id__exact = huser)
                history = history.order_by('-date_creation')
            else:
                history = History.objects.all()
                history = history.order_by('-date_creation')
        if request.POST.__contains__('hdelete'):
            if request.POST['huser'] == '0':
                for h in history:
                    h.delete()
                messages.append('Historiques supprimés avec succès !')
            else:
                huser = int(request.POST['huser'])
                history = History.objects.filter(utilisateur__id__exact = huser)
                for h in history:
                    h.delete()
                messages.append('Historiques de "%s" supprimés avec succès !' % (UserProfile.objects.get(pk = int(request.POST['huser'])), ))
            history = History.objects.all()
            history = history.order_by('-date_creation')

    return render_to_response('projects/logs.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 
         'logs': logs, 'history': history, 'users': users, 'luser': luser, 'huser': huser, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def logs_archives(request):
    user = request.user.get_profile()
    title = u'Archives'
    messages = list()
    request.session['url'] = home + 'projects/logs/archives'

    add_history(user, request.session['url'])

    if request.method == 'POST':
        if request.POST.__contains__('files'):
            for f in request.POST.getlist('files'):
                os.remove(os.path.join(root, 'logs', f))

    path = os.path.join(root, 'logs')
    os.chdir(path)
    files = list()
    for f in os.listdir('.'):
        if f[-4:].lower() == 'html':
            files.append(f)
    files.sort()

    return render_to_response('projects/logs_archives.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'files': files, },
        context_instance = RequestContext(request))