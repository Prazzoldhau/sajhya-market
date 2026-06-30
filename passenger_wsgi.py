import sys
import os

# Add your project directory to the Python path
PROJECT_PATH = '/home2/madhyapu/sajhya.com'
if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sajhya_project.settings')

# Create WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()