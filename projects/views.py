# -*- coding: utf-8 -*-

import os
import time
import datetime
from xml.dom.minidom import parse

import logging
logging.basicConfig (
    level = logging.DEBUG, 
    format = '%(asctime)s %(levelname)s %(message)s', 
)

from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.models import LogEntry, ContentType
from django.contrib.auth.models import User
from django.template import RequestContext

from scrum import settings
from scrum.projects.models import UserProfile, Project, Feature, Note, Sprint, Task, Problem, Release, Document, NoteTime, TaskTime, History
from scrum.projects.forms import UserForm, ProjectForm, FeatureForm, NoteForm, SprintForm, TaskForm, ProblemForm, DocumentForm

NOT_MEMBER_MSG = u"Accès refusé : l'utilisateur n'est pas membre du projet !"
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
    while d <= sprint.date_fin:
        if d.strftime('%w') not in ('0', '6', ) and d not in holidays:
            time = NoteTime()
            time.sprint = sprint
            time.note = note
            time.jour = d
            time.temps = 0
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
def add_log(user, model_name, model, flag):
    l = LogEntry()
    l.user = user.user
    l.content_type = ContentType.objects.get(app_label = 'projects', model = model_name)
    l.object_id = model.id
    l.object_repr = unicode(model)
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
    date = datetime.date.today()
    date -= datetime.timedelta(1)
    history = History.objects.filter(date_creation__lt = datetime.date.today());
    if history.count() > 0:
        file = open(root + 'logs' + os.sep + 'log-' + date.strftime("%Y%m%d") + ".html", 'w')
        file.write('<html><head><title>Historiques du %s</title></head><body><h1>Historiques du %s</h1><br />' 
            % (date.strftime('%d/%m/%Y'), date.strftime('%d/%m/%Y'), ));
        file.write('<table><thead><tr><th width="100">Heure</th><th width="200">Utilisateur</th><th>URL</th></tr></thead><tbody>')
        history = history.order_by('date_creation')
        for h in history:
            file.write('<tr><td>%s</td><td>%s</td><td><a href="http://%s">%s</a></td></tr>' 
                % (h.date_creation.strftime('%H:%m:%S'), h.utilisateur, settings.DEFAULT_URL + h.url, h.url, ))
            h.delete()
        file.write('</table></body></html>')
        file.close()

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
        sprint = Sprint.objects.filter(projet__id__exact = t.id, 
            date_debut__lte = datetime.date.today(), date_fin__gte = datetime.date.today())
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
def list_features(project_id, sort = '-priorite', todo = True, tab = True, max = 0, target = None, nb_notes = NOTES_PAR_LIGNE):
    tmp = Feature.objects.filter(projet__id__exact = project_id)
    
    if sort:
        tmp = tmp.order_by(sort)
    if todo:
        tmp = tmp.exclude(termine__exact = 1)
    
    if not tab:
        if not max == 0:
            return tmp[:max]
        else:
            return tmp
    
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
def list_notes(feature_id, sort = '-priorite', todo = True, toset = False, tab = True, max = 0, target = None, nb_notes = NOTES_PAR_LIGNE):
    tmp = Note.objects.filter(feature__id__exact = feature_id)
    
    if sort:
        tmp = tmp.order_by(sort)
    if todo:
        tmp = tmp.exclude(etat__exact = 2)
    if toset:
        tmp = tmp.exclude(sprint__id__isnull = False)
    
    if not tab:
        if not max == 0:
            return tmp[:max]
        else:
            return tmp
    
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
def list_sprints(project_id, sort = '-date_debut', todo = True, tab = True, max = 0, target = None, nb_notes = NOTES_PAR_LIGNE):
    tmp = Sprint.objects.filter(projet__id__exact = project_id)
    
    if sort:
        tmp = tmp.order_by(sort)
    if todo:
        tmp = tmp.exclude(date_fin__lt = datetime.date.today())
    
    if not tab:
        if not max == 0:
            return tmp[:max]
        else:
            return tmp
    
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
def list_snotes(sprint_id, sort = '-priorite', todo = True, tab = True, max = 0, target = None, nb_notes = NOTES_PAR_LIGNE):
    tmp = Note.objects.filter(sprint__id__exact = sprint_id)
    
    if sort:
        tmp = tmp.order_by(sort)
    if todo:
        tmp = tmp.exclude(etat__exact = 2)
    
    if not tab:
        if not max == 0:
            return tmp[:max]
        else:
            return tmp
    
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
def list_tasks(sprint_id, sort = '-priorite', todo = True, tab = True, max = 0, target = None, nb_notes = NOTES_PAR_LIGNE):
    tmp = Task.objects.filter(sprint__id__exact = sprint_id)
    
    if sort:
        tmp = tmp.order_by(sort)
    if todo:
        tmp = tmp.exclude(etat__exact = 2)
    
    if not tab:
        if not max == 0:
            return tmp[:max]
        else:
            return tmp
    
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
def list_problems(project_id, sort = '-priorite', todo = True, tab = True, max = 0, target = None, nb_notes = NOTES_PAR_LIGNE):
    tmp = Problem.objects.filter(projet__id__exact = project_id)
    
    if sort:
        tmp = tmp.order_by(sort)
    if todo:
        tmp = tmp.exclude(resolu__exact = 1)
    
    if not tab:
        if not max == 0:
            return tmp[:max]
        else:
            return tmp
    
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
def list_releases(sprint_id):
    notes = Note.objects.filter(sprint__id__exact = sprint_id).exclude(etat__exact = 2)
    notes = notes.order_by('-priorite')
    for n in notes:
        release = Release.objects.filter(note__id__exact = n.id)
        if release.count() == 0:    
            release = Release()
            release.note = n
            release.status = 0
            release.date_creation = n.date_creation
            release.utilisateur = n.utilisateur
            release.save()
    releases = list()
    
    for n in notes:
        release = Release.objects.filter(note__id__exact = n.id)
        release = release.order_by('-date_creation')[0]
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
    
    return render_to_response('projects/projects.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 
         'projects': projects, 'nb_notes': nb_notes, })

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
    
    features = list_features(project_id, tab = True, max = nb_notes, nb_notes = nb_notes)
    sprints = list_sprints(project_id, tab = True, max = nb_notes, nb_notes = nb_notes)
    problems = list_problems(project_id, tab = True, max = nb_notes, nb_notes = nb_notes)
    
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

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'POST':
        if request.POST.__contains__('id'):
            feature = Feature.objects.get(pk = int(request.POST['id']))
            if request.POST.__contains__('priorite'):
                feature.priorite = int(request.POST['priorite'])
            if request.POST.__contains__('termine'):
                feature.termine = True
            else:
                feature.termine = False
            feature.utilisateur = user
            feature.save()
            add_log(user, 'feature', feature, 2)
            messages.append(u'Fonctionnalité modifiée avec succès !')
    
    if request.method == 'GET':
        if request.GET.__contains__('d'):
            feature = Feature.objects.get(pk = int(request.GET['d']))
            feature.confiance_dev = int(feature.confiance_dev) +1
            if int(feature.confiance_dev) > 3:
                feature.confiance_dev = '0'
            feature.save()
        if request.GET.__contains__('s'):
            feature = Feature.objects.get(pk = int(request.GET['s']))
            feature.confiance_sm = int(feature.confiance_sm) +1
            if int(feature.confiance_sm) > 3:
                feature.confiance_sm = '0'
            feature.save()
        if request.GET.__contains__('p'):
            feature = Feature.objects.get(pk = int(request.GET['p']))
            feature.confiance_po = int(feature.confiance_po) +1
            if int(feature.confiance_po) > 3:
                feature.confiance_po = '0'
            feature.save()
    
    sort = '-priorite'
    todo = False
    target = None
    if request.method == 'GET':
        if request.GET.__contains__('sort'):
            sort = request.GET['sort']
        if request.GET.__contains__('todo'):
            todo = True
        if request.GET.__contains__('target'):
            target = int(request.GET['target'])
    
    features = list_features(project_id, sort = sort, todo = todo, tab = True, max = 0, target = target, nb_notes = nb_notes)
    
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
    
    notes = list_notes(feature_id, tab = True, max = nb_notes, nb_notes = nb_notes)
    
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
    
    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'POST':
        if request.POST.__contains__('id'):
            note = Note.objects.get(pk = int(request.POST['id']))
            if request.POST.__contains__('priorite'):
                note.priorite = int(request.POST['priorite'])
            if request.POST.__contains__('sprint'):
                if request.POST['sprint'] == '':
                    note.temps_realise = 0
                    note.sprint = None
                    times = NoteTime.objects.filter(note__id__exact = note.id)
                    times.delete()
                else:
                    sprint = Sprint.objects.get(pk = int(request.POST['sprint']))
                    if not note.sprint == sprint:
                        note.temps_realise = 0
                        times = NoteTime.objects.filter(note__id__exact = note.id)
                        times.delete()
                        create_note_days(sprint, note)
                    note.sprint = sprint
            if request.POST.__contains__('temps'):
                note.temps_estime = int(request.POST['temps'])
            note.utilisateur = user
            note.save()
            add_log(user, 'note', note, 2)
            messages.append(u'Note de backlog modifiée avec succès !')
    if request.method == 'GET':
        if request.GET.__contains__('d'):
            note = Note.objects.get(pk = int(request.GET['d']))
            note.confiance_dev = int(note.confiance_dev) +1
            if int(note.confiance_dev) > 3:
                note.confiance_dev = '0'
            note.save()
        if request.GET.__contains__('s'):
            note = Note.objects.get(pk = int(request.GET['s']))
            note.confiance_sm = int(note.confiance_sm) +1
            if int(note.confiance_sm) > 3:
                note.confiance_sm = '0'
            note.save()
        if request.GET.__contains__('p'):
            note = Note.objects.get(pk = int(request.GET['p']))
            note.confiance_po = int(note.confiance_po) +1
            if int(note.confiance_po) > 3:
                note.confiance_po = '0'
            note.save()
    
    sort = '-priorite'
    todo = False
    toset = False
    target = None
    if request.method == 'GET':
        if request.GET.__contains__('sort'):
            sort = request.GET['sort']
        if request.GET.__contains__('todo'):
            todo = True
        if request.GET.__contains__('toset'):
            toset = True
        if request.GET.__contains__('target'):
            target = int(request.GET['target'])
    
    notes = list_notes(feature_id, sort = sort, todo = todo, toset = toset, tab = True, max = 0, target = target, nb_notes = nb_notes)
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
    
    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'GET':
        if request.GET.__contains__('d'):
            sprint = Sprint.objects.get(pk = int(request.GET['d']))
            sprint.confiance_dev = int(sprint.confiance_dev) +1
            if int(sprint.confiance_dev) > 3:
                sprint.confiance_dev = '0'
            sprint.save()
        if request.GET.__contains__('s'):
            sprint = Sprint.objects.get(pk = int(request.GET['s']))
            sprint.confiance_sm = int(sprint.confiance_sm) +1
            if int(sprint.confiance_sm) > 3:
                sprint.confiance_sm = '0'
            sprint.save()
        if request.GET.__contains__('p'):
            sprint = Sprint.objects.get(pk = int(request.GET['p']))
            sprint.confiance_po = int(sprint.confiance_po) +1
            if int(sprint.confiance_po) > 3:
                sprint.confiance_po = '0'
            sprint.save()
    if request.method == 'POST' and request.POST.__contains__('id'):
        import time
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
        add_log(user, 'sprint', sprint, 2)
    
    sort = '-date_debut'
    todo = False
    target = None
    if request.method == 'GET':
        if request.GET.__contains__('sort'):
            sort = request.GET['sort']
        if request.GET.__contains__('todo'):
            todo = True
        if request.GET.__contains__('target'):
            target = int(request.GET['target'])
    
    sprints = list_sprints(project_id, sort = sort, todo = todo, tab = True, max = 0, target = target, nb_notes = nb_notes)
    
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
    
    notes = list_snotes(sprint_id, tab = True, max = nb_notes, nb_notes = nb_notes)
    tasks = list_tasks(sprint_id, tab = True, max = nb_notes, nb_notes = nb_notes)
    
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
        if request.GET.__contains__('d'):
            note = Note.objects.get(pk = int(request.GET['d']))
            note.confiance_dev = int(note.confiance_dev) +1
            if int(note.confiance_dev) > 3:
                note.confiance_dev = '0'
            note.save()
        if request.GET.__contains__('s'):
            note = Note.objects.get(pk = int(request.GET['s']))
            note.confiance_sm = int(note.confiance_sm) +1
            if int(note.confiance_sm) > 3:
                note.confiance_sm = '0'
            note.save()
        if request.GET.__contains__('p'):
            note = Note.objects.get(pk = int(request.GET['p']))
            note.confiance_po = int(note.confiance_po) +1
            if int(note.confiance_po) > 3:
                note.confiance_po = '0'
            note.save()   
    
    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'POST':
        if request.POST.__contains__('id'):
            note = Note.objects.get(pk = int(request.POST['id']))
            if request.POST.__contains__('priorite'):
                note.priorite = int(request.POST['priorite'])
            if request.POST.__contains__('etat'):
                note.etat = int(request.POST['etat'])
                if note.etat != 2:
                    nts = NoteTime.objects.filter(note__in = (note, ))
                    for nt in nts:
                        nt.temps_fin = 0
                        nt.save();
            note.utilisateur = user
            note.save()
            add_log(user, 'note', note, 2)
            messages.append(u'Note de sprint modifiée avec succès !')
    
    sort = '-priorite'
    todo = False
    target = None
    if request.method == 'GET':
        if request.GET.__contains__('sort'):
            sort = request.GET['sort']
        if request.GET.__contains__('todo'):
            todo = True
        if request.GET.__contains__('target'):
            target = int(request.GET['target'])
    
    notes = list_snotes(sprint_id, sort = sort, todo = todo, tab = True, max = 0, target = target, nb_notes = nb_notes)
    
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
        if request.GET.__contains__('d'):
            task = Task.objects.get(pk = int(request.GET['d']))
            task.confiance_dev = int(task.confiance_dev) +1
            if int(task.confiance_dev) > 3:
                task.confiance_dev = '0'
            task.save()
        if request.GET.__contains__('s'):
            task = Task.objects.get(pk = int(request.GET['s']))
            task.confiance_sm = int(task.confiance_sm) +1
            if int(task.confiance_sm) > 3:
                task.confiance_sm = '0'
            task.save()
        if request.GET.__contains__('p'):
            task = Task.objects.get(pk = int(request.GET['p']))
            task.confiance_po = int(task.confiance_po) +1
            if int(task.confiance_po) > 3:
                task.confiance_po = '0'
            task.save() 
    
    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'POST':
        if request.POST.__contains__('id'):
            task = Task.objects.get(pk = int(request.POST['id']))
            if request.POST.__contains__('priorite'):
                task.priorite = int(request.POST['priorite'])
            if request.POST.__contains__('etat'):
                task.etat = int(request.POST['etat'])
                if task.etat != 2:
                    tts = TaskTime.objects.filter(task__in = (task, ))
                    for tt in tts:
                        tt.temps_fin = 0
                        tt.save();
            if request.POST.__contains__('temps'):
                task.temps_estime = int(request.POST['temps'])
            task.utilisateur = user
            task.save()
            add_log(user, 'task', task, 2)
            messages.append(u'Tâche modifiée avec succès !')
    
    sort = '-priorite'
    todo = False
    target = None
    if request.method == 'GET':
        if request.GET.__contains__('sort'):
            sort = request.GET['sort']
        if request.GET.__contains__('todo'):
            todo = True
        if request.GET.__contains__('target'):
            target = int(request.GET['target'])
    
    tasks = list_tasks(sprint_id, sort = sort, todo = todo, tab = True, max = 0, target = target, nb_notes = nb_notes)
    
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
    
    if request.method == 'POST':
        if request.POST.__contains__('id'):
            id = request.POST['id']
            note = Note.objects.get(pk = id)
            release = Release()
            release.note = note
            release.utilisateur = user
            if request.POST.__contains__('livrer'):
                release.status = 1
                release.save()
            elif request.POST.__contains__('refuser'):
                release.status = 2
                release.save()
            elif request.POST.__contains__('valider'):
                release.status = 3
                release.save()
            elif request.POST.__contains__('terminer'):
                note.etat = 2
                note.save()
    note = None
    details = list()
    if request.method == 'GET':
        if request.GET.__contains__('id'):
            note = int(request.GET['id'])
            details = Release.objects.filter(note__id__exact = note)
            details = details.order_by('date_creation')
    
    
    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)
    
    releases = list_releases(sprint_id)
    
    return render_to_response('projects/releases.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'sprint': sprint, 'releases': releases, 'note': note, 'details': details, 'nb_notes': nb_notes, },
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
        if request.GET.__contains__('d'):
            problem = Problem.objects.get(pk = int(request.GET['d']))
            problem.confiance_dev = int(problem.confiance_dev) +1
            if int(problem.confiance_dev) > 3:
                problem.confiance_dev = '0'
            problem.save()
        if request.GET.__contains__('s'):
            problem = Problem.objects.get(pk = int(request.GET['s']))
            problem.confiance_sm = int(problem.confiance_sm) +1
            if int(problem.confiance_sm) > 3:
                problem.confiance_sm = '0'
            problem.save()
        if request.GET.__contains__('p'):
            problem = Problem.objects.get(pk = int(request.GET['p']))
            problem.confiance_po = int(problem.confiance_po) +1
            if int(problem.confiance_po) > 3:
                problem.confiance_po = '0'
            problem.save()    
    
    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'POST':
        if request.POST.__contains__('id'):
            problem = Problem.objects.get(pk = int(request.POST['id']))
            if request.POST.__contains__('priorite'):
                problem.priorite = int(request.POST['priorite'])
            if request.POST.__contains__('resolu'):
                problem.resolu = True
            else:
                problem.resolu = False
            problem.utilisateur = user
            problem.save()
            add_log(user, 'problem', problem, 2)
            messages.append(u'Problème modifié avec succès !')
    
    sort = '-priorite'
    todo = False
    target = None
    if request.method == 'GET':
        if request.GET.__contains__('sort'):
            sort = request.GET['sort']
        if request.GET.__contains__('todo'):
            todo = True
        if request.GET.__contains__('target'):
            target = int(request.GET['target'])
    
    problems = list_problems(project_id, sort = sort, todo = todo, tab = True, max = 0, target = target, nb_notes = nb_notes)
    
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
    lock = sprint.date_modification.isoformat(' ')
    
    if request.user.get_profile() not in project.membres.all():
        raise Exception, NOT_MEMBER_MSG
    
    user = request.user.get_profile()
    title = u'Burndown Chart - Sprint "' + unicode(sprint.titre) + '"'
    messages = list()
    erreur = ''
    request.session['url'] = home + 'projects/' + project_id + '/sprints/' + sprint_id + '/burndown'
    
    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'POST':
        if request.POST['lock'] == lock:
            for id in request.POST:
                if id[0:4] == 'Note':
                    time = NoteTime.objects.get(pk = int(id[4:]))
                    note = time.note
                    if (time.temps != int(request.POST[id])):
                        note.etat = 1
                        time.date_modification = datetime.datetime.now()
                        time.utilisateur = user
                    note.temps_realise = note.temps_realise - time.temps
                    time.temps = int(request.POST[id])
                    note.temps_realise = note.temps_realise + time.temps
                    note.save()
                    time.save()
                elif id[0:5] == 'Tache':
                    time = TaskTime.objects.get(pk = int(id[5:]))
                    task = time.task
                    if (time.temps != int(request.POST[id])):
                        task.etat = 1
                        time.date_modification = datetime.datetime.now()
                        time.utilisateur = user
                    task.temps_realise = task.temps_realise - time.temps
                    time.temps = int(request.POST[id])
                    task.temps_realise = task.temps_realise + time.temps
                    task.save()
                    time.save()
                elif id[0:5] == '_Note':
                    note = Note.objects.get(pk = int(id[5:]))
                    nts = NoteTime.objects.filter(note__in = (note, ))
                    nts = nts.order_by('-jour')
                    for nt in nts:
                        if nt.temps > 0:
                            fin = nt.note.temps_estime - nt.note.temps_realise
                            if fin >= 0:
                                nt.temps_fin = fin
                                nt.save()
                            break
                    note.etat = 2
                    note.save()
                    add_log(user, 'note', note, 2)
                elif id[0:6] == '_Tache':
                    task = Task.objects.get(pk = int(id[6:]))
                    tts = TaskTime.objects.filter(task__in = (task, ))
                    tts = tts.order_by('-jour')
                    for tt in tts:
                        if tt.temps > 0:
                            fin = tt.task.temps_estime - tt.task.temps_realise
                            if fin >= 0:
                                tt.temps_fin = fin
                                tt.save()
                            break
                    task.etat = 2
                    task.save()
                    add_log(user, 'task', task, 2)
                sprint.date_modification = datetime.datetime.now()
                sprint.save()
        else:
            erreur = u'Les informations ont été modifiées pendant votre saisie !'
    
    holidays = get_holidays(datetime.date.today().year)
    
    times = list()
    
    notes = Note.objects.filter(sprint__id__exact = sprint_id)
    notes = notes.order_by('-priorite')
    
    if not request.method == 'GET' or not request.GET.__contains__('done'):
        notes = notes.exclude(etat__exact = 2)
    
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
        d['url'] = 'notes'
        times.append(d)
    
    tasks = Task.objects.filter(sprint__id__exact = sprint_id)
    tasks = tasks.order_by('-priorite')
    
    if not request.method == 'GET' or not request.GET.__contains__('done'):
        tasks = tasks.exclude(etat__exact = 2)
    
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
        d['url'] = 'tasks'
        times.append(d)
    
    notes = Note.objects.filter(sprint__id__exact = sprint_id)
    tasks = Task.objects.filter(sprint__id__exact = sprint_id)
    
    total = 0
    for n in notes:
        total += n.temps_estime
    for t in tasks:
        total += t.temps_estime
    
    days = NoteTime.objects.filter(sprint__id__exact = sprint_id).values_list('jour', flat=True).distinct()
    days = days.exclude(jour__in = holidays)
    days = days.order_by('jour')
    if (days.count() == 0):
        days = TaskTime.objects.filter(sprint__id__exact = sprint_id).values_list('jour', flat=True).distinct()
        days = days.exclude(jour__in = holidays)
        days = days.order_by('jour')
    
    min = 0
    data1 = list()
    tmp = total
    data1.append(tmp)
    for day in days:
        nts = NoteTime.objects.filter(sprint__id__exact = sprint.id, jour__exact = day)
        tts = TaskTime.objects.filter(sprint__id__exact = sprint.id, jour__exact = day)
        for t in nts:
            tmp -= t.temps + t.temps_fin
        for t in tts:
            tmp -= t.temps + t.temps_fin
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
    url += '&chdl=Temps restant|Temps estimé'
    url += '&chdlp=b'
    url += '&chxt=x,y'
    url += '&chxl=0:||' + '|'.join('%s' % (d.strftime('%d/%m')) for d in days)
    url += '&chxr=1,' + str(min) + ',' + str(total)
    url += '&chds=0,0,' + str(min) + ',' + str(total)
    url += '&chco=0000ff,ff0000,00aaaa'
    url += '&chls=2,4,1'
    url += '&chm=s,ff0000,0,-1,5|N*f0*,000000,0,-1,11|s,0000ff,1,-1,5|s,00aa00,2,-1,5'
    url += '&chf=c,lg,45,ffffff,0,76a4fb,0.75'
    url += '&chd=t:-1|' + ','.join('%s' % (x) for x in data1)
    url += '|-1|' + ','.join('%s' % (y) for y in data2)
    
    return render_to_response('projects/burndown.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'sprint': sprint, 'days': days, 'times': times, 'lock': lock,
         'url': url, 'date': datetime.date.today(), 'erreur': erreur, 'nb_notes': nb_notes, },
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
    
    max = 0
    for i in range(sprints.count()):
        n = 0
        for j in range(4):
            n += data[j][i]
        if n > max:
            max = n
    
    url1  = 'http://chart.apis.google.com/chart'
    url1 += '?chs=800x350'
    url1 += '&cht=bvs'
    url1 += '&chbh=a'
    url1 += '&chdl=User-story|Feature|Bug|Spike'
    url1 += '&chdlp=t'
    url1 += '&chxt=x,y'
    url1 += '&chxl=0:|' + '|'.join('%s' % (str(s.titre)) for s in sprints)
    url1 += '&chxr=1,0,' + str(max)
    url1 += '&chds=0,' + str(max)
    url1 += '&chco=ccffcc,ffffcc,ffcc99,cecaff'
    url1 += '&chm=N,ff0000,-1,,12,,e::11|N,000000,0,,11,,c|N,000000,1,,11,,c|N,000000,2,,10,,c|N,000000,3,,11,,c'
    url1 += '&chf=c,lg,45,ffffff,0,76a4fb,0.75'
    url1 += '&chd=t:' + '|'.join('%s' % (','.join('%s' % (v) for v in values)) for values in data)
    
    first = True
    cumul = 0
    max = 0
    charge1 = list()
    charge2 = list()
    for sprint in sprints:
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
        if sprint.effort > max:
            max = sprint.effort
    
    url2  = 'http://chart.apis.google.com/chart'
    url2 += '?chs=800x350'
    url2 += '&cht=lxy'
    url2 += '&chdl=Charge terminée|Charge totale'
    url2 += '&chdlp=t'
    url2 += '&chxt=x,y'
    url2 += '&chxl=0:||' + '|'.join('%s' % (str(s.titre)) for s in sprints)
    url2 += '&chxr=1,0,' + str(max)
    url2 += '&chds=0,0,0,' + str(max)
    url2 += '&chco=0000ff,ff0000,00aaaa'
    url2 += '&chls=2,4,1'
    url2 += '&chm=s,ff0000,0,-1,5|N*f0*,000000,0,-1,11|s,0000ff,1,-1,5|N*f0*,000000,1,-1,11|s,00aa00,2,-1,5'
    url2 += '&chf=c,lg,45,ffffff,0,76a4fb,0.75'
    url2 += '&chd=t:-1|0,' + ','.join('%s' % (x) for x in charge1)
    url2 += '|-1|' + ','.join('%s' % (y) for y in charge2)
    
    return render_to_response('projects/velocity.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'url1': url1, 'url2': url2, 'nb_notes': nb_notes, },
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

    scrumwall = list()
    features = Feature.objects.filter(projet__id__exact = project_id)
    features = features.order_by('-priorite')
    for f in features:
        items = dict()
        items['id'] = f.id
        items['name'] = f.titre
        items['item'] = f
        todo = Note.objects.filter(feature__id__exact = f.id, etat__exact = 0)
        todo = todo.order_by('-priorite')
        items['todo'] = todo
        run  = Note.objects.filter(feature__id__exact = f.id, etat__exact = 1)
        run  = run.order_by('-priorite')
        items['run'] = run
        done = Note.objects.filter(feature__id__exact = f.id, etat__exact = 2)
        done = done.order_by('-priorite')
        items['done'] = done
        scrumwall.append(items)
    
    return render_to_response('projects/scrumwall.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'scrumwall': scrumwall, 
         'project': project, 'nb_notes': nb_notes, 'taille': nb_notes * 230, },
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
            u.is_staff = True
            u.is_active = True
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

    users = UserProfile.objects.all()
    
    logs = LogEntry.objects.all()
    logs = logs.order_by('-action_time')
    
    history = History.objects.all()
    history = history.order_by('-date_creation')
    
    if request.method == 'POST':
        if request.POST.__contains__('lselect'):
            if request.POST['luser'] != '0':
                logs = logs.filter(user__id__exact = int(request.POST['luser']))
                logs = logs.order_by('-action_time')
            else:
                logs = LogEntry.objects.all()
                logs = logs.order_by('-action_time')
        if request.POST.__contains__('ldelete'):
            if request.POST['luser'] == '0':
                for log in logs:
                    log.delete()
                messages.append('Logs supprimés avec succès !')
            else:
                temp = LogEntry.objects.filter(user__id__exact = int(request.POST['luser']))
                for log in temp:
                    log.delete()
                messages.append('Logs de "%s" supprimés avec succès !' % (UserProfile.objects.get(pk = int(request.POST['luser'])), ))
            logs = LogEntry.objects.all()
            logs = logs.order_by('-action_time')
        if request.POST.__contains__('hselect'):
            if request.POST['huser'] != '0':
                history = History.objects.filter(utilisateur__id__exact = int(request.POST['huser']))
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
                temp = History.objects.filter(utilisateur__id__exact = int(request.POST['huser']))
                for h in temp:
                    h.delete()
                messages.append('Historiques de "%s" supprimés avec succès !' % (UserProfile.objects.get(pk = int(request.POST['huser'])), ))
            history = History.objects.all()
            history = history.order_by('-date_creation')
    
    return render_to_response('projects/logs.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'logs': logs, 'history': history, 'users': users, },
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
    
    return render_to_response('projects/logs_archives.html',
        {'home': home, 'theme': theme, 'user': user, 'title': title, 'messages': messages, 'files': files, },
        context_instance = RequestContext(request))
