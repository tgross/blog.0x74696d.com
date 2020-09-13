# Django settings for djangobook project.
# Stripped-down to minimal required settings

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = ()
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db',
    }
}

SITE_ID = 1

TIME_ZONE = 'UTC' # Local time zone for this installation.
LANGUAGE_CODE = 'en-us' # Language code for this installation.
USE_I18N = False
USE_L10N = True
USE_TZ = True

MEDIA_ROOT = '' # absolute filesystem path to directory for user-uploaded files
MEDIA_URL = '' # URL to handle the media (use trailing slash)
STATIC_ROOT = '' # absolute path to directory static files should be collected to.
STATIC_URL = '/static/' # URL prefix for static files.

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'pe5c4kz=i*r1ha66z54aj+p43@jpf(3cz)7(*y^ylaqghsx6e%'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'djangobook.urls'
WSGI_APPLICATION = 'djangobook.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'books',
    'django.contrib.admin',
)

# Logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
