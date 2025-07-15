import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE = {
    'name': os.path.join(BASE_DIR, 'database.db'),
    'backup_dir': os.path.join(BASE_DIR, 'backups')
}

CACHE = {
    'timeout': 300,  # 5 minutes
    'max_size': 100  # maximum items in cache
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'app.log'),
            'formatter': 'standard'
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True
        }
    }
}

# Internationalization
LANGUAGES = ['fr', 'en']
DEFAULT_LANGUAGE = 'fr'