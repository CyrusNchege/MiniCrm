import os
from dotenv import load_dotenv
from celery import Celery

# Load environment variables from .env file
load_dotenv()

from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Instantiate Celery app
app = Celery("core")

# Load configuration from Django settings, using the 'CELERY_' namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks from all installed apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")