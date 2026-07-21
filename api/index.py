"""
Vercel Serverless Function Entry Point
This file imports and exposes the Flask app for Vercel deployment.
"""
import sys
import os

# Add the backend directory to Python path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Import the Flask app from backend
from app import app

# Vercel expects a handler
handler = app

# For local testing
if __name__ == '__main__':
    app.run(debug=True)
