# -*- coding: utf-8 -*-

import os
import codecs
import datetime
from xml.dom.minidom import parse

import logging
logging.basicConfig (
    level = logging.INFO, 
    format = '(%(asctime)s) [%(levelname)s] :\n%(message)s\n', 
)

from django.db.models import Count, Sum, Avg
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.admin.models import LogEntry, ContentType
from django.contrib.auth.models import User
from django.template import RequestContext, Context, loader
from django.utils.translation import ugettext as _

try: # Asynchronous send_mail
    from scrum.projects import send_mail
except: # Build-in send_mail
    from django.core.mail import send_mail 

from scrum import settings
from scrum.projects.models import UserProfile, Project, Feature, Note, Sprint, Task, Problem, Release, Meteo, Poker, Document, NoteTime, TaskTime, History
from scrum.projects.models import ETATS, PRIORITES, TYPES, STATUTS, EFFORTS, CONFIANCE, METEO
from scrum.projects.forms import UserForm, ProjectForm, FeatureForm, NoteForm, SprintForm, TaskForm, ProblemForm, DocumentForm

ERREUR_TITRE = _(u"Accès refusé !")
ERREUR_TEXTE = _(u"L'utilisateur n'est pas membre du projet ou ne dispose pas d'autorisations suffisantes pour visualiser cet élément.")
NOTES_PAR_LIGNE = 5

ROOT = settings.DEFAULT_DIR
HOME = settings.DEFAULT_HOME
THEME = settings.MEDIA_URL

# ------------------------------------------------
import unicodedata
def remove_accents(string):
    if isinstance(string, str):
        s = unicode(s, 'utf8', 'replace')
    s = unicodedata.normalize('NFD', string)
    return s.encode('ascii', 'ignore')

# ------------------------------------------------
def check_rights(user, project, *objects):
    previous = None
    valid = True
    if user not in project.membres.all():
        valid = False
    for o in objects:
        if hasattr(o, 'projet') and o.projet != project:
            valid = False
        elif hasattr(o, 'feature') and o.feature != previous:
            valid = False
        elif hasattr(o, 'sprint') and o.sprint != previous:
            valid = False
        previous = o
    return valid

# ------------------------------------------------
def recalc_effort(project):
    effort = 0
    sprint = Sprint.objects.select_related().filter(projet__id__exact = project.id).order_by('-date_debut')
    if sprint:
        notes = Note.objects.filter(feature__projet__id__exact = project.id, priorite__in = ('0', '2', '3', '4', '5'))
        for note in notes:
            effort += note.effort
        sprint = sprint[0]
        if sprint.date_fin > datetime.date.today():
            sprint.effort = effort
            sprint.save()
    return effort

# ------------------------------------------------
def get_nb_notes(request):
    if request.method == 'POST' and request.POST.__contains__('nb_notes'):
        request.session['nb_notes'] = request.POST['nb_notes']
    if request.session.__contains__('nb_notes'):
        return int(request.session['nb_notes'])
    else:
        return NOTES_PAR_LIGNE

# ------------------------------------------------
def get_holidays(year1, year2 = None):
    import time
    holidays = list()
    if (os.path.exists(ROOT + str(year1) + '.xml')):
        dom = parse(ROOT + str(year1) + '.xml')
        for node in dom.getElementsByTagName('day'):
            day = time.strptime(node.firstChild.nodeValue, "%Y-%m-%d")
            holidays.append(datetime.date(day[0], day[1], day[2]))
    if year2 != None and year1 != year2:
        if (os.path.exists(ROOT + str(year2) + '.xml')):
            dom = parse(ROOT + str(year2) + '.xml')
            for node in dom.getElementsByTagName('day'):
                day = time.strptime(node.firstChild.nodeValue, "%Y-%m-%d")
                holidays.append(datetime.date(day[0], day[1], day[2]))
    return holidays

# ------------------------------------------------
def create_note_days(sprint, note):
    holidays = get_holidays(sprint.date_debut.year, sprint.date_fin.year)
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
    holidays = get_holidays(sprint.date_debut.year, sprint.date_fin.year)
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
def write_logs(archive_history = False, archive_logs = False):
    file = False
    date = datetime.date.today()
    if archive_history:
        history = History.objects.filter(date_creation__lt = datetime.date.today() - datetime.timedelta(settings.ARCHIVE_DAYS)).order_by('date_creation');
        for h in history:
            current = h.date_creation.date()
            path1 = ROOT + 'logs' + os.sep + 'urls-' + current.strftime('%Y%m%d') + '.html'
            path2 = ROOT + 'logs' + os.sep + 'urls-' + date.strftime('%Y%m%d') + '.html'
            if date != current and os.path.exists(path2):
                file = codecs.open(path2, mode='a', encoding='utf-8')
                file.write(u'</tbody></table></body></html>')
                file.close()
            if not os.path.exists(path1):
                file = codecs.open(path1, mode='w', encoding='utf-8')
                file.write(u'<html><head><meta http-equiv="content-type" content="text/html; charset=utf-8" /><title>%s (%s)</title><style>* { font-family: "Verdana"; } th { text-align: left; }</style></head><body><h1>%s (%s)</h1><br />' % 
                    (_(u'Historiques de navigation'), current.strftime(_('%d/%m/%Y')), _(u'Historiques de navigation'), current.strftime(_('%d/%m/%Y')), ));
                file.write(u'<table><thead><tr><th width="100">%s</th><th width="400">%s</th><th>%s</th></tr></thead><tbody>' % (_(u'Heure'), _(u'Utilisateur'), _(u'URL'), ))
            else:
                file = codecs.open(path1, mode='a', encoding='utf-8')
            file.write(u'<tr><td>%s</td><td>%s %s (%s)</td><td><a href="http://%s">%s</a></td></tr>' 
                       % (h.date_creation.strftime('%H:%m:%S'), h.utilisateur.user.first_name, h.utilisateur.user.last_name, h.utilisateur.user.username, settings.DEFAULT_URL + h.url, h.url, ))
            file.close()
            h.delete()
            date = current 
        file = False
    date = datetime.date.today()
    actions = [u'', _(u'Ajout'), _(u'Modification'), _(u'Suppression')]
    if archive_logs:
        logs = LogEntry.objects.filter(action_time__lt = datetime.date.today() - datetime.timedelta(7)).order_by('action_time')
        for l in logs:
            current = l.action_time.date()
            path1 = ROOT + 'logs' + os.sep + 'logs-' + l.action_time.strftime('%Y%m%d') + '.html'
            path2 = ROOT + 'logs' + os.sep + 'logs-' + date.strftime('%Y%m%d') + '.html'
            if date != current and os.path.exists(path2):
                file = codecs.open(path2, mode='a', encoding='utf-8')
                file.write(u'</tbody></table></body></html>')
                file.close()
            if not os.path.exists(path1):
                file = codecs.open(path1, mode='w', encoding='utf-8')
                file.write(u'<html><head><meta http-equiv="content-type" content="text/html; charset=utf-8" /><title>%s (%s)</title><style>* { font-family: "Verdana"; } th { text-align: left; }</style></head><body><h1>%s (%s)</h1><br />' % 
                    (_(u'Historiques de gestion'), current.strftime(_('%d/%m/%Y')), _(u'Historiques de gestion'), current.strftime(_('%d/%m/%Y')), ))
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
        t.target = True if target != None and target == t.id else False

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
        tmp = tmp.exclude(etat__exact = '4') if todo else tmp.filter(etat__exact = '4')
        tmp = tmp.exclude(sprint__id__isnull = False) if toset else tmp.filter(sprint__id__isnull = False)

    notes = list()
    notes.append(list())
    i = 1
    j = 0
    n = 0
    for t in tmp:
        t.target = True if target != None and target == t.id else False

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
        t.target = True if target != None and target == t.id else False

        nb = 0
        t.notes = 0
        t.temps_realise = 0
        t.temps_estime = 0
        ns = Note.objects.select_related().filter(sprint__id__exact = t.id)
        for nt in ns:
            t.notes += 1
            nb += 1 if nt.etat not in ('3', '4') else 0
            t.temps_realise += min(nt.temps_realise, nt.temps_estime) if nt.etat not in ('3', '4') else nt.temps_estime
            t.temps_estime += nt.temps_estime
        ts = Task.objects.select_related().filter(sprint__id__exact = t.id)
        for tt in ts:
            t.notes += 1
            nb += 1 if nt.etat not in ('3', '4') else 0
            t.temps_realise += min(tt.temps_realise, tt.temps_estime) if tt.etat not in ('3', '4') else tt.temps_estime
            t.temps_estime += tt.temps_estime
        
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

        value1 = 1 if t.etat == 'done' else 1.0 * t.temps_realise / t.temps_estime if t.temps_estime > 0 else 0

        holidays = get_holidays(t.date_debut.year, t.date_fin.year)

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

        value2 = ((datetime.date.today() - t.date_debut).days - nbd1 + 1) / float((t.date_fin - t.date_debut).days - nbd2 + 1)

        url  = u'http://chart.apis.google.com/chart'
        url += u'?cht=bhg'
        url += u'&chs=200x100'
        url += u'&chds=0,1'
        url += u'&chl=0%|100%'
        url += u'&chdl=%s|%s' % (_(u'Réalisé'), _(u'Théorique'), )
        url += u'&chdlp=b'
        url += u'&chm=N*p0*,000000,-1,-1,11'
        url += u'&chd=t:%f,%f' % (value1, value2, )
        url += u'&chco=4d89f9|c6d9fd'
        url += u'&chbh=20'
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
        tmp = tmp.filter(etat__in = ('0', '1')) if todo else tmp.filter(etat__in = ('2', '3')) if work else tmp.filter(etat__exact = '4')

    notes = list()
    notes.append(list())
    i = 1
    j = 0
    n = 0
    for t in tmp:
        t.target = True if target != None and target == t.id else False

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
        tmp = tmp.filter(etat__in = ('0', '1')) if todo else tmp.filter(etat__in = ('2', '3')) if work else tmp.filter(etat__exact = '4')

    tasks = list()
    tasks.append(list())
    i = 1
    j = 0
    n = 0
    for t in tmp:
        t.target = True if target != None and target == t.id else False

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
        t.target = True if target != None and target == t.id else False

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
def list_releases(sprint_id, statut = None):
    notes = Note.objects.select_related().filter(sprint__id__exact = sprint_id).exclude(etat__exact = '4')
    notes = notes.order_by('-priorite')
    
    releases = list()
    for n in notes:
        release = Release.objects.select_related().filter(note__id__exact = n.id)
        if release.count() == 0:    
            release = Release()
            release.note = n
            release.statut = 0
            release.date_creation = n.date_creation
            release.utilisateur = n.utilisateur
            release.save()
        else:
            release = release.order_by('-date_creation')[0]
        if statut:
            if release.statut == str(statut):
                releases.append(release)
        else:
            releases.append(release)
    return releases

# ------------------------------------------------
@login_required
@csrf_protect
def projects(request):
    page = 'projects'
    
    user = request.user.get_profile()
    title = _(u'Projets')
    messages = list()

    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = HOME + 'projects'

    #write_logs()
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
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'projects': projects, 'membres': membres, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def project(request, project_id):
    page = 'project'
    
    project = get_object_or_404(Project, pk = project_id)

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s"') % {'project': project.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    f_all = Feature.objects.filter(projet__id__exact = project_id)
    f_done = f_all.filter(termine__gt = 0)

    s_all = Sprint.objects.filter(projet__id__exact = project_id)
    s_done = s_all.filter(date_fin__lt = datetime.date.today())

    p_all = Problem.objects.filter(projet__id__exact = project_id)
    p_done = p_all.filter(resolu__gt = 0)

    n_all = Note.objects.filter(feature__projet__id__exact = project.id, priorite__in = ('0', '2', '3', '4', '5'))
    n_done = n_all.filter(etat__exact = '4')

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
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'nbf': '%d / %d' % (f_done.count(), f_all.count()), 'nbs': '%d / %d' % (s_done.count(), s_all.count()), 
         'nbp': '%d / %d' % (p_done.count(), p_all.count()), 'nbn': '%d / %d' % (nd, na),
         'features': features, 'sprints': sprints, 'problems': problems, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def features(request, project_id):
    page = 'features'
    
    project = get_object_or_404(Project, pk = project_id)

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Fonctionnalités') % {'project': project.titre, }
    messages = list()
    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = HOME + 'projects/' + project_id + '/features'

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
            messages.append(_(u'Fonctionnalité modifiée avec succès !'))

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
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'features': features, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def feature(request, project_id, feature_id):
    page = 'feature'
    
    project = get_object_or_404(Project, pk = project_id)
    feature = get_object_or_404(Feature, pk = feature_id)

    user = request.user.get_profile()
    if not check_rights(user, project, feature):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Fonctionnalité "%(feature)s"') % {'project': project.titre, 'feature' : feature.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/features/' + feature_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    n_all = Note.objects.filter(feature__id__exact = feature_id)
    n_done = n_all.filter(etat__exact = '4')

    notes = list_notes(feature_id, max = nb_notes, nb_notes = nb_notes)

    return render_to_response('projects/feature.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'feature': feature, 'nbn': '%d / %d' % (n_done.count(), n_all.count()), 
         'notes': notes, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def notes(request, project_id, feature_id):
    page = 'notes'
    
    project = get_object_or_404(Project, pk = project_id)
    feature = get_object_or_404(Feature, pk = feature_id)

    user = request.user.get_profile()
    if not check_rights(user, project, feature):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Fonctionnalité "%(feature)s" - Notes de backlog') % {'project': project.titre, 'feature': feature.titre, }
    messages = list()
    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = HOME + 'projects/' + project_id + '/features/' + feature_id + '/notes'    

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
                    changes.append(u'sprint = %s' % (_(u'<Aucun>'), ))
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
            recalc_effort(project)
            add_log(user, 'note', note, 2, ', '.join(changes))
            messages.append(_(u'Note de backlog modifiée avec succès !'))

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
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'feature': feature, 'notes': notes, 'sprints': sprints, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def note(request, project_id, feature_id, note_id):
    page = 'note'
    
    project = get_object_or_404(Project, pk = project_id)
    feature = get_object_or_404(Feature, pk = feature_id)
    note = get_object_or_404(Note, pk = note_id)

    user = request.user.get_profile()
    if not check_rights(user, project, feature):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Fonctionnalité "%(feature)s" - Note "%(note)s"') % {'project': project.titre, 'feature': feature.titre, 'note': note.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/features/' + feature_id + '/notes/' + note_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    return render_to_response('projects/note.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'feature': feature, 'note': note, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def sprints(request, project_id):
    page = 'sprints'
    
    project = get_object_or_404(Project, pk = project_id)

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Sprints') % {'project': project.titre, }
    messages = list()
    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = HOME + 'projects/' + project_id + '/sprints'  

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
        import time
        id = int(request.POST['id'])
        sprint = Sprint.objects.get(pk = id)
        tmp = time.strptime(request.POST['date_debut'], '%Y-%m-%d')
        date_debut = datetime.date(tmp[0], tmp[1], tmp[2])
        tmp = time.strptime(request.POST['date_fin'], '%Y-%m-%d')
        date_fin = datetime.date(tmp[0], tmp[1], tmp[2])
        
        holidays = get_holidays(date_debut.year, date_fin.year)
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
        
        sprint.date_debut = date_debut
        sprint.date_fin = date_fin
        sprint.save()
        messages.append(_(u'Sprint modifié avec succès !'))
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
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 
         'messages': messages, 'project': project, 'sprints': sprints, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def sprint(request, project_id, sprint_id):
    page = 'sprint'
    
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)

    user = request.user.get_profile()
    if not check_rights(user, project, sprint):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Sprint "%(sprint)s"') % {'project': project.titre, 'sprint': sprint.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/sprints/' + sprint_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    n_all = Note.objects.filter(sprint__id__exact = sprint_id)
    t_all = Task.objects.filter(sprint__id__exact = sprint_id)
    n_done = n_all.filter(etat__exact = '4')
    t_done = t_all.filter(etat__exact = '4')

    notes = list_snotes(sprint_id, max = nb_notes, nb_notes = nb_notes)
    tasks = list_tasks(sprint_id, max = nb_notes, nb_notes = nb_notes)

    return render_to_response('projects/sprint.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'sprint': sprint, 'nbn': '%d / %d' % (n_done.count(), n_all.count()), 'nbt': '%d / %d' % (t_done.count(), t_all.count()), 
         'notes': notes, 'tasks': tasks, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def snotes(request, project_id, sprint_id):
    page = 'snotes'
    
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)

    user = request.user.get_profile()
    if not check_rights(user, project, sprint):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Sprint "%(sprint)s" - Notes de sprint') % {'project': project.titre, 'sprint': sprint.titre, }
    messages = list()
    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = HOME + 'projects/' + project_id + '/sprints/' + sprint_id + '/notes'

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
                if note.etat in (3, 4, ):
                    nts = NoteTime.objects.select_related().filter(note__in = (note, ))
                    nts = nts.order_by('-jour')
                    for nt in nts:
                        if nt.temps_fin != 0:
                            nt.temps_fin = 0
                            nt.save()
                    for nt in nts:
                        if nt.temps > 0:
                            fin = nt.note.temps_estime - nt.note.temps_realise
                            nt.temps_fin = fin
                            nt.save()
                            break
                    if note.etat == 3:
                        release = Release()
                        release.note = note
                        release.utilisateur = user
                        release.statut = '1'
                        release.commentaire = _(u'( Livraison automatique )')
                        release.save()
                else:
                    nts = NoteTime.objects.select_related().filter(note__in = (note, ))
                    for nt in nts:
                        nt.temps_fin = 0
                        nt.save()
                    release = Release.objects.select_related().filter(note__id__exact = note.id)
                    if release.count() != 0:                        
                        release = release.order_by('-date_creation')[0]
                        if release.statut == '1':
                            release = Release()
                            release.note = note
                            release.utilisateur = user
                            release.statut = '2'
                            release.commentaire = _(u'( Refus automatique )')
                            release.save()
                changes.append(u'état = ' + ETATS[int(note.etat)][1])
            note.utilisateur = user
            note.save()
            recalc_effort(project)
            add_log(user, 'note', note, 2, ', '.join(changes))
            messages.append(_(u'Note de sprint modifiée avec succès !'))

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
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'feature': feature, 'sprint': sprint, 'notes': notes, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def snote(request, project_id, sprint_id, note_id):
    page = 'snote'
    
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)
    note = get_object_or_404(Note, pk = note_id)

    user = request.user.get_profile()
    if not check_rights(user, project, sprint, note):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Sprint "%(sprint)s" - Note "%(note)s"') % {'project': projet.titre, 'sprint': sprint.titre, 'note': note.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/sprints/' + sprint_id + '/notes/' + note_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    return render_to_response('projects/snote.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'sprint': sprint, 'note': note, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def tasks(request, project_id, sprint_id):
    page = 'tasks'    
    
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)    

    user = request.user.get_profile()
    if not check_rights(user, project, sprint):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Sprint "%(sprint)s" - Tâches') % {'project': project.titre, 'sprint': sprint.titre, }
    messages = list()
    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = HOME + 'projects/' + project_id + '/sprints/' + sprint_id + '/tasks' 

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
                if task.etat == '4':
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
            messages.append(_(u'Tâche modifiée avec succès !'))

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
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'sprint': sprint, 'tasks': tasks, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def task(request, project_id, sprint_id, task_id):
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)
    task = get_object_or_404(Task, pk = task_id)    

    user = request.user.get_profile()
    if not check_rights(user, project, sprint, task):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Sprint "%(sprint)s" - Tâche "%(task)s"') % {'project': project.titre, 'sprint': sprint.titre, 'task': task.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/sprints/' + sprint_id + '/tasks/' + task_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    return render_to_response('projects/task.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'sprint': sprint, 'task': task, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def releases(request, project_id, sprint_id):
    page = 'releases'
    
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)   

    user = request.user.get_profile()
    if not check_rights(user, project, sprint):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Sprint "%(sprint)s" - Livraisons') % {'project': project.titre, 'sprint': sprint.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/sprints/' + sprint_id + '/releases'

    statut = '0'
    note = None
    details = list()
    if request.GET.__contains__('id'):
        note = int(request.GET['id'])
        details = Release.objects.filter(note__id__exact = note)
        details = details.order_by('-date_creation')
    if request.GET.__contains__('statut'):
        statut = request.GET['statut']    
    
    if request.method == 'POST':
        changes = list()
        if request.POST.__contains__('id'):
            id = request.POST['id']
            note = Note.objects.get(pk = id)
            nts = NoteTime.objects.select_related().filter(note__in = (note, ))
            nts = nts.order_by('-jour')
            
            old = Release.objects.select_related().filter(note__id__exact = id).order_by('-date_creation')
            old = old[0] if old.count() > 0 else None            
            
            release = Release()
            release.note = note
            release.utilisateur = user
            release.commentaire = request.POST['commentaire']
            
            if request.POST.__contains__('livrer'):
                if old and old.statut == '2' and settings.EMAIL_ENABLED:
                    send_mail(_(u'%(head)sLivraison de "%(note)s" %(state)s par %(user)s') % {'head': settings.EMAIL_SUBJECT_PREFIX, 'note': note.titre, 'state': _(u'RE-LIVRÉE'), 'user': user, },
                        _(u'La livraison de "%(note)s" (%(feature)s) a été %(state)s par %(user)s.\nCommentaire : "%(desc)s"') % 
                        {'note': note.titre, 'feature': note.feature.titre, 'state': _(u'RE-LIVRÉE'), 'user': user, 'desc': release.commentaire if release.commentaire else _(u'Aucun commentaire'), },
                        None, [ old.utilisateur.user.email ])
                for nt in nts:
                    if nt.temps > 0:
                        fin = nt.note.temps_estime - nt.note.temps_realise
                        nt.temps_fin = fin
                        nt.save()
                        break
                release.statut = 1
                release.save()
                note.etat = '3'
                note.save()
                changes.append(u'statut = ' + STATUTS[release.statut][1])
                add_log(user, 'release', release, 2, ', '.join(changes))
                messages.append(u'%s ( <a href=".?statut=%d#%d">%s</a> )' 
                    % (_(u'Livraison effectuée avec succès !'), release.statut, release.id, _(u'voir l\'élément'), ))
            elif request.POST.__contains__('refuser'):
                if old and settings.EMAIL_ENABLED:
                    send_mail(_(u'%(head)sLivraison de "%(note)s" %(state)s par %(user)s') % {'head': settings.EMAIL_SUBJECT_PREFIX, 'note': note.titre, 'state': _(u'REFUSÉE'), 'user': user, },
                        _(u'La livraison de "%(note)s" (%(feature)s) a été %(state)s par %(user)s.\nCommentaire : "%(desc)s"') % 
                        {'note': note.titre, 'feature': note.feature.titre, 'state': _(u'REFUSÉE'), 'user': user, 'desc': release.commentaire if release.commentaire else _(u'Aucun commentaire'), },
                        None, [ old.utilisateur.user.email ])
                for nt in nts:
                    if nt.temps_fin != 0:
                        nt.temps_fin = 0
                        nt.save()
                release.statut = 2
                release.save()
                note.etat = '2'
                note.save()
                changes.append(u'statut = ' + STATUTS[release.statut][1])
                add_log(user, 'release', release, 2, ', '.join(changes))
                messages.append(u'%s ( <a href=".?statut=%d#%d">%s</a> )' % 
                    (_(u'Livraison refusée avec succès !'), release.statut, release.id, _(u'voir l\'élément'), ))
            elif request.POST.__contains__('valider'):
                if old and settings.EMAIL_ENABLED:
                    send_mail(_(u'%(head)sLivraison de "%(note)s" %(state)s par %(user)s') % {'head': settings.EMAIL_SUBJECT_PREFIX, 'note': note.titre, 'state': _(u'VALIDÉE'), 'user': user, },
                        _(u'La livraison de "%(note)s" (%(feature)s) a été %(state)s par %(user)s.\nCommentaire : "%(desc)s"') % 
                        {'note': note.titre, 'feature': note.feature.titre, 'state': _(u'VALIDÉE'), 'user': user, 'desc': release.commentaire if release.commentaire else _(u'Aucun commentaire'), },
                        None, [ old.utilisateur.user.email ])
                for nt in nts:
                    if nt.temps_fin != 0:
                        nt.temps_fin = 0
                        nt.save()
                for nt in nts:
                    if nt.temps > 0:
                        fin = nt.note.temps_estime - nt.note.temps_realise
                        nt.temps_fin = fin
                        nt.save()
                        break
                release.statut = 3
                release.save()
                changes.append(u'statut = ' + STATUTS[release.statut][1])
                add_log(user, 'release', release, 2, ', '.join(changes))
                messages.append(u'%s ( <a href=".?statut=%d#%d">%s</a> )' % 
                    (_(u'Livraison validée avec succès !'), release.statut, release.id, _(u'voir l\'élément'), ))
            elif request.POST.__contains__('terminer'):
                for nt in nts:
                    if nt.temps > 0:
                        fin = nt.note.temps_estime - nt.note.temps_realise
                        nt.temps_fin = fin
                        nt.save()
                        break
                note.etat = '4'
                note.save()
                changes.append(u'etat = ' + ETATS[int(note.etat)][1])
                add_log(user, 'note', note, 2, ', '.join(changes))
                messages.append(_(u'Note de backlog terminée avec succès !'))

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    releases = list_releases(sprint_id, statut)

    return render_to_response('projects/releases.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'sprint': sprint, 'releases': releases, 'note': note, 'details': details, 'nb_notes': nb_notes, 'statut': statut, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def release(request, project_id, sprint_id, release_id):
    page = 'release'
    
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id) 
    release = get_object_or_404(Release, pk = release_id)

    user = request.user.get_profile()
    if not check_rights(user, project, sprint, release):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Sprint "%(sprint)s" - Livraison de "%(note)s"') % {'project': project.titre, 'sprint': sprint.titre, 'note': release.note.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/sprints/' + sprint_id + '/releases/' + release_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    return render_to_response('projects/releases.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'sprint': sprint, 'release': release, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def problems(request, project_id):
    page = 'problems'
    
    project = get_object_or_404(Project, pk = project_id)

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Problèmes') % {'project': project.titre, }
    messages = list()
    if request.session.__contains__('messages'):
        messages = request.session['messages']
        del request.session['messages']
    request.session['url'] = HOME + 'projects/' + project_id + '/problems'

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
                if settings.EMAIL_ENABLED:
                    send_mail(_(u'%(head)sProblème "%(problem)s" %(state)s dans le projet "%(project)s"') % {'head': settings.EMAIL_SUBJECT_PREFIX, 'problem': p.titre, 'state': _(u'résolu'), 'project': project.titre, },
                        _(u'Le problème "%(problem)s" dans le projet "%(project)s" a été %(state)s par %(user)s.\nDescription du problème : "%(desc)s"') % 
                        {'problem': p.titre, 'project': project.titre, 'state': _(u'résolu'), 'user': user, 'desc': p.description if p.description else _(u'Aucune description'), },
                        None, ['%s' % (u.user.email) for u in project.membres.all()])                
            else:
                problem.resolu = False
                changes.append(u'résolu = Non')
                if settings.EMAIL_ENABLED:
                    send_mail(_(u'%(head)sProblème "%(problem)s" %(state)s dans le projet "%(project)s"') % {'head': settings.EMAIL_SUBJECT_PREFIX, 'problem': p.titre, 'state': _(u'ré-ouvert'), 'project': project.titre, },
                        _(u'Le problème "%(problem)s" dans le projet "%(project)s" a été %(state)s par %(user)s.\nDescription du problème : "%(desc)s"') % 
                        {'problem': p.titre, 'project': project.titre, 'state': _(u'ré-ouvert'), 'user': user, 'desc': p.description if p.description else _(u'Aucune description'), },
                        None, ['%s' % (u.user.email) for u in project.membres.all()])  
            problem.utilisateur = user
            problem.save()
            add_log(user, 'problem', problem, 2, ', '.join(changes))
            messages.append(_(u'Problème modifié avec succès !'))

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
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'problems': problems, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def problem(request, project_id, problem_id):
    page = 'problem'
    
    project = get_object_or_404(Project, pk = project_id)
    problem = get_object_or_404(Problem, pk = problem_id)    

    user = request.user.get_profile()
    if not check_rights(user, project, problem):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Problème "%(problem)s"') % {'project': project.titre, 'problem': problem.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/problems/' + problem_id

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    return render_to_response('projects/problem.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'problem': problem, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def burndown(request, project_id, sprint_id):
    page = 'burndown'
    
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)

    user = request.user.get_profile()
    if not check_rights(user, project, sprint):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    tag = _('%d/%m/%Y %H:%M:%S')
    now = datetime.datetime.now()
    
    title = _(u'Projet "%(project)s" - Sprint "%(sprint)s" - Burndown Chart') % {'project': project.titre, 'sprint': sprint.titre, }
    messages = list()
    erreurs = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/sprints/' + sprint_id + '/burndown'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    csv = True if request.GET.__contains__('csv') else False
    csvdata = list()

    if request.method == 'POST':
        changes = list()
        ok = True
        item = None
        derniere_modification = request.POST['lock']
        for id in request.POST:
            if id[0:4] == 'Note':
                time = NoteTime.objects.select_related().get(pk = int(id[4:]))
                note = time.note
                if (derniere_modification != note.date_modification.strftime(tag)):
                    ok = False
                    continue
                temps = int(request.POST[id]) if request.POST[id].isdigit() else 0
                if (temps == 0):
                    time.date_modification = None
                    time.utilisateur = None
                elif (time.temps != temps):
                    note.etat = '2'
                    time.date_modification = datetime.datetime.now()
                    time.utilisateur = user
                note.temps_realise = note.temps_realise - time.temps
                time.temps = temps
                note.temps_realise = note.temps_realise + time.temps
                note.save()
                time.save()
                item = note
            elif id[0:5] == 'Tache':
                time = TaskTime.objects.select_related().get(pk = int(id[5:]))
                task = time.task
                if (derniere_modification != task.date_modification.strftime(tag)):
                    ok = False
                    continue
                temps = int(request.POST[id]) if request.POST[id].isdigit() else 0
                if (temps == 0):
                    time.date_modification = None
                    time.utilisateur = None
                elif (time.temps != temps):
                    task.etat = '2'
                    time.date_modification = datetime.datetime.now()
                    time.utilisateur = user
                task.temps_realise = task.temps_realise - time.temps
                time.temps = temps
                task.temps_realise = task.temps_realise + time.temps
                task.save()
                time.save()
                item = task
            elif id[0:5] == '_Note':
                note = Note.objects.select_related().get(pk = int(id[5:]))
                if (derniere_modification != note.date_modification.strftime(tag)):
                    ok = False
                    continue
                etat = '4' if request.POST[id] == 'oui' else '2'
                if note.etat in ('1', '2') and etat == '4':
                    nts = NoteTime.objects.filter(note__in = (note, ))
                    nts = nts.order_by('-jour')
                    for nt in nts:
                        if nt.temps > 0:
                            fin = nt.note.temps_estime - nt.note.temps_realise
                            nt.temps_fin = fin
                            nt.save()
                            break
                elif note.etat == '4' and etat == '2':
                    nts = NoteTime.objects.filter(note__in = (note, ))
                    etat = '1'
                    for nt in nts:
                        if nt.temps > 0:
                            etat = '2'
                        nt.temps_fin = 0
                        nt.save()
                note.etat = etat
                note.save()
                item = note
                changes.append(u'état = ' + ETATS[int(note.etat)][1])
                add_log(user, 'note', note, 2, ', '.join(changes))
            elif id[0:6] == '_Tache':
                task = Task.objects.select_related().get(pk = int(id[6:]))
                if (derniere_modification != task.date_modification.strftime(tag)):
                    ok = False
                    continue
                etat = '4' if request.POST[id] == 'oui' else '2'
                if task.etat in ('1', '2') and etat == '4':
                    tts = TaskTime.objects.filter(task__in = (task, ))
                    tts = tts.order_by('-jour')
                    for tt in tts:
                        if tt.temps > 0:
                            fin = tt.task.temps_estime - tt.task.temps_realise
                            tt.temps_fin = fin
                            tt.save()
                            break
                elif task.etat == '4' and etat == '2':
                    tts = TaskTime.objects.filter(task__in = (task, ))
                    etat = '1'
                    for tt in tts:
                        if tt.temps > 0:
                            etat = '2'
                        tt.temps_fin = 0
                        tt.save()
                task.etat = etat
                task.save()
                item = task
                changes.append(u'état = ' + ETATS[int(task.etat)][1])
                add_log(user, 'task', task, 2, ', '.join(changes))
        if ok:
            item.date_modification = now
            item.save()
            sprint.date_modification = now
            sprint.save()
            messages.append(_(u'Saisie de temps enregistrée avec succès !'))
        else:
            erreurs.append(_(u'Saisie annulée : les données ont été modifiées avant l\'enregistrement !'))
    
    holidays = get_holidays(datetime.date.today().year, datetime.date.today().year + 1)

    released = request.GET.__contains__('released')
    done = request.GET.__contains__('done')    

    days = list()
    times = list()
    total = 0

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
        d['etat'] = t.etat
        d['line'] = str(t.id)
        d['form'] = '?done' if done else '.'
        d['lock'] = t.date_modification.strftime(tag)
        d['url'] = 'tasks'
        
        if csv:
            export = [ d['type'], d['base'], d['name'], PRIORITES[int(t.priorite)][1], '', ETATS[int(t.etat)][1], ]
            for x in tt:
                export.append(str(x.temps))
            export.extend([ str(d['done']), str(d['todo']), ])
            csvdata.append(export)        
        
        if done and t.etat in ('3', '4'):
            times.append(d)
        elif not done and t.etat not in ('0', '3', '4'):
            times.append(d)
        for d in tt:
            days.append(d.jour)
        total += t.temps_estime

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
        d['etat'] = n.etat
        d['line'] = str(n.feature.id) + '_' + str(n.id)
        d['form'] = '?done' if done else '?released' if released else '.'
        d['lock'] = n.date_modification.strftime(tag)
        d['url'] = 'notes'

        if csv:
            export = [ d['type'], d['base'], d['name'], PRIORITES[int(n.priorite)][1], TYPES[int(n.type)][1], ETATS[int(n.etat)][1], ]
            for x in nt:
                export.append(str(x.temps))
            export.extend([ str(d['done']), str(d['todo']), ])
            csvdata.append(export)
        
        if released and n.etat == '3':
            times.append(d)
        elif done and n.etat == '4':
            times.append(d)
        elif not released and not done and n.etat not in ('3', '4'):
            times.append(d)
        for d in nt:
            days.append(d.jour)
        total += n.temps_estime

    days = list(set(days))
    days.sort()
    
    headers = [ u'', _(u'Fonctionnalité'), _(u'Titre'), _(u'Priorité'), _(u'Type'), _(u'État'), ]
    
    mini = 0
    data1 = list()
    tmp = total
    data1.append(tmp)
    for day in days:
        headers.append(day.strftime(_('%d/%m')))
        nts = NoteTime.objects.filter(sprint__id__exact = sprint.id, jour__exact = day)
        tts = TaskTime.objects.filter(sprint__id__exact = sprint.id, jour__exact = day)
        for t in nts:
            tmp -= (t.temps + t.temps_fin)
        for t in tts:
            tmp -= (t.temps + t.temps_fin)
        if tmp < 0 and tmp < mini:
            mini = tmp
        data1.append(tmp)
    
    headers.extend([ _(u'Temps réalisé'), _(u'Temps estimé'), ]) 

    data2 = list()
    tmp = total
    data2.append(tmp)
    for day in days:
        tmp = tmp - (float(total) / (len(days)))
        if tmp < 0:
            tmp = 0
        data2.append(tmp)

    url  = u'http://chart.apis.google.com/chart'
    url += u'?chs=800x350'
    url += u'&cht=lxy'
    url += u'&chg=%f,0' % (100.0 / len(days) if len(days) > 0 else 100, )
    url += u'&chdl=%s|%s' % (_(u'Temps restant'), _(u'Temps estimé'), )
    url += u'&chdlp=b'
    url += u'&chxt=x,y'
    url += u'&chxl=0:||%s' % ('|'.join('%s' % (d.strftime(_('%d/%m'))) for d in days), )
    url += u'&chxr=1,%f,%f' % (mini, total, )
    url += u'&chds=0,0,%f,%f' % (mini, total, )
    url += u'&chco=0000ff,ff0000,00aaaa'
    url += u'&chls=2,4,2|2,0,0|2,0,0'
    url += u'&chm=s,ff0000,0,-1,5|N*f0*,000000,0,-1,11|s,0000ff,1,-1,5|s,00aa00,2,-1,5'
    url += u'&chf=c,lg,45,ffffff,0,76a4fb,0.75'
    url += u'&chd=t:-1|%s' % (','.join('%f' % (x) for x in data1), )
    url += u'|-1|%s' % (','.join('%f' % (y) for y in data2), )
    
    if not csv:
        return render_to_response('projects/burndown.html',
            {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
             'erreurs': erreurs, 'project': project, 'sprint': sprint, 'days': days, 'times': times, 
             'url': url, 'date': datetime.date.today(), 'nb_notes': nb_notes, },
            context_instance = RequestContext(request))
    else:
        csvreturn = HttpResponse(mimetype = 'text/csv')
        csvreturn['Content-Disposition'] = 'attachement; filename=%s - %s.csv' % (remove_accents(project.titre), remove_accents(sprint.titre), )
        t = loader.get_template('projects/csvexport.txt')
        csvdata.insert(0, headers)
        c = Context({ 'data': csvdata, })
        csvreturn.write(t.render(c))
        return csvreturn

#-------------------------------------------------
@login_required
@csrf_protect
def velocity(request, project_id):    
    page = 'velocity'
    
    project = get_object_or_404(Project, pk = project_id)

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Velocité et progression') % {'project': project.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/velocity'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    sprints = Sprint.objects.filter(projet__id__exact = project.id).order_by('date_debut')
    
    i = 0
    labels = list()
    for sprint in sprints:
        i += 1
        labels.append(_(u'Sprint %d') % (i))

    data = [list(), list(), list(), list()]
    for i in range(4):
        s = 0
        for sprint in sprints:
            notes = Note.objects.filter(sprint__id__exact = sprint.id, type__exact = i, etat__in = ('3', '4'))
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

    url1  = u'http://chart.apis.google.com/chart'
    url1 += u'?chs=800x350'
    url1 += u'&cht=bvs'
    url1 += u'&chbh=a'
    url1 += u'&chdl=%s|%s|%s|%s' % (_(u'User-story'), _(u'Feature'), _(u'Bug'), _(u'Spike'), )
    url1 += u'&chdlp=t|l'
    url1 += u'&chxt=x,y'
    url1 += u'&chxl=0:|%s' % ('|'.join(labels), )
    url1 += u'&chxr=1,0,%f' % (max1, )
    url1 += u'&chds=0,%f' % (max1, )
    url1 += u'&chco=ccffcc,ffffcc,ffcc99,cecaff'
    url1 += u'&chm=N,ff0000,-1,,12,,e::11|N,000000,0,,11,,c|N,000000,1,,11,,c|N,000000,2,,10,,c|N,000000,3,,11,,c'
    url1 += u'&chf=c,lg,45,ffffff,0,76a4fb,0.75'
    url1 += u'&chd=t:%s' % ('|'.join('%s' % (','.join('%f' % (v) for v in values)) for values in data), )

    i = 0
    first = True
    cumul = 0
    max2 = 0
    charge1 = list()
    charge2 = list()
    labels = list()
    for sprint in sprints:
        i += 1
        labels.append(_(u'Sprint %d') % (i))
        notes = Note.objects.filter(sprint__id__exact = sprint.id, etat__in = ('3', '4'))
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
    
    l = None
    avgs = list()
    if sprints.count() > 0:
        avg = cumul / sprints.count()
        avgs = charge1[:]
        tmp = cumul
        while tmp < max2 and avg != 0:
            tmp += avg
            avgs.append(tmp)
            labels.append(_(u'Sprint %d') % (len(labels) + 1))
            charge1.append(cumul)
            charge2.append(sprint.effort)
            l = [max(charge1) if len(charge1) > 0 else 0, max(charge2) if len(charge2) > 0 else 0, max(avgs) if len(avgs) > 0 else 0]
    else:
        l = [max(charge1) if len(charge1) > 0 else 0, max(charge2) if len(charge2) > 0 else 0]
    max2 = max(l) if l else sprint.effort

    url2  = u'http://chart.apis.google.com/chart'
    url2 += u'?chs=800x350'
    url2 += u'&cht=lxy'
    url2 += u'&chg=%f,0' % (100.0 / len(charge1) if len(charge1) > 0 else 0, )
    url2 += u'&chdl=%s|%s' % (_(u'Charge réalisée puis estimée'), _(u'Charge totale'), )
    url2 += u'&chdlp=t|l'
    url2 += u'&chxt=x,y'
    url2 += u'&chxl=0:||%s' % ('|'.join(labels), )
    url2 += u'&chxr=1,0,%f' % (max2, )
    url2 += u'&chds=0,%f' % (max2, )
    url2 += u'&chco=0000ff,ff0000'
    url2 += u'&chls=2,4,2|2,0,0'
    url2 += u'&chm=s,ff0000,0,-1,5|N*f0*,000000,0,-1,11|s,0000ff,1,-1,5|N*f0*,ff0000,1,-1,11'
    url2 += u'&chf=c,lg,45,ffffff,0,76a4fb,0.75'
    url2 += u'&chd=t:-1|0,%s' % (','.join('%f' % (x) for x in avgs), )
    url2 += u'|-1|%s' % (','.join('%f' % (y) for y in charge2), )

    return render_to_response('projects/velocity.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'project': project, 'url1': url1, 'url2': url2, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def pareto(request, project_id):
    page = 'pareto'
    
    project = get_object_or_404(Project, pk = project_id)    

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Diagramme de Pareto') % {'project': project.titre, }
    request.session['url'] = HOME + 'projects/' + project_id + '/pareto'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)
    
    data = dict()
    rows = dict()
    taux = dict()
    features = Feature.objects.filter(projet__id__exact = project_id)
    for feature in features:
        data[feature.titre] = list()
        rows[feature.titre] = 0
        taux[feature.titre] = [0, 0]
    
    i = 0
    cols = list()
    labels = list()
    sprints = Sprint.objects.filter(projet__id__exact = project_id)
    for sprint in sprints:
        cols.append(0)
        i += 1
        labels.append(_(u'Sprint %d') % (i))
        for feature in features:
            data[feature.titre].append(0)
        notes = Note.objects.select_related().filter(sprint__id__exact = sprint.id)
        for note in notes:
            name = note.feature.titre
            data[name][-1] += note.temps_realise
            rows[name] += note.temps_realise
            cols[-1] += note.temps_realise
    
    cols.append(0)
    for (k, v) in rows.iteritems():
        cols[-1] += v
    total = cols[-1]
    for (k, v) in rows.iteritems():
        taux[k][0] = round(v * 100.0 / total, 1)
    
    data = sorted(data.iteritems(), key = lambda d: sum(d[1]))
    data.reverse()
    
    numbers = dict()
    colors = dict()
    cumul = 0.0
    i = 0
    for (k, v) in data:
        i += 1
        numbers[k] = i
        cumul += taux[k][0]
        taux[k][1] = cumul
        colors[k] = 'ccffcc' if cumul <= 80 else 'ffffcc' if cumul > 80 and cumul <= 95 else 'ffcc99'
    
    nbs = numbers.values()
    nbs.sort()
    
    chart1 = rows.values()
    chart1.sort()
    chart1.reverse()
    
    chart2 = [round(t[1]) for t in taux.values()]
    chart2.sort()
    
    maxi = max(chart1) if len(chart1) > 0 else 0
    url  = u'http://chart.apis.google.com/chart'
    url += u'?chs=800x350'
    url += u'&cht=bvg'
    url += u'&chg=0,10'
    url += u'&chbh=a'
    url += u'&chxt=x,y,r'
    url += u'&chxl=0:|%s' % ('|'.join('%d' % (n) for n in nbs), )
    url += u'&chxr=1,0,%f|2,0,100' % (maxi, )
    url += u'&chds=0,%f,0,100' % (maxi, )
    url += u'&chco=%s,ff0000' % ('|'.join('%s' % (colors[k]) for (k, v) in data), )
    url += u'&chm=N,000000,0,,11,,t:0:15|D,ff0000,1,0,2|N** %,ff0000,1,,9,,t:0:-15'
    url += u'&chf=c,lg,45,ffffff,0,76a4fb,0.75'
    url += u'&chd=t1:%s' % (','.join('%f' % (x) for x in chart1), )
    url += u'|%s' % (','.join('%f' % (y) for y in chart2), )
    
    return render_to_response('projects/pareto.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'project': project, 'nb_notes': nb_notes, 'url': url, 
         'labels': labels, 'numbers': numbers, 'data': data, 'rows': rows, 'cols': cols, 'taux': taux, 'colors': colors, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def summary(request, project_id):
    page = 'summary'
    
    project = get_object_or_404(Project, pk = project_id)

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Synthèse') % {'project': project.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/summary'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)
    
    sprints = Sprint.objects.filter(projet__id__exact = project.id).order_by('date_debut')
    id = int(request.GET['sprint']) if request.GET.__contains__('sprint') else sprints[sprints.count() - 1].id if sprints.count() > 0 else 0
    
    items = list()
    for sprint in sprints:
        if sprint.id == id:
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
                time['day'] = time['jour'].strftime(_('%d/%m'))
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
            l = [max(chart1) if len(chart1) > 0 else 0, max(chart2) if len(chart2) > 0 else 0]
            max1 = max(l)
            
            url1  = u'http://chart.apis.google.com/chart'
            url1 += u'?chs=800x350'
            url1 += u'&cht=lxy'
            url1 += u'&chg=%f,0' % (100.0 / len(days) if len(days) > 0 else 100, )
            url1 += u'&chdl=%s|%s' % (_(u'Temps réalisé'), _(u'Temps moyen estimé'), )
            url1 += u'&chdlp=t'
            url1 += u'&chxt=x,y'
            url1 += u'&chxl=0:||%s' % ('|'.join('%s' % (str(day)) for day in days), )
            url1 += u'&chxr=1,0,%f' % (max1, )
            url1 += u'&chds=0,%f' % (max1, )
            url1 += u'&chco=0000ff,ff0000'
            url1 += u'&chls=2,4,2|2,0,0|2,0,0'
            url1 += u'&chm=s,ff0000,0,-1,5|N*f0*,000000,0,-1,11|s,0000ff,1,-1,5|N*f0*,ff0000,1,-1,11'
            url1 += u'&chf=c,lg,45,ffffff,0,76a4fb,0.75'
            url1 += u'&chd=t:-1|0,%s' % (','.join('%f' % (x) for x in chart1), )
            url1 += u'|-1|0,%s' % (','.join('%f' % (y) for y in chart2), )
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
            l = [max(chart1) if len(chart1) > 0 else 0, max(chart2) if len(chart2) > 0 else 0, item['total_todo']]
            max2 = max(l)
            
            url2  = u'http://chart.apis.google.com/chart'
            url2 += u'?chs=800x350'
            url2 += u'&cht=lxy'
            url2 += u'&chg=%f,0' % (100.0 / len(days) if len(days) > 0 else 100, )
            url2 += u'&chdl=%s|%s' % (_(u'Progression réelle'), _(u'Progression estimée'), )
            url2 += u'&chdlp=t'
            url2 += u'&chxt=x,y'
            url2 += u'&chxl=0:||%s' % ('|'.join('%s' % (str(day)) for day in days), )
            url2 += u'&chxr=1,0,%f' % (max2, )
            url2 += u'&chds=0,%f' % (max2, )
            url2 += u'&chco=0000ff,ff0000,000000'
            url2 += u'&chls=2,4,2|2,0,0|2,0,0'
            url2 += u'&chm=s,ff0000,0,-1,5|N*f0*,000000,0,-1,11|s,0000ff,1,-1,5|N*f0*,ff0000,1,-1,11'
            url2 += u'&chf=c,lg,45,ffffff,0,76a4fb,0.75'
            url2 += u'&chd=t:-1|0,%s' % (','.join('%f' % (x) for x in chart1), )
            url2 += u'|-1|0,%s' % (','.join('%f' % (y) for y in chart2), )
            url2 += u'|-1|%s' % (','.join('%f' % (z) for z in chart3), )
            item['url2'] = url2
            
            items.append(item)
    
    return render_to_response('projects/summary.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 'project': project, 
         'items': items, 'date': datetime.datetime.today().strftime('%d/%m'), 'sprint': str(id), 'sprints': sprints, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

#-------------------------------------------------
@login_required
@csrf_protect
def meteo(request, project_id, sprint_id):
    page = 'meteo'
    
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)

    user = request.user.get_profile()
    if not check_rights(user, project, sprint):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Sprint "%(sprint)s" - Météo') % {'project': project.titre, 'sprint': sprint.titre, }
    messages = list()
    erreurs = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/sprints/' + sprint_id + '/meteo'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)
    
    if request.method == 'POST':
        meteo = Meteo()
        date = request.POST['date'].split('/')
        meteo.jour = datetime.date(int(date[2]), int(date[1]), int(date[0]))
        meteo.sprint = sprint
        meteo.utilisateur = user
        test = Meteo.objects.filter(sprint__id__exact = sprint.id, jour__exact = meteo.jour, utilisateur__id__exact = user.user.id)
        if not test:
            meteo.meteo_projet = request.POST['meteo_projet']
            meteo.meteo_equipe = request.POST['meteo_equipe']
            meteo.meteo_avance = request.POST['meteo_avance']
            meteo.commentaire = request.POST['commentaire']
            meteo.save()
            add_log(user, 'meteo', meteo, 1)
            messages.append(_(u'Météorologie enregistrée avec succès pour la journée du %s !') % (request.POST['date']))
        else:
            erreurs.append(_(u'Vous avez déjà enregistré une météorologie pour la journée du %s !') % (request.POST['date']))
    
    labels = list()
    data = [list(), list(), list()]
    
    row = 1
    jours = list()
    holidays = get_holidays(sprint.date_debut.year, sprint.date_fin.year)
    d = sprint.date_fin if sprint.date_fin < datetime.date.today() else datetime.date.today()
    while d >= sprint.date_debut:
        if d.strftime('%w') not in ('0', '6', ) and d not in holidays:
            jour = dict()
            meteo = Meteo.objects.select_related().filter(sprint__id__exact = sprint_id, jour__exact = d).order_by("utilisateur")
            perso = meteo.filter(utilisateur__id__exact = user.user.id)
            autre = meteo.exclude(utilisateur__id__exact = user.user.id)
            row = (row + 1) % 2
            jour['row'] = row + 1
            jour['date'] = d.strftime(_('%d/%m/%Y'))
            jour['perso'] = perso
            jour['autre'] = autre
            jour['nb'] = autre.count() + 1
            jours.append(jour)
            labels.append(d.strftime(_('%d/%m')))
            mp = 0
            me = 0
            ma = 0
            for m in meteo:
                mp += int(m.meteo_projet)
                me += int(m.meteo_equipe)
                ma += int(m.meteo_avance)
            data[0].append(mp)
            data[1].append(me)
            data[2].append(ma)
        d -= datetime.timedelta(1)
    
    labels.reverse()
    for i in range(len(data)):
        data[i].reverse()    
    
    maxi = 0
    tmp = 0
    for i in range(len(labels)):
        for j in range(len(data)):
            tmp += data[j][i]
        if tmp > maxi:
            maxi = tmp
        tmp = 0
    
    url  = u'http://chart.apis.google.com/chart'
    url += u'?chs=800x350'
    url += u'&cht=bvs'
    url += u'&chbh=a'
    url += u'&chdl=%s|%s|%s' % (_(u'Projet'), _(u'Equipe'), _(u'Avancement'), )
    url += u'&chdlp=t'
    url += u'&chxt=x,y'
    url += u'&chxl=0:|%s' % ('|'.join(labels), )
    url += u'&chxr=1,0,%f' % (maxi, )
    url += u'&chds=0,%f' % (maxi, )
    url += u'&chco=ccffcc,ffffcc,ffcc99'
    url += u'&chm=N,000000,0,,11,,c|N,000000,1,,11,,c|N,000000,2,,10,,c'
    url += u'&chf=c,lg,45,ffffff,0,76a4fb,0.75'
    url += u'&chd=t:%s' % ('|'.join('%s' % (','.join('%f' % (v) for v in values)) for values in data), )
    
    return render_to_response('projects/meteo.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 'erreurs': erreurs,  
         'project': project, 'sprint': sprint, 'jours': jours, 'meteo': METEO, 'url': url, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

#-------------------------------------------------
@login_required
@csrf_protect
def documents(request, project_id):
    page = 'documents'
    
    project = get_object_or_404(Project, pk = project_id)

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Documents') % {'project': project.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/documents'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.save()
            add_log(user, 'document', d, 1)
            messages.append(_(u'Document ajouté avec succès !'))
    else:
        form = DocumentForm(initial = {'utilisateur': user.id, 'projet': project.id, })

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
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'form': form, 'documents': documents, 'project': project, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def scrumwall(request, project_id):
    page = 'scrumwall'
    
    project = get_object_or_404(Project, pk = project_id)    

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Scrum Wall') % {'project': project.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/scrumwall'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)
    
    sprint = 0
    if request.method == 'GET':
        if request.GET.__contains__('sprint'):
            sprint = int(request.GET['sprint'])
    
    backlog = False
    scrumwall = list()
    features = Feature.objects.filter(projet__id__exact = project_id)
    features = features.order_by('-priorite')
    for f in features:
        items = dict()
        items['id'] = f.id
        items['name'] = f.titre
        items['item'] = f
        
        spec = Note.objects.filter(feature__id__exact = f.id, etat__exact = '0')
        if sprint != 0:
            spec = spec.filter(sprint__id__exact = sprint)
        spec = spec.order_by('-priorite')
        items['spec'] = spec
        
        todo = Note.objects.filter(feature__id__exact = f.id, etat__exact = '1')
        if sprint != 0:
            todo = todo.filter(sprint__id__exact = sprint)
        todo = todo.order_by('-priorite')
        items['todo'] = todo
        
        run  = Note.objects.filter(feature__id__exact = f.id, etat__exact = '2')
        if sprint != 0:
            run = run.filter(sprint__id__exact = sprint)
        run  = run.order_by('-priorite')
        items['run'] = run
        
        gone = Note.objects.filter(feature__id__exact = f.id, etat__exact = '3')
        if sprint != 0:
            gone = gone.filter(sprint__id__exact = sprint)
        gone = gone.order_by('-priorite')
        items['gone'] = gone
        
        done = Note.objects.filter(feature__id__exact = f.id, etat__exact = '4')
        if sprint != 0:
            done = done.filter(sprint__id__exact = sprint)
        done = done.order_by('-priorite')
        items['done'] = done
        
        if spec.count() > 0:
            backlog = True
        if spec.count() + todo.count() + run.count() + gone.count() + done.count() > 0:
            scrumwall.append(items)
    
    sprints = Sprint.objects.filter(projet__id__exact = project_id).order_by('date_debut')

    return render_to_response('projects/scrumwall.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 'scrumwall': scrumwall, 
         'project': project, 'sprints': sprints, 'backlog': backlog, 'nb_notes': nb_notes, 'taille': nb_notes * 230, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def poker(request, project_id):
    page = 'poker'    
    
    project = get_object_or_404(Project, pk = project_id)    

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Planning Poker') % {'project': project.titre, }
    messages = list()
    erreurs = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/poker'

    add_history(user, request.session['url'])
    nb_notes = get_nb_notes(request)
    
    if request.method == 'POST':
        if request.POST.__contains__('effort'):
            effort = int(request.POST['effort'])
            note = Note.objects.get(pk = int(request.POST['id']))
            poker = Poker.objects.filter(note__id__exact = note.id, utilisateur__id__exact = user.user.id)
            if not poker:
                poker = Poker()
                poker.note = note
                poker.effort = effort
                poker.utilisateur = user
                poker.save()
            else:
                poker = poker[0]
                poker.effort = effort
                if poker.effort != 0:
                    poker.save()
                else:
                    poker.delete()
            messages.append(_(u'Estimation d\'effort sauvegardée avec succès !'))
        elif request.POST.__contains__('avg'):
            note = Note.objects.get(pk = int(request.POST['id']))
            avg = int(request.POST['avg']) if request.POST['avg'].isdigit() else 0
            temps = int(request.POST['temps']) if request.POST['temps'].isdigit() else 0
            note.effort = avg
            note.temps_estime = temps
            note.save()
            recalc_effort(project)
            add_log(user, 'note', note, 2, u'effort = %d, temps = %d' % (avg, temps, ))
            messages.append(_(u'Nouvelles valeurs de l\'effort et du temps estimé sauvegardées avec succès !'))

    sprint = 0
    opt = None
    if request.GET.__contains__('sprint'):
        sprint = int(request.GET['sprint'])
    if request.GET.__contains__('opt'):
        opt = request.GET['opt']
    
    liste = list()
    if sprint or opt:
        features = Feature.objects.filter(projet__id__exact = project_id).order_by('titre')
        for f in features:
            notes = Note.objects.filter(feature__id__exact = f.id).order_by('titre')
            if sprint != 0:
                notes = notes.filter(sprint__id__exact = sprint)
            for n in notes:
                data = dict()
                poker = Poker.objects.filter(note__id__exact = n.id).order_by('utilisateur')
                perso = poker.filter(utilisateur__id__exact = user.user.id)
                data['f'] = f.titre
                data['fid'] = f.id
                data['n'] = n.titre
                data['nid'] = n.id
                data['temps'] = n.temps_estime
                data['effort'] = n.effort
                data['perso'] = perso[0].effort if perso else 0
                data['poker'] = poker
                data['nb'] = poker.count()
                avg = 0
                if poker.count() > 0:
                    for p in poker:
                        avg += p.effort
                    avg = avg * 1.0 / poker.count()
                    old = -1
                    for e in EFFORTS:
                        if e[0] > avg:
                            avg = e[0] if (avg - old) > (e[0] - avg) else old
                            break
                        old = e[0]
                data['avg'] = avg
                if (opt == 'all') or (opt == 'todo' and not perso) or (opt == 'set' and perso) or (opt == 'done' and avg != 0 and (n.effort != avg or n.effort == 0)):
                    liste.append(data)
    
    sprints = Sprint.objects.filter(projet__id__exact = project_id).order_by('date_debut')
    
    return render_to_response('projects/poker.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'project': project, 'messages': messages, 'erreurs': erreurs,
         'sprints': sprints, 'sprint': sprint, 'opt': opt, 'liste': liste, 'efforts': EFFORTS, 'nb_notes': nb_notes, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def new_project(request):
    page = 'new_project'    
    
    user = request.user.get_profile()
    title = _(u'Nouveau projet')
    messages = list()
    request.session['url'] = HOME + 'projects/new'

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            p = form.save()
            add_log(user, 'project', p, 1)
            messages.append(_(u'Projet ajouté avec succès !'))
            request.session['messages'] = messages
            return HttpResponseRedirect(request.session['url'][0:-3])
    else:
        form = ProjectForm(initial = { 'membres': (1, user.id, ) })

    return render_to_response('projects/project_new.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 'form': form, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def new_feature(request, project_id):
    page = 'new_feature'
    
    project = get_object_or_404(Project, pk = project_id)

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Nouvelle fonctionnalité') % {'project': project.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/features/new'

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = FeatureForm(request.POST)
        if form.is_valid():
            f = form.save()
            add_log(user, 'feature', f, 1)
            messages.append(_(u'Fonctionnalité ajoutée avec succès !'))
            request.session['messages'] = messages
            return HttpResponseRedirect(request.session['url'][0:-3])
    else:
        form = FeatureForm(initial = { 'utilisateur': user.id, 'projet': project.id, })

    return render_to_response('projects/feature_new.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'form': form, 'project': project, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def new_note(request, project_id, feature_id):
    page = 'new_note'
    
    project = get_object_or_404(Project, pk = project_id)
    feature = get_object_or_404(Feature, pk = feature_id)     

    user = request.user.get_profile()
    if not check_rights(user, project, feature):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Fonctionnalité "%(feature)s" - Nouvelle note') % {'project': project.titre, 'feature': feature.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/features/' + feature_id + '/notes/new'   

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            n = form.save()
            release = Release.objects.filter(note__id__exact = n.id)
            if release.count() == 0:    
                release = Release()
                release.note = n
                release.statut = 0
                release.date_creation = n.date_creation
                release.utilisateur = n.utilisateur
                release.save()
            add_log(user, 'note', n, 1)
            messages.append(_(u'Note de backlog ajoutée avec succès !'))
            request.session['messages'] = messages
            recalc_effort(project)
            return HttpResponseRedirect(request.session['url'][0:-3])
    else:
        form = NoteForm(initial = { 'utilisateur': user.id, 'projet': project.id, 'feature': feature.id, 'etat': '1', })

    return render_to_response('projects/note_new.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'form': form, 'project': project, 'feature': feature, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def new_sprint(request, project_id):
    page = 'new_sprint'
    
    project = get_object_or_404(Project, pk = project_id)

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Nouveau sprint') % {'project': project.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/sprints/new'

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = SprintForm(request.POST)
        if form.is_valid():
            s = form.save()
            add_log(user, 'sprint', s, 1)
            messages.append(_(u'Sprint ajouté avec succès !'))
            request.session['messages'] = messages
            return HttpResponseRedirect(request.session['url'][0:-3])
    else:
        notes = Note.objects.filter(feature__projet__id__exact = project.id, priorite__in = ('0', '2', '3', '4', '5'))
        effort = 0
        for note in notes:
            effort += note.effort
        sprints = Sprint.objects.filter(projet__id__exact = project.id)
        titre = _(u'Sprint %d') % (sprints.count() + 1)
        form = SprintForm(initial = { 'utilisateur': user.id, 'projet': project.id, 'effort': effort, 'titre': titre, })

    return render_to_response('projects/sprint_new.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'form': form, 'project': project, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def new_task(request, project_id, sprint_id):
    page = 'new_task'
    
    project = get_object_or_404(Project, pk = project_id)
    sprint = get_object_or_404(Sprint, pk = sprint_id)

    user = request.user.get_profile()
    if not check_rights(user, project, sprint):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Sprint "%(sprint)s" - Nouvelle tâche') % {'project': project.titre, 'sprint': sprint.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/sprints/' + sprint_id + '/tasks/new'

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            t = form.save()
            create_task_days(sprint, t)
            add_log(user, 'task', t, 1)
            messages.append(_(u'Tâche ajoutée avec succès !'))
            request.session['messages'] = messages
            return HttpResponseRedirect(request.session['url'][0:-3])
    else:
        form = TaskForm(initial = { 'utilisateur': user.id, 'projet': project.id, 'sprint': sprint.id, 'etat': '1', })

    return render_to_response('projects/task_new.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'form': form, 'project': project, 'sprint': sprint, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def new_problem(request, project_id):
    page = 'new_problem'
    
    project = get_object_or_404(Project, pk = project_id)    

    user = request.user.get_profile()
    if not check_rights(user, project):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Nouveau problème') % {'project': project.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/problems/new'   

    add_history(user, request.session['url'])

    if request.method == 'POST':
        form = ProblemForm(request.POST)
        if form.is_valid():
            p = form.save()
            if settings.EMAIL_ENABLED:
                send_mail(_(u'%(head)sProblème "%(problem)s" détecté dans le projet "%(project)s"') % {'head': settings.EMAIL_SUBJECT_PREFIX, 'problem': p.titre, 'project': project.titre, },
                    _(u'Un nouveau problème "%(problem)s" dans le projet "%(project)s" a été identifié par %(user)s.\nDescription du problème : "%(desc)s"') % 
                    {'problem': p.titre, 'project': project.titre, 'user': user, 'desc': p.description if p.description else _(u'Aucune description'), },
                    None, ['%s' % (u.user.email) for u in project.membres.all()])
            add_log(user, 'problem', p, 1)
            messages.append(_(u'Problème ajouté avec succès !'))
            request.session['messages'] = messages
            return HttpResponseRedirect(request.session['url'][0:-3])
    else:
        form = ProblemForm(initial = { 'utilisateur': user.id, 'projet': project.id, })

    return render_to_response('projects/problem_new.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'form': form, 'project': project, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@csrf_protect
def new_user(request):
    page = 'new_user'
    
    user = request.user
    title = u'Nouvel utilisateur'
    messages = list()
    request.session['url'] = HOME + 'projects/user'

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
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'form': form, 'project': project, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def add_sprint(request, project_id, feature_id, note_id):
    page = 'add_sprint'
    
    project = get_object_or_404(Project, pk = project_id)
    feature = get_object_or_404(Feature, pk = feature_id)
    note = get_object_or_404(Note, pk = note_id)

    user = request.user.get_profile()
    if not check_rights(user, project, feature, note):
        return render_to_response('error.html', { 'page': page, 'home': HOME, 'theme': THEME, 
            'user': user, 'title': ERREUR_TITRE, 'erreur': ERREUR_TEXTE, })
    
    title = _(u'Projet "%(project)s" - Nouveau sprint') % {'project': project.titre, }
    messages = list()
    request.session['url'] = HOME + 'projects/' + project_id + '/features/' + feature_id + '/notes/' + note_id + '/sprint'

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
            messages.append(_(u'Sprint ajouté et associé avec succès !'))
            request.session['messages'] = messages
            return HttpResponseRedirect(HOME + 'projects/' + project_id + '/features/' + feature_id + '/notes/')
    else:
        notes = Note.objects.filter(feature__projet__id__exact = project.id, priorite__in = ('0', '2', '3', '4', '5'))
        effort = 0
        for note in notes:
            effort += note.effort
        sprints = Sprint.objects.filter(projet__id__exact = project.id)
        titre = _(u'Sprint %d') % (sprints.count() + 1)
        form = SprintForm(initial = { 'utilisateur': user.id, 'projet': project.id, 'effort': effort, 'titre': titre, })

    return render_to_response('projects/sprint_new.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'form': form, 'project': project, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def logs(request):
    page = 'logs'
    
    user = request.user.get_profile()
    title = _(u'Logs')
    messages = list()
    request.session['url'] = HOME + 'projects/logs'

    add_history(user, request.session['url'])

    lcount = LogEntry.objects.values('user').annotate(count = Count('id'))
    users = UserProfile.objects.all()
    for u in users:
        u.lcount = 0
        for l in lcount:
            if l['user'] == u.user.id:
                u.lcount = l['count']

    if request.method == 'GET':
        if request.GET.__contains__('archive'):
            write_logs(archive_history = False, archive_logs = True)
            messages.append(_(u'Logs les plus anciens archivés avec succès !'))

    logs = LogEntry.objects.all()

    numero = 1
    luser = 0
    huser = 0
    if request.method == 'GET':
        if request.GET.__contains__('page'):
            numero = int(request.GET['page'])
        if request.GET.__contains__('luser'):
            luser = int(request.GET['luser'])
            logs = logs.filter(user__id__exact = luser)
    if request.method == 'POST':
        if request.POST.__contains__('lselect'):
            if request.POST['luser'] != '0':
                luser = int(request.POST['luser'])
                logs = logs.filter(user__id__exact = luser)
        if request.POST.__contains__('ldelete'):
            if request.POST['luser'] == '0':
                for l in logs:
                    l.delete()
                messages.append(_(u'Logs supprimés avec succès !'))
            else:
                luser = int(request.POST['luser'])
                logs = LogEntry.objects.filter(user__id__exact = luser)
                for l in logs:
                    l.delete()
                messages.append(_(u'Logs de "%s" supprimés avec succès !') % (UserProfile.objects.get(pk = int(request.POST['luser'])), ))
            logs = LogEntry.objects.all()
            logs = logs.order_by('-action_time')
    
    logs = logs.order_by('-action_time')
    paginator = Paginator(logs, 20)
    logs_list = paginator.page(numero)    

    return render_to_response('projects/logs.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'logs': logs_list, 'users': users, 'luser': luser, },
        context_instance = RequestContext(request))

# ------------------------------------------------
@login_required
@csrf_protect
def history(request):
    page = 'history'
    
    user = request.user.get_profile()
    title = _(u'Historiques')
    messages = list()
    request.session['url'] = HOME + 'projects/history'

    add_history(user, request.session['url'])

    hcount = History.objects.values('utilisateur').annotate(count = Count('id'))
    users = UserProfile.objects.all()
    for u in users:
        u.hcount = 0
        for h in hcount:
            if h['utilisateur'] == u.user.id:
                u.hcount = h['count']

    if request.method == 'GET':
        if request.GET.__contains__('archive'):
            write_logs(archive_history = True, archive_logs = False)
            messages.append(_(u'Historiques les plus anciens archivés avec succès !'))

    history = History.objects.all()

    numero = 1
    luser = 0
    huser = 0
    if request.method == 'GET':
        if request.GET.__contains__('page'):
            numero = int(request.GET['page'])
        if request.GET.__contains__('huser'):
            huser = int(request.GET['huser'])
            history = history.filter(utilisateur__id__exact = huser)            
    if request.method == 'POST':
        if request.POST.__contains__('hselect'):
            if request.POST['huser'] != '0':
                huser = int(request.POST['huser'])
                history = history.filter(utilisateur__id__exact = huser)
        if request.POST.__contains__('hdelete'):
            if request.POST['huser'] == '0':
                for h in history:
                    h.delete()
                messages.append(_(u'Historiques supprimés avec succès !'))
            else:
                huser = int(request.POST['huser'])
                history = History.objects.filter(utilisateur__id__exact = huser)
                for h in history:
                    h.delete()
                messages.append(_(u'Historiques de "%s" supprimés avec succès !') % (UserProfile.objects.get(pk = int(request.POST['huser'])), ))
            history = History.objects.all()
            history = history.order_by('-date_creation')
    
    history = history.order_by('-date_creation')
    paginator = Paginator(history, 20)
    history_list = paginator.page(numero)    

    return render_to_response('projects/history.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 'messages': messages, 
         'history': history_list, 'users': users, 'huser': huser, },
        context_instance = RequestContext(request))  

# ------------------------------------------------
@login_required
@csrf_protect
def archives(request):
    page = 'archives'
    
    user = request.user.get_profile()
    title = _(u'Archives')
    messages = list()
    request.session['url'] = HOME + 'projects/archives'

    add_history(user, request.session['url'])

    if request.method == 'POST':
        if request.POST.__contains__('files'):
            for f in request.POST.getlist('files'):
                os.remove(os.path.join(ROOT, 'logs', f))

    path = os.path.join(ROOT, 'logs')
    os.chdir(path)
    lfiles = list()
    hfiles = list()
    for f in os.listdir('.'):
        if f[-4:].lower() == 'html':
            if f[:4].lower() == 'logs':
                lfiles.append(f)
            elif f[:4].lower() == 'urls':
                hfiles.append(f)
    lfiles.sort()
    hfiles.sort()

    return render_to_response('projects/archives.html',
        {'page': page, 'home': HOME, 'theme': THEME, 'user': user, 'title': title, 
         'messages': messages, 'lfiles': lfiles, 'hfiles': hfiles, 'lcount': len(lfiles), 'hcount': len(hfiles), },
        context_instance = RequestContext(request))
