from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from scrum import settings

urlpatterns = patterns('',
    # Example:
    # (r'^scrum/', include('scrum.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
    (r'^accounts/', include('django.contrib.auth.urls')),
    
    # Project's views
    (r'^projects/', include('scrum.projects.urls')),
    
    # Logs archives
    (r'^logs/(?P<path>.*)$', 'django.views.static.serve', 
     {'document_root': settings.DEFAULT_DIR + 'logs'}),    
    
    # Themes
    (r'^media/(?P<path>.*)$', 'django.views.static.serve', 
     {'document_root': settings.DEFAULT_DIR + 'media'}),
)

# Fix urls in admin panel
admin.site.root_path = ''
