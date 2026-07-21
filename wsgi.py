"""
WSGI Entry Point for Production Deployment
This file can be used by WSGI servers like Gunicorn
"""
from backend.app import app

# For WSGI servers
application = app

if __name__ == '__main__':
    app.run()
