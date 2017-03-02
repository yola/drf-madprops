import django
from django.conf import settings


settings.configure()
if hasattr(django, 'setup'):
    django.setup()
