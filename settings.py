# Deployment settings for an easy install

import os

DEFAULT_HOME = '/'
DEFAULT_DIR = os.path.dirname(os.path.abspath(__file__)) + os.sep
DEFAULT_URL = 'localhost:8000'

# Django settings for scrum project.

DEBUG = True
#TEMPLATE_DEBUG = DEBUG
TEMPLATE_DEBUG = True

ADMINS = (
    ('Marc DEBUREAUX', 'marc@debnet.fr'),
)

MANAGERS = ADMINS

# Obsolete
#DATABASE_ENGINE = 'sqlite3'					# 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
#DATABASE_NAME = DEFAULT_DIR + 'database.db'	# Or path to database file if using sqlite3.
#DATABASE_USER = ''								# Not used with sqlite3.
#DATABASE_PASSWORD = ''							# Not used with sqlite3.
#DATABASE_HOST = ''								# Set to empty string for localhost. Not used with sqlite3.
#DATABASE_PORT = ''								# Set to empty string for default. Not used with sqlite3.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DEFAULT_DIR + 'database.db',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Paris'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'fr-FR'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = DEFAULT_DIR + 'media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = DEFAULT_HOME + 'media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = 'http://' + DEFAULT_URL + DEFAULT_HOME + 'media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.csrf.CsrfResponseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'scrum.middleware.UrlRedirectMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
)

ROOT_URLCONF = 'scrum.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    DEFAULT_DIR + 'templates',
)

URL_REDIRECTS = (
    (r'^/$', DEFAULT_HOME + 'projects'),
    (r'^/accounts/$', DEFAULT_HOME + 'projects'),
    (r'^/accounts/profile/$', DEFAULT_HOME + 'projects'),
    (r'^/accounts/login/user/$', DEFAULT_HOME + 'projects/user/'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'scrum.projects',
)

LOGIN_REDIRECT_URL = DEFAULT_HOME + 'accounts/profile/'
LOGIN_URL = DEFAULT_HOME + 'accounts/login/'
LOGOUT_URL = DEFAULT_HOME + 'accounts/logout/' 

# Custom User model for authentification
AUTH_PROFILE_MODULE = 'projects.UserProfile'
