# Django settings for tangleon project.

import os
import socket

DEBUG = socket.gethostname() != 'tangleon-srv'
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Faraz Masood Khan', 'faraz@tangleon.com'),
)

MANAGERS = ADMINS

if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2', #'mysql', 'sqlite3' or 'oracle'.
            'NAME': 'tangleon',                      # Or path to database file if using sqlite3.
            # The following settings are not used with sqlite3:
            'USER': 'pguser',
            'PASSWORD': 'turboteen',
            'HOST': '127.0.0.1',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
            'PORT': '5432',                      # Set to empty string for default.
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2', #'mysql', 'sqlite3' or 'oracle'.
            'NAME': 'tangleon',                      # Or path to database file if using sqlite3.
            # The following settings are not used with sqlite3:
            'USER': os.environ['TANGLE_ON_DB_USER'],
            'PASSWORD': os.environ['TANGLE_ON_DB_PASSWORD'],
            'HOST': os.environ['TANGLE_ON_DB_HOST'],                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
            'PORT': int(os.environ['TANGLE_ON_DB_PORT']),                      # Set to empty string for default.
        }
    }
    

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['.tangleon.com']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Asia/Karachi'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = '' if DEBUG else os.environ['TANGLE_ON_MEDIA_ROOT']

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = '' if DEBUG else os.environ['TANGLE_ON_STATIC_ROOT']

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(os.path.dirname(__file__),'static').replace('\\','/'),
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
if DEBUG:
    SECRET_KEY = '1vbeii4ia8pkg5e7!jea-q$ukvx+!#p!b@g!%=(a9$*y)l)514'
else:
    SECRET_KEY = os.environ['TANGLE_ON_SECRET_KEY']

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tangleon.app.AppMiddleware', # It attaches user object to every request by with lazy loading
)

ROOT_URLCONF = 'tangleon.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'tangleon.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__),'templates').replace('\\','/'),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'tangleon.app',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    #'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    'django.contrib.admindocs',
    'django.contrib.humanize',
)

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

INTERNAL_IPS = ('127.0.0.1',)
# Settings for django debug toolbar
if DEBUG and False:    
    MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
    DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
    #'template_timings_panel.panels.TemplateTimings.TemplateTimings',
    )
    INSTALLED_APPS += ('debug_toolbar', )# 'template_timings_panel')


# Context processors
from django.conf import global_settings
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
    'django.core.context_processors.request', 
    'tangleon.app.context_processors.bootstrip',
)

# Email server settings
if DEBUG:
    EMAIL_HOST = os.environ['TANGLE_ON_EMAIL_HOST']
    EMAIL_PORT = os.environ['TANGLE_ON_EMAIL_PORT']
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ['TANGLE_ON_EMAIL_HOST_USER']
    EMAIL_HOST_PASSWORD = os.environ['TANGLE_ON_EMAIL_HOST_PASSWORD']
else:
    EMAIL_HOST = os.environ['TANGLE_ON_EMAIL_HOST']
    EMAIL_PORT = os.environ['TANGLE_ON_EMAIL_PORT']
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ['TANGLE_ON_EMAIL_HOST_USER']
    EMAIL_HOST_PASSWORD = os.environ['TANGLE_ON_EMAIL_HOST_PASSWORD'] 

# TangleOn specific settings
ADMIN_EMAILS = ('faraz@tangleon.com',)
META_KEYWORDS = ''
META_DESCRIPTION = ''
PAGE_SIZE = 20
STATIC_CONTENT_VERSION = 20 # An incremental value to force browser reload, it should only be incremented if static content updated
MAX_COMMENT_LEGNTH = 1000

# Facebook settings
if DEBUG:
    FB_APP_ID = os.environ['TANGLE_ON_DEBUG_FB_APP_ID']
    FB_APP_SECRET = os.environ['TANGLE_ON_DEBUG_FB_APP_SECRET']
else:
    FB_APP_ID = os.environ['TANGLE_ON_FB_APP_ID']
    FB_APP_SECRET = os.environ['TANGLE_ON_FB_APP_SECRET']
    
FB_ACCESS_TOKEN = 'https://graph.facebook.com/oauth/access_token'
FB_AUTH_URL = 'https://www.facebook.com/dialog/oauth'
FB_GRAPH_ME = 'https://graph.facebook.com/me'
FB_GRAPH_FRIENDS = 'https://graph.facebook.com/me/friends'
