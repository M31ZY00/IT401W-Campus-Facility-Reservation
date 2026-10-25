from .settings import *

DATABASES['default']['TEST'] = {
    'NAME': str(BASE_DIR / 'test_concurrency.sqlite3'),
}