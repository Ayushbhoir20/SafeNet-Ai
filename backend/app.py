"""
Flask Web Application for Phishing Detection (Industry-Grade Tiered Detection)
===============================================================================

This application uses a three-layer tiered detection approach:

Layer 1: Fast ML Detection (Random Forest with probability-based classification)
  - Safe: phishing_prob < 0.35
  - Suspicious: 0.35 <= phishing_prob <= 0.65
  - Phishing: phishing_prob > 0.65

Layer 2: External Blacklist Check (PhishTank, Google Safe Browsing)
  - If blacklisted → FINAL = Phishing

Layer 3: Lightweight Content Analysis (only for Suspicious URLs)
  - Analyzes page title, forms, password fields, brand impersonation
  - Does NOT perform full crawling or JavaScript execution

Features:
- Three-layer tiered detection for accuracy and speed
- External blacklist integration (PhishTank, Google Safe Browsing)
- Selective content analysis (only suspicious URLs)
- Professional UI with dark/light themes
- Comprehensive detection results with all layer outputs
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
from datetime import datetime
import joblib
import numpy as np
import traceback
import stripe
from feature_extraction import extract_url_features, validate_url, get_whois_info
from urllib.parse import urlparse
import tldextract
from authlib.integrations.flask_client import OAuth

# Import tiered detection modules
from tiered_detection import TieredDetectionEngine
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)  # Suppress Gemini API warning


# Import Google Gemini AI for chatbot
import google.generativeai as genai
import os

# Import database and authentication modules
from db import (mongodb_available, users_collection, scans_collection, logs_collection,
                blacklist_collection, system_config_collection, admin_logs_collection, 
                messages_collection, payments_collection, credit_logs_collection)
from auth import register_user, authenticate_user, create_admin_user, log_admin_action

# Validate MongoDB is available
if not mongodb_available or users_collection is None:
    print("\n" + "=" * 80)
    print("ERROR: MongoDB is required for SafeNet AI")
    print("=" * 80)
    print("\n❌ MongoDB connection not available!")
    print("   SafeNet AI requires MongoDB for user authentication.\n")
    print("📋 Setup Instructions:")
    print("   1. See MONGODB_QUICKSTART.md for 5-minute setup")
    print("   2. Create .env file with your MongoDB connection string")
    print("   3. Restart the application\n")
    print("=" * 80 + "\n")
    import sys
    sys.exit(1)

# Initialize Flask app with templates and static in backend folder
import os as os_module
base_dir = os_module.path.dirname(os_module.path.abspath(__file__))
template_dir = os_module.path.join(base_dir, 'templates')
static_dir = os_module.path.join(base_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'your-secret-key-change-this-in-production-12345'  # Change this in production!
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Always reload templates on change
CORS(app)  # Enable CORS for API testing

# Inject a cache-bust version into every template (changes each server restart)
import time as _time
_CACHE_BUST = str(int(_time.time()))
@app.context_processor
def inject_cache_bust():
    return {'cache_bust': _CACHE_BUST}

# PHISHING DETECTION THRESHOLD
# If phishing probability > THRESHOLD, classify as phishing
# Lower threshold = more aggressive phishing detection (fewer false negatives)
PHISHING_THRESHOLD = 0.35  # Custom threshold for production-ready phishing detection

# Initialize Google Gemini AI for Chatbot
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
gemini_model = None

# Initialize OAuth
oauth = OAuth(app)

# Get the base URL from environment or use localhost for development
BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')

google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        # Add clock skew tolerance (5 minutes)
        'token_endpoint_auth_method': 'client_secret_post',
    },
    # Explicitly set redirect URI
    redirect_uri=f'{BASE_URL}/auth/google/callback',
    # Add leeway for token validation (handles clock skew)
    authorize_params={'access_type': 'offline'}
)

if GEMINI_API_KEY and GEMINI_API_KEY != 'your_gemini_api_key_here':
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel(
            model_name='models/gemini-2.5-flash',  # Latest available model
            generation_config={
                'temperature': 0.7,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 2048,  # Increased for better responses
            },
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
        )
        pass  # Gemini AI initialized
    except Exception as e:
        pass  # Gemini AI failed
        gemini_model = None
else:
    pass  # Gemini API key not configured

# Global variables for model and scaler
model = None
scaler = None
model_metadata = None
tiered_engine = None  # Tiered detection engine


def login_required(f):
    """
    Decorator to protect routes that require authentication.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to protect routes that require admin access.
    Returns 403 Forbidden for non-admin users.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            return render_template('403.html'), 403
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """
    Get current user data from database.
    Returns None if not logged in or user not found.
    """
    if 'logged_in' not in session or 'user_id' not in session:
        return None
    
    try:
        user = users_collection.find_one({'user_id': session['user_id']})
        return user
    except Exception as e:
        print(f"Error getting current user: {e}")
        return None


# Trusted domains - well-known legitimate websites
TRUSTED_DOMAINS = [
    'google.com', 'www.google.com', 'youtube.com', 'www.youtube.com',
    'amazon.com', 'www.amazon.com', 'amazon.in', 'www.amazon.in',
    'flipkart.com', 'www.flipkart.com',
    'microsoft.com', 'www.microsoft.com',
    'apple.com', 'www.apple.com',
    'paypal.com', 'www.paypal.com',
    'facebook.com', 'www.facebook.com',
    'instagram.com', 'www.instagram.com',
    'twitter.com', 'www.twitter.com',
    'linkedin.com', 'www.linkedin.com',
    'github.com', 'www.github.com',
    'stackoverflow.com', 'www.stackoverflow.com',
    'wikipedia.org', 'www.wikipedia.org',
    'netflix.com', 'www.netflix.com'
]


def load_model():
    """
    Load the trained ML model, scaler, and initialize tiered detection engine.
    """
    global model, scaler, model_metadata, tiered_engine
    
    try:
        # Use absolute paths based on this script's location
        script_dir = os_module.path.dirname(os_module.path.abspath(__file__))
        model_dir = os_module.path.join(script_dir, 'model')
        
        model = joblib.load(os_module.path.join(model_dir, 'best_model.pkl'))
        scaler = joblib.load(os_module.path.join(model_dir, 'scaler.pkl'))
        model_metadata = joblib.load(os_module.path.join(model_dir, 'model_metadata.pkl'))
        
        # Initialize Tiered Detection Engine
        google_api_key = None
        tiered_engine = TieredDetectionEngine(model, scaler, google_api_key)
        
        return True
    except Exception as e:
        print(f"❌ Error loading model: {str(e)}")
        print("Please run 'python backend/train_model.py' first to train the model.")
        return False


def calculate_suspicious_word_count(url):
    """
    Count suspicious keywords commonly used in phishing URLs.
    
    Args:
        url (str): URL to analyze
        
    Returns:
        int: Count of suspicious words found
    """
    suspicious_keywords = [
        'login', 'verify', 'account', 'update', 'secure', 'banking',
        'confirm', 'password', 'signin', 'suspended', 'locked',
        'validate', 'authentication', 'credential', 'urgent', 'alert'
    ]
    
    url_lower = url.lower()
    count = sum(1 for keyword in suspicious_keywords if keyword in url_lower)
    return count


def is_trusted_domain(domain, clean_domain):
    """
    Check if a domain is in the trusted domain whitelist.
    
    Args:
        domain (str): Full domain from URL (e.g., www.google.com)
        clean_domain (str): Clean domain without subdomain (e.g., google.com)
        
    Returns:
        bool: True if domain is trusted, False otherwise
    """
    domain_lower = domain.lower()
    clean_lower = clean_domain.lower()
    
    # Check both full domain and clean domain
    return domain_lower in TRUSTED_DOMAINS or clean_lower in TRUSTED_DOMAINS


def detect_brand_in_path(url, domain, clean_domain):
    """
    Detect brand names appearing in the URL PATH when the actual domain is NOT the official brand.
    This catches phishing attacks like: http://malicious.com/path/paypal.com/login
    
    Args:
        url (str): Full URL to analyze
        domain (str): Domain from URL (could include subdomain)
        clean_domain (str): Clean eTLD+1 domain (e.g., example.com)
        
    Returns:
        tuple: (is_brand_in_path: bool, brand_name: str or None)
    """
    # Known brand domains to check for
    brand_domains = {
        'itau': ['itau.com.br', 'www.itau.com.br'],
        'paypal': ['paypal.com', 'www.paypal.com'],
        'amazon': ['amazon.com', 'www.amazon.com', 'amazon.in', 'www.amazon.in'],
        'google': ['google.com', 'www.google.com'],
        'facebook': ['facebook.com', 'www.facebook.com'],
        'microsoft': ['microsoft.com', 'www.microsoft.com'],
        'apple': ['apple.com', 'www.apple.com'],
        'netflix': ['netflix.com', 'www.netflix.com'],
        'instagram': ['instagram.com', 'www.instagram.com'],
        'twitter': ['twitter.com', 'www.twitter.com'],
        'linkedin': ['linkedin.com', 'www.linkedin.com']
    }
    
    # Extract the URL path
    parsed = urlparse(url)
    url_path = parsed.path.lower()
    domain_lower = domain.lower()
    clean_lower = clean_domain.lower()
    
    # Check if any brand domain appears in the PATH
    for brand_name, official_domains in brand_domains.items():
        for official_domain in official_domains:
            # Check if brand domain appears in the PATH
            if official_domain in url_path:
                # Verify that the actual domain is NOT the official domain
                if domain_lower not in official_domains and clean_lower not in official_domains:
                    print(f"[BRAND IN PATH] Found '{official_domain}' in path, but domain is '{clean_domain}' - PHISHING!")
                    return True, brand_name.capitalize()
    
    return False, None


def detect_brand_impersonation(url, domain):
    """
    Detect potential brand impersonation or typosquatting.
    
    Args:
        url (str): Full URL to analyze
        domain (str): Domain name extracted from URL
        
    Returns:
        tuple: (is_impersonation: bool, brand_name: str or None)
    """
    # Common brands and their typosquatting variants
    brand_patterns = {
        'paypal': ['paypa1', 'paypai', 'paypa11', 'paypall', 'paypa-'],
        'google': ['goog1e', 'googie', 'gooogle', 'g00gle', 'gogle'],
        'amazon': ['amaz0n', 'amazom', 'arnazon', 'amazon-'],
        'microsoft': ['micros0ft', 'microsft', 'micro-soft', 'microsoft-'],
        'apple': ['app1e', 'appl3', 'apple-', 'appie'],
        'facebook': ['faceb00k', 'face-book', 'facebook-', 'facebo0k'],
        'netflix': ['netf1ix', 'netfl1x', 'netflix-', 'netflex'],
        'instagram': ['instagr4m', 'insta-gram', 'instagram-'],
        'twitter': ['twiter', 'tw1tter', 'twitter-'],
        'linkedin': ['link3din', 'linked-in', 'linkedin-']
    }
    
    url_lower = url.lower()
    domain_lower = domain.lower()
    
    # Check for brand names or variants in URL/domain
    for brand, variants in brand_patterns.items():
        # Check if brand name appears but domain doesn't exactly match the official domain
        if brand in url_lower or brand in domain_lower:
            # If it's not the official domain, flag as impersonation
            official_domains = [f'{brand}.com', f'www.{brand}.com']
            if domain_lower not in official_domains:
                return True, brand.capitalize()
        
        # Check for typosquatting variants
        for variant in variants:
            if variant in url_lower or variant in domain_lower:
                return True, brand.capitalize()
    
    return False, None


def apply_rule_based_detection(url, features, whois_info, ml_prediction, ml_confidence):
    """
    Apply rule-based validation to override or adjust ML predictions.
    This implements a hybrid approach to catch obvious phishing patterns.
    
    Args:
        url (str): The URL being analyzed
        features (dict): Extracted URL features
        whois_info (dict): WHOIS information
        ml_prediction (str): ML model's prediction ("Phishing" or "Legitimate")
        ml_confidence (float): ML model's confidence (0-100)
        
    Returns:
        tuple: (final_prediction, final_confidence, detection_method, warnings)
    """
    warnings = []
    detection_method = "ML Prediction"
    final_prediction = ml_prediction
    final_confidence = ml_confidence
    
    # Extract domain information
    parsed = urlparse(url)
    domain = parsed.netloc
    ext = tldextract.extract(url)
    domain_suffix = ext.suffix.lower()
    clean_domain = f"{ext.domain}.{ext.suffix}"
    
    # Check if this is a trusted domain
    is_trusted = is_trusted_domain(domain, clean_domain)
    
    # Count suspicious words
    suspicious_count = calculate_suspicious_word_count(url)
    
    # Detect brand impersonation
    is_impersonation, brand_name = detect_brand_impersonation(url, domain)
    
    # Detect brand in path (CRITICAL RULE - highest priority)
    is_brand_in_path, brand_in_path_name = detect_brand_in_path(url, domain, clean_domain)
    
    # Get feature values
    has_https = features.get('has_https', 0)
    domain_age = whois_info.get('domain_age_days', -1)
    has_suspicious_words = features.get('has_suspicious_words', 0)
    
    # ==================== PRIORITY RULE 0: BRAND IN PATH (CRITICAL) ====================
    # This catches URLs like: http://malicious.info/path/itau.com.br/login
    # where the real domain is malicious but contains a brand in the path
    if is_brand_in_path:
        final_prediction = "Phishing"
        final_confidence = 93.0  # High confidence for this clear attack pattern
        detection_method = "Rule-Based Override (Brand Impersonation)"
        warnings.append(f"Brand domain '{brand_in_path_name}' found in URL path")
        warnings.append(f"Actual domain is '{clean_domain}' - not the official brand")
        if not has_https:
            warnings.append("No HTTPS encryption")
            final_confidence = 95.0  # Even higher confidence
        print(f"[RULE 0 - CRITICAL] Brand '{brand_in_path_name}' in path but domain is '{clean_domain}' - forcing PHISHING")
    
    # RULE 1: .example domain (RFC 2606 - reserved for documentation)
    elif domain_suffix == 'example':
        final_prediction = "Phishing"
        final_confidence = 100.0
        detection_method = "Rule-Based Override"
        warnings.append("Suspicious .example domain detected")
        print(f"[RULE 1] .example domain detected - forcing PHISHING")
    
    # RULE 2: No HTTPS + Brand Impersonation
    elif not has_https and is_impersonation:
        final_prediction = "Phishing"
        final_confidence = 95.0
        detection_method = "Rule-Based Override"
        warnings.append(f"Brand impersonation detected ({brand_name})")
        warnings.append("No HTTPS encryption")
        print(f"[RULE 2] HTTP + Brand impersonation ({brand_name}) - forcing PHISHING")
    
    # RULE 3: Multiple suspicious words + No HTTPS
    elif suspicious_count >= 2 and not has_https:
        final_prediction = "Phishing"
        final_confidence = 90.0
        detection_method = "Rule-Based Override"
        warnings.append(f"Multiple suspicious keywords detected ({suspicious_count})")
        warnings.append("No HTTPS encryption")
        print(f"[RULE 3] {suspicious_count} suspicious words + HTTP - forcing PHISHING")
    
    # TRUSTED DOMAIN HANDLING - Boost confidence and reduce penalties
    elif is_trusted:
        print(f"[TRUSTED DOMAIN] {clean_domain} is in whitelist")
        
        # For trusted domains, boost confidence if prediction is legitimate
        if final_prediction == "Legitimate":
            # HTTPS + Trusted = Very high confidence
            if has_https and not has_suspicious_words:
                final_confidence = max(final_confidence, 92.0)
                detection_method = "Hybrid Decision"
                print(f"[TRUSTED DOMAIN] HTTPS + Trusted domain - boosting confidence to {final_confidence}%")
            # HTTP but trusted and no suspicious words = Still reasonably confident
            elif not has_suspicious_words:
                final_confidence = max(final_confidence, 85.0)
                detection_method = "Hybrid Decision"
                if not has_https:
                    warnings.append("Trusted domain, but HTTP instead of HTTPS")
            
            # Don't penalize for unknown WHOIS on trusted domains
            if domain_age == -1:
                # Remove any WHOIS-related warnings
                warnings = [w for w in warnings if 'domain age' not in w.lower() and 'whois' not in w.lower()]
        
        # If ML predicted phishing for a trusted domain, be very cautious
        elif final_prediction == "Phishing" and not is_impersonation:
            # Reduce confidence in phishing prediction for trusted domains
            final_confidence = min(final_confidence, 60.0)
            detection_method = "Hybrid Decision"
            warnings.append(f"Trusted domain ({clean_domain}) flagged - review carefully")
    
    # RULE 4: Unknown WHOIS + Suspicious words (cap confidence, don't override)
    elif domain_age == -1 and has_suspicious_words:
        if final_prediction == "Legitimate" and final_confidence > 75:
            final_confidence = 75.0
            detection_method = "Hybrid Decision"
            warnings.append("Domain age unknown")
            warnings.append("Suspicious keywords present")
            print(f"[RULE 4] Unknown WHOIS + suspicious words - capping confidence at 75%")
        elif final_prediction == "Phishing":
            # Boost phishing confidence
            final_confidence = min(95.0, final_confidence + 10)
            detection_method = "Hybrid Decision"
            warnings.append("Domain age unknown")
    
    # RULE 5: Young domain + Suspicious words
    elif 0 <= domain_age < 30 and suspicious_count > 0:
        if final_prediction == "Phishing":
            final_confidence = min(98.0, final_confidence + 15)
            detection_method = "Hybrid Decision"
            warnings.append(f"Very young domain ({domain_age} days)")
            warnings.append("Suspicious keywords present")
            print(f"[RULE 5] Young domain ({domain_age} days) + suspicious words - boosting phishing score")
        else:
            # Lower confidence in legitimate prediction
            final_confidence = max(50.0, final_confidence - 20)
            detection_method = "Hybrid Decision"
            warnings.append(f"Very young domain ({domain_age} days)")
    
    # Additional check: Brand impersonation alone (even with HTTPS)
    if is_impersonation and "impersonation" not in str(warnings) and not is_trusted:
        warnings.append(f"Possible {brand_name} impersonation")
        if final_prediction == "Legitimate":
            final_confidence = min(70.0, final_confidence)
            detection_method = "Hybrid Decision"
    
    # Cap confidence when WHOIS is unknown (general rule for non-trusted domains)
    if domain_age == -1 and final_confidence > 85 and final_prediction == "Legitimate" and not is_trusted:
        final_confidence = 85.0
        if detection_method == "ML Prediction":
            detection_method = "Hybrid Decision"
        if "Domain age unknown" not in warnings:
            warnings.append("Domain age unknown - confidence limited")
    
    return final_prediction, final_confidence, detection_method, warnings


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login with email and password.
    Supports both MongoDB and demo mode.
    """
    if request.method == 'GET':
        # If already logged in, redirect to home page
        if 'logged_in' in session:
            return redirect(url_for('home'))
        return render_template('login.html')
    
    # POST request - handle login
    try:
        data = request.get_json()
        email = data.get('username', '').strip()  # Frontend sends 'username' but we treat it as email
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400
        
        # Authenticate user with MongoDB
        success, message, user_data = authenticate_user(users_collection, email, password)
        
        if success:
            # Get full user data from database to include plan
            user = users_collection.find_one({'user_id': user_data['id']})
            user_plan = user.get('plan', 'free') if user else 'free'
            
            session['logged_in'] = True
            session['user_id'] = user_data['id']
            session['email'] = user_data['email']
            session['role'] = user_data.get('role', 'user')
            session['plan'] = user_plan  # Add plan to session
            
            # Determine redirect based on role
            if user_data.get('role') == 'admin':
                # Log admin login
                log_admin_action(admin_logs_collection, user_data['email'], 'admin_login', {
                    'ip_address': request.remote_addr
                })
                redirect_url = '/admin/dashboard'
            else:
                # Normal users go to home page, NOT dashboard
                redirect_url = '/'
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'redirect': redirect_url,
                'role': user_data.get('role', 'user')
            }), 200
        else:
            # Log failed login attempt for admin emails
            if email == 'ayushbhoir114@gmail.com':
                log_admin_action(admin_logs_collection, email, 'failed_login', {
                    'ip_address': request.remote_addr,
                    'reason': message
                })
            return jsonify({
                'success': False,
                'message': message
            }), 401
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during login'
        }), 500


@app.route('/register', methods=['GET'])
def register_page():
    """
    Render the registration page.
    """
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register():
    """
    Handle user registration with email and password.
    Automatically logs in the user after successful registration.
    """
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400
        
        # Register user in MongoDB
        success, message, user_id = register_user(users_collection, email, password)
        
        if success:
            # Automatically log in the user by creating a session
            # Get the user data from database
            user = users_collection.find_one({'user_id': user_id})
            
            if user:
                # Create session (must include 'logged_in' for login_required decorator)
                session['logged_in'] = True
                session['user_id'] = user['user_id']
                session['email'] = user['email']
                session['role'] = user.get('role', 'user')
                session['plan'] = user.get('plan', 'free')  # Add plan to session
                
                # Update last login
                users_collection.update_one(
                    {'user_id': user_id},
                    {'$set': {'last_login': datetime.utcnow()}}
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Registration successful! Redirecting to home...',
                    'user_id': user_id,
                    'redirect': '/'  # Redirect to home page (root route)
                }), 201
            else:
                # Fallback if user not found (shouldn't happen)
                return jsonify({
                    'success': True,
                    'message': message,
                    'user_id': user_id,
                    'redirect': '/login'
                }), 201
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during registration'
        }), 500


@app.route('/logout')
def logout():
    """
    Handle user logout.
    """
    session.clear()
    return redirect(url_for('home'))


@app.route('/auth/google')
def google_login():
    """
    Initiate Google OAuth login flow.
    """
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/auth/google/callback')
def google_callback():
    """
    Handle Google OAuth callback and create/login user.
    """
    try:
        # Get OAuth token
        print("🔄 Processing Google OAuth callback...")
        token = google.authorize_access_token()
        
        # Get user info from Google
        user_info = token.get('userinfo')
        
        if not user_info:
            print("❌ Google OAuth: No user info received")
            print(f"   Token data: {token}")
            return redirect(url_for('login') + '?error=oauth_failed')
        
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0] if email else 'User')
        
        if not email:
            print("❌ Google OAuth: No email in user info")
            print(f"   User info: {user_info}")
            return redirect(url_for('login') + '?error=no_email')
        
        print(f"✓ Google OAuth: User authenticated - {email}")
        
        # Check if user exists
        existing_user = users_collection.find_one({'email': email})
        
        if existing_user:
            # User exists, log them in
            user_id = existing_user['user_id']
            user_plan = existing_user.get('plan', 'free')
            user_role = existing_user.get('role', 'user')
            print(f"✓ Existing user found: {email} (Plan: {user_plan})")
        else:
            # Create new user with OAuth
            from uuid import uuid4
            from pricing_config import DEFAULT_PLAN, get_plan_credits
            from datetime import timedelta
            
            user_id = str(uuid4())
            now = datetime.utcnow()
            
            # Get default plan credits
            default_credits = get_plan_credits(DEFAULT_PLAN)
            reset_date = now + timedelta(days=30)
            
            new_user = {
                'user_id': user_id,
                'email': email,
                'name': name,
                'password': None,  # OAuth users don't have passwords
                'auth_provider': 'google',
                'role': 'user',
                'status': 'active',
                'created_at': now,
                'last_login': now,
                'total_scans': 0,
                # Pricing & Credits (Enhanced)
                'plan': DEFAULT_PLAN,
                'total_credits': default_credits,
                'credits_used': 0,
                'credits_remaining': default_credits,
                'plan_activated_at': now,
                'reset_at': reset_date if default_credits != -1 else None,
                'last_credit_renewal': now,
                'next_credit_renewal': reset_date if default_credits != -1 else None,
                'low_credit_alert_sent': False,
                'updated_at': now
            }
            
            users_collection.insert_one(new_user)
            user_plan = DEFAULT_PLAN
            user_role = 'user'
            print(f"✓ New OAuth user created: {email} (Plan: {user_plan})")
        
        # Update last login
        users_collection.update_one(
            {'user_id': user_id},
            {'$set': {'last_login': datetime.utcnow()}}
        )
        
        # Set session
        session['logged_in'] = True
        session['user_id'] = user_id
        session['email'] = email
        session['role'] = user_role
        session['plan'] = user_plan
        
        print(f"✓ Session created for: {email}")
        
        # Redirect based on role
        if user_role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('home'))
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Google OAuth error: {error_msg}")
        
        # Provide specific error messages for common issues
        if 'redirect_uri_mismatch' in error_msg.lower():
            print("   ⚠️  REDIRECT URI MISMATCH")
            print("   Fix: Add this URI to Google Console:")
            print("   http://localhost:5000/auth/google/callback")
        elif 'invalid_client' in error_msg.lower():
            print("   ⚠️  INVALID CLIENT CREDENTIALS")
            print("   Fix: Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
        elif 'access_denied' in error_msg.lower():
            print("   ⚠️  ACCESS DENIED")
            print("   Fix: Add your email as a test user in OAuth consent screen")
        
        import traceback
        traceback.print_exc()
        return redirect(url_for('login') + '?error=oauth_error')


@app.route('/')
def home():
    """
    Render the home/landing page (public, default page).
    SINGLE SOURCE OF TRUTH: Uses get_user_plan_state() helper.
    """
    from user_plan_helper import get_user_plan_state
    
    is_logged_in = 'logged_in' in session
    user_email = session.get('email', '') if is_logged_in else ''
    user_credits = 0
    user_plan = 'free'
    
    if is_logged_in:
        user_id = session.get('user_id')
        
        # Get complete plan state from database (SINGLE SOURCE OF TRUTH)
        plan_state = get_user_plan_state(users_collection, user_id)
        
        if plan_state:
            user_credits = plan_state['credits_remaining']
            user_plan = plan_state['plan_name']
    
    return render_template('home.html', 
                         is_logged_in=is_logged_in, 
                         user_email=user_email,
                         user_credits=user_credits,
                         user_plan=user_plan)



# Removed unused routes: /features, /how-it-works, /about
# These sections are implemented as anchor links on the home page (home.html)
# See lines 116-237 in home.html for the actual content


@app.route('/terms')
def terms():
    """
    Render the Terms & Conditions page.
    """
    is_logged_in = 'logged_in' in session
    return render_template('terms.html', is_logged_in=is_logged_in)


@app.route('/privacy')
def privacy():
    """
    Render the Privacy Policy page.
    """
    is_logged_in = 'logged_in' in session
    return render_template('privacy.html', is_logged_in=is_logged_in)


@app.route('/faq')
def faq():
    """
    Render the FAQ page.
    """
    is_logged_in = 'logged_in' in session
    return render_template('faq.html', is_logged_in=is_logged_in)


@app.route('/disclaimer')
def disclaimer():
    """
    Render the Disclaimer page.
    """
    is_logged_in = 'logged_in' in session
    return render_template('disclaimer.html', is_logged_in=is_logged_in)


@app.route('/contact')
def contact():
    """
    Render the Contact page.
    """
    is_logged_in = 'logged_in' in session
    user_email = session.get('email', '') if is_logged_in else ''
    return render_template('contact.html', is_logged_in=is_logged_in, user_email=user_email)


@app.route('/contact/message', methods=['POST'])
@login_required
def submit_contact_message():
    """
    Handle contact form submission.
    Only logged-in users can submit messages.
    Email is fetched from session, not from form data.
    """
    try:
        # Get message from request
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({
                'success': False,
                'message': 'Message cannot be empty'
            }), 400
        
        # Get user info from session (NOT from form)
        user_id = session.get('user_id')
        user_email = session.get('email')
        
        if not user_email:
            return jsonify({
                'success': False,
                'message': 'User email not found in session'
            }), 400
        
        # Create message document
        message_doc = {
            'user_id': user_id,
            'email': user_email,
            'message': message,
            'status': 'pending',
            'timestamp': datetime.utcnow(),
            'ip_address': request.remote_addr
        }
        
        # Save to MongoDB
        if messages_collection is not None:
            result = messages_collection.insert_one(message_doc)
            print(f"✓ Contact message saved from {user_email}")
            
            return jsonify({
                'success': True,
                'message': 'Your message has been sent successfully! We will get back to you soon.',
                'message_id': str(result.inserted_id)
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Database not available'
            }), 500
            
    except Exception as e:
        print(f"Error saving contact message: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while sending your message'
        }), 500


@app.route('/pricing')
def pricing():
    """
    Render the Pricing page with all available plans.
    SINGLE SOURCE OF TRUTH: Uses get_user_plan_state() helper.
    """
    from user_plan_helper import get_user_plan_state
    
    is_logged_in = 'logged_in' in session
    user = None
    plan_state = None
    
    if is_logged_in:
        user_id = session.get('user_id')
        
        # Get complete plan state from database (SINGLE SOURCE OF TRUTH)
        plan_state = get_user_plan_state(users_collection, user_id)
        
        if plan_state:
            # Create user object with plan state for template
            user = {
                'plan': plan_state['plan_name'],
                'total_credits': plan_state['total_credits'],
                'credits_remaining': plan_state['credits_remaining'],
                'credits_used': plan_state['credits_used'],
                'days_remaining': plan_state['days_remaining']
            }
    
    return render_template('pricing.html', 
                         is_logged_in=is_logged_in,
                         user=user)


@app.route('/api/change-plan', methods=['POST'])
@login_required
def change_plan():
    """
    Change user's pricing plan and update credits.
    """
    try:
        from credit_manager import update_user_plan
        from pricing_config import get_plan_config
        
        data = request.get_json()
        new_plan = data.get('plan', '').lower()
        
        # Validate plan
        plan_config = get_plan_config(new_plan)
        if not plan_config:
            return jsonify({
                'success': False,
                'message': 'Invalid plan selected'
            }), 400
        
        user_id = session.get('user_id')
        
        # Update plan
        success = update_user_plan(users_collection, user_id, new_plan)
        
        if success:
            # Update session if needed
            session['plan'] = new_plan
            
            return jsonify({
                'success': True,
                'message': f'Successfully upgraded to {plan_config["display_name"]} plan!',
                'new_credits': plan_config['credits_per_month']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update plan'
            }), 500
            
    except Exception as e:
        print(f"Error changing plan: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while changing your plan'
        }), 500


@app.route('/api/me')
@login_required
def get_current_user():
    """
    Get current authenticated user's complete information.
    This is the single source of truth for user state across all pages.
    Uses centralized get_user_plan_state() helper.
    
    Returns:
        JSON with complete user plan state
    """
    try:
        from user_plan_helper import get_user_plan_state
        
        user_id = session.get('user_id')
        
        # Get complete plan state from database (SINGLE SOURCE OF TRUTH)
        plan_state = get_user_plan_state(users_collection, user_id)
        
        if not plan_state:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Get user email
        user = users_collection.find_one({'user_id': user_id})
        
        # Build response with complete state
        user_data = {
            'success': True,
            'user_id': user_id,
            'email': user.get('email'),
            'plan': plan_state['plan_name'],
            'plan_display_name': plan_state['plan_name'].replace('_', ' ').title(),
            'total_credits': plan_state['total_credits'],
            'credits_remaining': plan_state['credits_remaining'],
            'credits_used': plan_state['credits_used'],
            'days_remaining': plan_state['days_remaining'],
            'plan_activated_at': plan_state['plan_activated_at'],
            'reset_at': plan_state['reset_at']
        }
        
        return jsonify(user_data), 200
        
    except Exception as e:
        print(f"Error getting user data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'An error occurred while fetching user data'
        }), 500


@app.route('/api/user/credits')
@login_required
def get_user_credits():
    """
    Get current user's credit state for scan page validation.
    This is the SINGLE SOURCE OF TRUTH for scan button state.
    
    Returns:
        JSON with:
        - credits_remaining: int
        - credits_used: int
        - total_credits: int
        - has_credits: bool (credits_remaining > 0)
    """
    try:
        from user_plan_helper import get_user_plan_state
        
        user_id = session.get('user_id')
        
        # Get complete plan state from database
        plan_state = get_user_plan_state(users_collection, user_id)
        
        if not plan_state:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Calculate has_credits
        credits_remaining = plan_state['credits_remaining']
        has_credits = credits_remaining > 0 or credits_remaining == -1  # -1 = unlimited
        
        return jsonify({
            'success': True,
            'credits_remaining': credits_remaining,
            'credits_used': plan_state['credits_used'],
            'total_credits': plan_state['total_credits'],
            'has_credits': has_credits
        }), 200
        
    except Exception as e:
        print(f"Error getting user credits: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'An error occurred while fetching credits'
        }), 500


@app.route('/api/credits/info')
@login_required
def get_credit_info():
    """
    Get comprehensive credit information for the logged-in user.
    Returns real-time credit status, usage, and reset information.
    """
    try:
        from credit_system import CreditManager
        from db import credit_logs_collection
        
        user_id = session.get('user_id')
        credit_manager = CreditManager(users_collection, credit_logs_collection)
        
        credit_info = credit_manager.get_user_credit_info(user_id)
        
        if credit_info is None:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            **credit_info
        }), 200
        
    except Exception as e:
        print(f"Error getting credit info: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while fetching credit information'
        }), 500


@app.route('/api/credits/usage')
@login_required
def get_credit_usage():
    """
    Get credit usage analytics for the logged-in user.
    Query params: range=daily|weekly|monthly
    """
    try:
        from credit_system import CreditManager
        from db import credit_logs_collection
        
        user_id = session.get('user_id')
        range_type = request.args.get('range', 'daily')
        
        if range_type not in ['daily', 'weekly', 'monthly']:
            return jsonify({
                'success': False,
                'message': 'Invalid range parameter. Use: daily, weekly, or monthly'
            }), 400
        
        credit_manager = CreditManager(users_collection, credit_logs_collection)
        usage_data = credit_manager.get_usage_analytics(user_id, range_type)
        
        return jsonify({
            'success': True,
            'range': range_type,
            'data': usage_data
        }), 200
        
    except Exception as e:
        print(f"Error getting credit usage: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while fetching usage data'
        }), 500


# ============================================================================
# STRIPE PAYMENT ROUTES
# ============================================================================

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """
    Create a Stripe Checkout Session for subscription payment.
    Accepts plan_id and creates a recurring subscription.
    """
    try:
        from stripe_config import (
            STRIPE_SECRET_KEY, 
            get_stripe_price_id, 
            validate_plan_for_stripe,
            SUCCESS_URL,
            CANCEL_URL
        )
        
        # Initialize Stripe
        stripe.api_key = STRIPE_SECRET_KEY
        
        # Debug: Check if key is loaded
        if not STRIPE_SECRET_KEY or len(STRIPE_SECRET_KEY) < 20:
            print(f"⚠️ WARNING: Stripe Secret Key appears invalid or empty!")
            print(f"   Key length: {len(STRIPE_SECRET_KEY) if STRIPE_SECRET_KEY else 0}")
            return jsonify({
                'success': False,
                'message': 'Stripe is not properly configured. Please check your .env file and restart the app.'
            }), 500
        
        print(f"✓ Stripe initialized with key: {STRIPE_SECRET_KEY[:20]}...{STRIPE_SECRET_KEY[-10:]}")
        
        # Get plan from request
        data = request.get_json()
        plan_id = data.get('plan_id', '').lower()
        
        if not plan_id:
            return jsonify({
                'success': False,
                'message': 'Plan ID is required'
            }), 400
        
        # Validate plan supports Stripe
        is_valid, error_msg = validate_plan_for_stripe(plan_id)
        if not is_valid:
            # Provide helpful error message
            if 'not configured' in error_msg.lower():
                return jsonify({
                    'success': False,
                    'message': f'⚠️ Stripe payment is not configured yet.\n\nTo enable payments:\n1. Sign up at stripe.com\n2. Get your API keys\n3. Create products in Stripe Dashboard\n4. Update .env file with your credentials\n\nSee STRIPE_QUICKSTART.md for details.'
                }), 400
            else:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 400
        
        # Get Stripe Price ID
        price_id = get_stripe_price_id(plan_id)
        
        # Get user info
        user_id = session.get('user_id')
        user_email = session.get('email')
        
        # Create Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            customer_email=user_email,
            metadata={
                'user_id': user_id,
                'plan': plan_id
            },
            success_url=SUCCESS_URL,
            cancel_url=CANCEL_URL,
            subscription_data={
                'metadata': {
                    'user_id': user_id,
                    'plan': plan_id
                }
            }
        )
        
        print(f"✓ Checkout session created for {user_email}: {plan_id} plan")
        
        return jsonify({
            'success': True,
            'session_id': checkout_session.id,
            'session_url': checkout_session.url
        }), 200
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Payment error: {str(e)}'
        }), 500
    except Exception as e:
        print(f"Error creating checkout session: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while creating checkout session'
        }), 500


@app.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events.
    Verifies webhook signature and processes events.
    """
    try:
        from stripe_config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
        from stripe_webhooks import (
            handle_checkout_completed,
            handle_invoice_payment_succeeded,
            handle_subscription_deleted,
            handle_payment_failed
        )
        from db import credit_logs_collection, payments_collection
        
        # Initialize Stripe
        stripe.api_key = STRIPE_SECRET_KEY
        
        # Get webhook payload and signature
        payload = request.data
        sig_header = request.headers.get('Stripe-Signature')
        
        if not sig_header:
            print("⚠️ Missing Stripe signature header")
            return jsonify({'error': 'Missing signature'}), 400
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError as e:
            print(f"⚠️ Webhook signature verification failed: {str(e)}")
            return jsonify({'error': 'Invalid signature'}), 400
        
        # Handle the event
        event_type = event['type']
        event_data = event['data']
        
        print(f"📥 Received Stripe webhook: {event_type}")
        
        # Route to appropriate handler
        if event_type == 'checkout.session.completed':
            success, message = handle_checkout_completed(
                event_data, 
                users_collection, 
                credit_logs_collection,
                payments_collection
            )
            
        elif event_type == 'invoice.payment_succeeded':
            success, message = handle_invoice_payment_succeeded(
                event_data,
                users_collection,
                credit_logs_collection,
                payments_collection
            )
            
        elif event_type == 'customer.subscription.deleted':
            success, message = handle_subscription_deleted(
                event_data,
                users_collection,
                credit_logs_collection
            )
            
        elif event_type == 'invoice.payment_failed':
            success, message = handle_payment_failed(
                event_data,
                users_collection
            )
            
        else:
            print(f"ℹ️ Unhandled webhook event: {event_type}")
            return jsonify({'received': True}), 200
        
        if success:
            print(f"✓ Webhook processed successfully: {message}")
            return jsonify({'received': True}), 200
        else:
            print(f"⚠️ Webhook processing failed: {message}")
            return jsonify({'error': message}), 500
            
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Webhook processing failed'}), 500


@app.route('/payment/success')
def payment_success():
    """
    Payment success page.
    CRITICAL: Verifies Stripe payment and updates user plan/credits.
    
    This is the BACKUP to webhook - ensures credits are added even if webhook fails.
    NOTE: Removed @login_required to handle Stripe redirects properly
    """
    from datetime import datetime, timedelta
    from pricing_config import get_plan_credits
    from stripe_config import STRIPE_SECRET_KEY
    
    session_id = request.args.get('session_id')
    
    # Check if user is logged in
    is_logged_in = 'logged_in' in session
    user_id = session.get('user_id') if is_logged_in else None
    
    if not session_id:
        print("⚠️ No session_id provided in payment success")
        # If not logged in, redirect to login
        if not is_logged_in:
            return redirect(url_for('login'))
        return render_template('payment_success.html',
                             is_logged_in=True,
                             user=get_current_user(),
                             session_id=None)
    
    try:
        # Initialize Stripe
        stripe.api_key = STRIPE_SECRET_KEY
        
        # VERIFY PAYMENT WITH STRIPE API
        print(f"🔍 Verifying Stripe session: {session_id}")
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Check payment status
        payment_status = checkout_session.payment_status
        print(f"Payment status: {payment_status}")
        
        if payment_status != 'paid':
            print(f"⚠️ Payment not completed. Status: {payment_status}")
            if not is_logged_in:
                return redirect(url_for('login'))
            return render_template('payment_success.html',
                                 is_logged_in=True,
                                 user=get_current_user(),
                                 session_id=session_id)
        
        # Get plan from metadata
        plan_name = checkout_session.metadata.get('plan')
        metadata_user_id = checkout_session.metadata.get('user_id')
        customer_email = checkout_session.customer_details.email
        
        print(f"✓ Payment verified! Plan: {plan_name}, User: {metadata_user_id}, Email: {customer_email}")
        
        # If user is not logged in, try to log them in using the email from Stripe
        if not is_logged_in and customer_email:
            user = users_collection.find_one({'email': customer_email})
            if user and user['user_id'] == metadata_user_id:
                # Auto-login the user
                session['logged_in'] = True
                session['user_id'] = user['user_id']
                session['email'] = user['email']
                session['role'] = user.get('role', 'user')
                session['plan'] = user.get('plan', 'free')
                is_logged_in = True
                user_id = user['user_id']
                print(f"✓ Auto-logged in user: {customer_email}")
        
        # Security check: ensure session user matches metadata user (if logged in)
        if is_logged_in and user_id and metadata_user_id != user_id:
            print(f"⚠️ User ID mismatch! Session: {user_id}, Metadata: {metadata_user_id}")
            return render_template('payment_success.html',
                                 is_logged_in=True,
                                 user=get_current_user(),
                                 session_id=session_id)
        
        # Check if this session was already processed (prevent double credit addition)
        user = users_collection.find_one({'user_id': user_id})
        
        if user.get('last_stripe_session_id') == session_id:
            print(f"✓ Session {session_id} already processed, skipping update")
        else:
            # UPDATE USER PLAN AND CREDITS IN DATABASE
            plan_credits = get_plan_credits(plan_name)
            now = datetime.utcnow()
            reset_at = now + timedelta(days=30)
            
            update_data = {
                'plan': plan_name,
                'total_credits': plan_credits,
                'credits_used': 0,
                'credits_remaining': plan_credits,
                'plan_activated_at': now,
                'reset_at': reset_at,
                'last_credit_renewal': now,
                'next_credit_renewal': reset_at,
                'stripe_customer_id': checkout_session.customer,
                'stripe_subscription_id': checkout_session.subscription,
                'payment_status': 'active',
                'last_payment_date': now,
                'last_stripe_session_id': session_id  # Prevent double processing
            }
            
            # Update user in database
            users_collection.update_one(
                {'user_id': user_id},
                {'$set': update_data}
            )
            
            # CREATE SALES RECORD FOR ADMIN PANEL
            try:
                # Get payment amount from checkout session
                amount_total = checkout_session.amount_total / 100 if checkout_session.amount_total else 0
                currency = checkout_session.currency.upper() if checkout_session.currency else 'INR'
                
                # Create payment record for revenue tracking
                payment_record = {
                    'user_id': user_id,
                    'email': user.get('email'),
                    'plan_name': plan_name,
                    'amount': amount_total,
                    'currency': currency,
                    'payment_id': checkout_session.payment_intent or session_id,
                    'stripe_session_id': session_id,
                    'stripe_customer_id': checkout_session.customer,
                    'stripe_subscription_id': checkout_session.subscription,
                    'payment_status': 'success',
                    'payment_method': checkout_session.payment_method_types[0] if checkout_session.payment_method_types else 'card',
                    'created_at': now,
                    'metadata': {
                        'credits_granted': plan_credits,
                        'plan_activated_at': now,
                        'next_renewal': reset_at,
                        'source': 'payment_success_page'
                    }
                }
                
                # Check if payment record already exists for this session
                existing_payment = payments_collection.find_one({'stripe_session_id': session_id})
                
                if not existing_payment:
                    payments_collection.insert_one(payment_record)
                    print(f"✅ SALES RECORD CREATED: ₹{amount_total} for {plan_name} plan")
                else:
                    print(f"⏭️  Sales record already exists for session {session_id}")
                    
            except Exception as sales_error:
                print(f"⚠️ Warning: Could not create sales record: {str(sales_error)}")
                # Don't fail the whole payment process if sales tracking fails
            
            print(f"✅ USER PLAN UPGRADED!")
            print(f"   User: {user.get('email')}")
            print(f"   Plan: {plan_name}")
            print(f"   Credits: {plan_credits}")
            print(f"   Activated: {now}")
            
            # Update session
            session['plan'] = plan_name
        
        # Refresh user data for template
        user = users_collection.find_one({'user_id': user_id})
        
        return render_template('payment_success.html',
                             is_logged_in=True,
                             session_id=session_id,
                             plan_name=plan_name,
                             credits=user.get('credits_remaining', 0))
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error during verification: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Still show success page but log error
        return render_template('payment_success.html',
                             is_logged_in=True,
                             session_id=session_id)
    
    except Exception as e:
        print(f"❌ Error processing payment success: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return render_template('payment_success.html',
                             is_logged_in=True,
                             session_id=session_id)


@app.route('/payment/cancel')
@login_required
def payment_cancel():
    """
    Payment cancellation page.
    Displayed when user cancels Stripe checkout.
    """
    return render_template('payment_cancel.html',
                         is_logged_in=True)


@app.route('/billing/portal')
@login_required
def billing_portal():
    """
    Redirect to Stripe Customer Portal for subscription management.
    """
    try:
        from stripe_config import STRIPE_SECRET_KEY
        
        stripe.api_key = STRIPE_SECRET_KEY
        
        # Get user
        user_id = session.get('user_id')
        user = users_collection.find_one({'user_id': user_id})
        
        if not user:
            return redirect(url_for('pricing'))
        
        # Get Stripe customer ID
        customer_id = user.get('stripe_customer_id')
        
        if not customer_id:
            return jsonify({
                'success': False,
                'message': 'No active subscription found'
            }), 404
        
        # Create portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=url_for('pricing', _external=True)
        )
        
        return redirect(portal_session.url)
        
    except Exception as e:
        print(f"Error creating portal session: {str(e)}")
        return redirect(url_for('pricing'))


# ============================================================================
# END STRIPE PAYMENT ROUTES
# ============================================================================


@app.route('/api/admin/credits/adjust', methods=['POST'])
@admin_required
def admin_adjust_credits():
    """
    Admin endpoint to manually adjust user credits.
    """
    try:
        from credit_system import CreditManager
        from db import credit_logs_collection
        
        data = request.get_json()
        target_user_id = data.get('user_id')
        adjustment = data.get('adjustment', 0)
        reason = data.get('reason', 'Admin adjustment')
        
        if not target_user_id:
            return jsonify({
                'success': False,
                'message': 'User ID is required'
            }), 400
        
        if not isinstance(adjustment, int) or adjustment == 0:
            return jsonify({
                'success': False,
                'message': 'Adjustment must be a non-zero integer'
            }), 400
        
        admin_id = session.get('user_id')
        credit_manager = CreditManager(users_collection, credit_logs_collection)
        
        success = credit_manager.admin_adjust_credits(
            target_user_id,
            adjustment,
            admin_id,
            reason
        )
        
        if success:
            # Log admin action
            log_admin_action(admin_logs_collection, session.get('email'), 'credit_adjustment', {
                'target_user_id': target_user_id,
                'adjustment': adjustment,
                'reason': reason
            })
            
            return jsonify({
                'success': True,
                'message': f'Credits adjusted by {adjustment:+d}'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to adjust credits'
            }), 500
            
    except Exception as e:
        print(f"Error adjusting credits: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while adjusting credits'
        }), 500


@app.route('/api/admin/credits/reset', methods=['POST'])
@admin_required
def admin_reset_credits():
    """
    Admin endpoint to manually reset user credits to their plan allocation.
    """
    try:
        from credit_system import CreditManager
        from db import credit_logs_collection
        
        data = request.get_json()
        target_user_id = data.get('user_id')
        
        if not target_user_id:
            return jsonify({
                'success': False,
                'message': 'User ID is required'
            }), 400
        
        credit_manager = CreditManager(users_collection, credit_logs_collection)
        success = credit_manager.reset_credits(target_user_id)
        
        if success:
            # Log admin action
            log_admin_action(admin_logs_collection, session.get('email'), 'credit_reset', {
                'target_user_id': target_user_id
            })
            
            return jsonify({
                'success': True,
                'message': 'Credits reset successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to reset credits'
            }), 500
            
    except Exception as e:
        print(f"Error resetting credits: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while resetting credits'
        }), 500


@app.route('/api/notifications/count')
@login_required
def get_notification_count():
    """
    Get count of unread notifications (replied messages) for logged-in user.
    """
    try:
        user_id = session.get('user_id')
        
        # Count replied messages that haven't been read by user
        unread_count = messages_collection.count_documents({
            'user_id': user_id,
            'status': 'replied',
            'read_by_user': {'$ne': True}
        })
        
        return jsonify({
            'success': True,
            'unread_count': unread_count
        }), 200
        
    except Exception as e:
        print(f"Error getting notification count: {str(e)}")
        return jsonify({
            'success': False,
            'unread_count': 0
        }), 500


@app.route('/api/notifications')
@login_required
def get_notifications():
    """
    Get all replied messages for logged-in user.
    """
    try:
        user_id = session.get('user_id')
        
        # Get all replied messages for this user
        notifications_cursor = messages_collection.find({
            'user_id': user_id,
            'status': 'replied'
        }).sort('replied_at', -1).limit(10)
        
        notifications = []
        for notif in notifications_cursor:
            notifications.append({
                'id': str(notif['_id']),
                'message': notif.get('message', ''),
                'admin_reply': notif.get('admin_reply', ''),
                'replied_at': notif.get('replied_at').strftime('%b %d, %Y') if notif.get('replied_at') else '',
                'replied_by': notif.get('replied_by', 'Admin'),
                'read': notif.get('read_by_user', False)
            })
        
        return jsonify({
            'success': True,
            'notifications': notifications
        }), 200
        
    except Exception as e:
        print(f"Error getting notifications: {str(e)}")
        return jsonify({
            'success': False,
            'notifications': []
        }), 500


@app.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    """
    Mark all replied messages as read for logged-in user.
    """
    try:
        user_id = session.get('user_id')
        
        # Update all replied messages to mark as read
        result = messages_collection.update_many(
            {
                'user_id': user_id,
                'status': 'replied',
                'read_by_user': {'$ne': True}
            },
            {
                '$set': {
                    'read_by_user': True,
                    'read_at': datetime.utcnow()
                }
            }
        )
        
        return jsonify({
            'success': True,
            'marked_count': result.modified_count
        }), 200
        
    except Exception as e:
        print(f"Error marking notifications as read: {str(e)}")
        return jsonify({
            'success': False
        }), 500


@app.route('/dashboard')
@login_required
def dashboard():
    """
    Render the user dashboard with scan statistics and history.
    Fetches real-time data from MongoDB for the logged-in user.
    
    URL Parameters:
    - filter: all, phishing, legitimate, suspicious
    - view: recent (default, 6 items), full (all items)
    
    Default: Shows last 6 scans (recent activity)
    Card clicks: Show all scans with applied filter
    """
    user_id = session.get('user_id')
    user_email = session.get('email', '')
    
    # Get parameters from URL
    active_filter = request.args.get('filter', 'recent')  # 'recent' is default (no filter, limited)
    view_mode = request.args.get('view', 'recent')  # 'recent' or 'full'
    
    # Determine if we're showing recent activity or full history
    is_recent_view = (active_filter == 'recent' and view_mode == 'recent')
    show_all = (view_mode == 'full' or active_filter in ['all', 'phishing', 'legitimate', 'suspicious'])
    
    # Get user's scan statistics from MongoDB
    total_scans = 0
    phishing_count = 0
    legitimate_count = 0
    suspicious_count = 0
    last_scan_time = "No scans yet"
    recent_scans = []
    detection_layers = ["ML", "WHOIS", "Blacklist"]
    
    try:
        if scans_collection is not None:
            # Count total scans by user
            total_scans = scans_collection.count_documents({'user_id': user_id})
            
            # Count by result type - Phishing
            phishing_count = scans_collection.count_documents({
                'user_id': user_id,
                'prediction': {'$in': ['Phishing', 'phishing']}
            })
            
            # Count by result type - Legitimate/Safe
            legitimate_count = scans_collection.count_documents({
                'user_id': user_id,
                'prediction': {'$in': ['Legitimate', 'legitimate', 'Safe', 'safe']}
            })
            
            # Count by result type - Suspicious
            suspicious_count = scans_collection.count_documents({
                'user_id': user_id,
                'prediction': {'$in': ['Suspicious', 'suspicious']}
            })
            
            # Build query based on filter
            query = {'user_id': user_id}
            
            if active_filter == 'phishing':
                query['prediction'] = {'$in': ['Phishing', 'phishing']}
            elif active_filter == 'legitimate':
                query['prediction'] = {'$in': ['Legitimate', 'legitimate', 'Safe', 'safe']}
            elif active_filter == 'suspicious':
                query['prediction'] = {'$in': ['Suspicious', 'suspicious']}
            # 'all' and 'recent' filters show all types
            
            # Determine limit based on view mode
            # Default (recent): 6 items, Card click (full): no limit
            if is_recent_view:
                scan_limit = 6
            else:
                scan_limit = 100  # Practical limit for full view
            
            # Get scans sorted by timestamp descending
            recent_cursor = scans_collection.find(query).sort('timestamp', -1).limit(scan_limit)
            
            for scan in recent_cursor:
                timestamp = scan.get('timestamp', datetime.utcnow())
                scan_data = {
                    'url': scan.get('url', 'Unknown'),
                    'result': scan.get('prediction', 'Unknown'),
                    'confidence': scan.get('confidence', 0),
                    'date': timestamp.strftime('%b %d, %Y') if timestamp else 'Unknown'
                }
                recent_scans.append(scan_data)
            
            # Get last scan date (date only, no time)
            last_scan = scans_collection.find_one(
                {'user_id': user_id},
                sort=[('timestamp', -1)]
            )
            if last_scan and 'timestamp' in last_scan:
                last_scan_time = last_scan['timestamp'].strftime('%b %d, %Y')
                
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
                
    # Get scan report download status
    has_downloaded_report = False
    try:
        if users_collection is not None:
            user_doc = users_collection.find_one({'user_id': user_id}, {'has_downloaded_report': 1})
            if user_doc:
                has_downloaded_report = user_doc.get('has_downloaded_report', False)
    except Exception as e:
        print(f"Error checking download status: {str(e)}")
    
    return render_template('dashboard.html',
                         user_email=user_email,
                         total_scans=total_scans,
                         phishing_count=phishing_count,
                         legitimate_count=legitimate_count,
                         suspicious_count=suspicious_count,
                         last_scan_time=last_scan_time,
                         recent_scans=recent_scans,
                         detection_layers=detection_layers,
                         active_filter=active_filter,
                         is_recent_view=is_recent_view,
                         show_all=show_all,
                         user_plan=session.get('plan', 'free'),
                         has_downloaded_report=has_downloaded_report)


@app.route('/api/download-report', methods=['GET'])
@login_required
def download_report():
    """
    Generate and download a PDF or Word report of scan history.
    
    Query Parameters:
        - type: 'all', 'phishing', 'legitimate' (default: 'all')
        - range: '7', '30', 'all' (default: 'all')
        - format: 'pdf', 'docx' (default: 'pdf')
    
    Returns:
        PDF or Word file download
    """
    try:
        from report_generator import generate_scan_report
        from word_generator import generate_word_report
        from flask import send_file
        from datetime import timedelta
        
        user_id = session.get('user_id')
        user_email = session.get('email', 'user@example.com')
        user_plan = session.get('plan', 'free')
        
        # Plan-based access control for report downloads
        if user_plan == 'free':
            user_doc = users_collection.find_one({'user_id': user_id})
            if user_doc and user_doc.get('has_downloaded_report'):
                return jsonify({
                    'success': False,
                    'code': 'DOWNLOAD_LIMIT_REACHED',
                    'message': 'Free plan allows only one report download. Upgrade to continue.'
                }), 403

        # Get filter parameters
        report_type = request.args.get('type', 'all').lower()
        date_range = request.args.get('range', 'all').lower()
        file_format = request.args.get('format', 'pdf').lower()
        
        # Validate report type
        if report_type not in ['all', 'phishing', 'legitimate']:
            return jsonify({
                'success': False,
                'message': 'Invalid report type. Use: all, phishing, or legitimate'
            }), 400
        
        # Validate file format
        if file_format not in ['pdf', 'docx']:
            return jsonify({
                'success': False,
                'message': 'Invalid file format. Use: pdf or docx'
            }), 400
        
        # Build query for scans
        query = {'user_id': user_id}
        
        # Apply report type filter
        if report_type == 'phishing':
            query['prediction'] = {'$in': ['Phishing', 'phishing']}
        elif report_type == 'legitimate':
            query['prediction'] = {'$in': ['Legitimate', 'legitimate', 'Safe', 'safe']}
        # 'all' includes everything
        
        # Apply date range filter
        if date_range in ['7', '30']:
            days = int(date_range)
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query['timestamp'] = {'$gte': cutoff_date}
        # 'all' includes all dates
        
        # Fetch scans from database
        if scans_collection is None:
            return jsonify({
                'success': False,
                'message': 'Database not available'
            }), 500
        
        scans_cursor = scans_collection.find(query).sort('timestamp', -1)
        scans_data = list(scans_cursor)
        
        # Check if user has any scans
        if not scans_data:
            return jsonify({
                'success': False,
                'message': 'No scans found matching your criteria. Please scan some URLs first.'
            }), 404
        
        # Generate report based on format
        if file_format == 'docx':
            # Generate Word document
            doc_buffer = generate_word_report(
                user_email=user_email,
                user_plan=user_plan,
                scans_data=scans_data,
                report_type=report_type,
                date_range=date_range
            )
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            extension = 'docx'
        else:
            # Generate PDF document
            doc_buffer = generate_scan_report(
                user_email=user_email,
                user_plan=user_plan,
                scans_data=scans_data,
                report_type=report_type,
                date_range=date_range
            )
            mimetype = 'application/pdf'
            extension = 'pdf'
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"SafeNet_AI_Report_{report_type}_{timestamp}.{extension}"
        
        print(f"✓ Generated {extension.upper()} report for {user_email}: {len(scans_data)} scans")
        print(f"  Filename: {filename}")
        print(f"  Size: {len(doc_buffer.getvalue())} bytes")
        
        # Mark as downloaded for free users if successful
        if user_plan == 'free':
            users_collection.update_one(
                {'user_id': user_id},
                {'$set': {'has_downloaded_report': True}}
            )
            print(f"  Plan: FREE - Download limit reached for {user_email}")

        # Create response with explicit headers
        response = send_file(
            doc_buffer,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
        # Add explicit headers to force download
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'An error occurred while generating the report'
        }), 500



@app.route('/scan')
@login_required
def scan():
    """
    Render the URL scanning page (protected).
    """
    user_plan = session.get('plan', 'free')
    return render_template('scan.html', user_plan=user_plan)



@app.route('/predict', methods=['POST'])
@login_required
def predict():
    """
    API endpoint for URL prediction.
    
    Expected JSON input:
    {
        "url": "https://example.com"
    }
    
    Returns:
    {
        "success": true/false,
        "url": "original URL",
        "prediction": "Phishing" or "Legitimate",
        "confidence": 0.95,
        "whois": {...},
        "features": {...},
        "message": "status message"
    }
    """
    try:
        # ========== CREDIT MANAGEMENT ==========
        from credit_manager import has_credits, deduct_credit, check_and_renew_credits
        
        user_id = session.get('user_id')
        
        # Check and renew credits if needed (30-day cycle)
        check_and_renew_credits(users_collection, user_id)
        
        # Check if user has available credits
        has_creds, current_credits = has_credits(users_collection, user_id)
        if not has_creds:
            return jsonify({
                'success': False,
                'message': 'Credits exhausted. Please upgrade your plan to continue scanning.',
                'credits_remaining': 0,
                'upgrade_required': True
            }), 403
        
        print(f"[CREDITS] User has {current_credits} credits available")
        
        # Get URL from request
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({
                'success': False,
                'message': 'Please provide a URL to check.'
            }), 400
        
        # Validate URL format (NO credit deduction for invalid URLs)
        if not validate_url(url):
            return jsonify({
                'success': False,
                'message': 'Invalid URL format. Please enter a valid URL.'
            }), 400
        
        # ========== GENERATE UNIQUE SCAN ID ==========
        import time
        scan_id = f"scan_{int(time.time() * 1000)}_{user_id[:8]}"  # timestamp_ms + user_id prefix
        print(f"[SCAN] Generated scan_id: {scan_id}")
        
        # Ensure URL has scheme
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        # Extract features from URL
        print(f"\nAnalyzing URL: {url}")
        features = extract_url_features(url)
        
        # Get WHOIS information
        parsed = urlparse(url)
        domain = parsed.netloc
        ext = tldextract.extract(url)
        clean_domain = f"{ext.domain}.{ext.suffix}"
        
        # Get enhanced WHOIS information (returns dict)
        whois_data = get_whois_info(domain)
        
        # Calculate domain age in years/days for display
        domain_age_display = 'Not Available'
        if whois_data['domain_age_days'] > 0:
            years = whois_data['domain_age_days'] // 365
            days = whois_data['domain_age_days'] % 365
            if years > 0:
                domain_age_display = f"{years} years, {days} days"
            else:
                domain_age_display = f"{days} days"
        
        whois_info = {
            'domain': whois_data.get('domain_name', clean_domain),
            'domain_age_days': whois_data['domain_age_days'],
            'domain_age_display': domain_age_display,
            'registrar': whois_data['registrar'],
            'creation_date': whois_data.get('creation_date', 'Not Available'),
            'expiry_date': whois_data['expiry_date'],
            'registration_length_days': whois_data['registration_length_days'],
            'privacy_protection': 'Yes' if whois_data['privacy_protection_flag'] == 1 else 'No'
        }
        
        # Prepare features for prediction (ALL 31 FEATURES IN CORRECT ORDER)
        feature_names = [
            'url_length', 'num_dots', 'num_hyphens', 'num_underscores',
            'num_slashes', 'num_questionmarks', 'num_equals', 'num_at',
            'num_ampersand', 'num_exclamation', 'num_tilde', 'num_percent',
            'num_special_chars_total',  # NEW
            'has_https', 'has_ip', 'subdomain_count', 'domain_length',
            'path_length', 'query_length', 'special_char_ratio',
            'url_entropy', 'digit_ratio', 'letter_ratio',
            'uppercase_ratio',  # NEW
            'consecutive_consonants_max',  # NEW
            'tld_suspicious',  # NEW
            'has_suspicious_words', 'domain_age_days',
            'registration_length_days',  # NEW
            'privacy_protection_flag',  # NEW
            'registrar_reputation',  # NEW
            'is_shortened'
        ]
        
        # Create feature vector in correct order
        feature_vector = np.array([[features.get(f, 0) for f in feature_names]])
        
        # Verify feature count
        expected_features = 31
        if feature_vector.shape[1] != expected_features:
            print(f"⚠️  WARNING: Feature count mismatch! Expected {expected_features}, got {feature_vector.shape[1]}")
        
        # Scale features
        feature_vector_scaled = scaler.transform(feature_vector)
        
        # ========== TIERED DETECTION: 3-LAYER APPROACH ==========
        # Use the tiered detection engine for comprehensive analysis
        tiered_result = tiered_engine.detect(url, features, feature_vector_scaled)
        
        # Extract results from tiered detection
        final_classification = tiered_result['final_classification']
        final_confidence = tiered_result['final_confidence']
        processing_time = tiered_result['processing_time_ms']
        detection_path = tiered_result['detection_path']
        
        # Get layer-specific results
        layer1 = tiered_result['layers']['layer1_ml']
        layer2 = tiered_result['layers']['layer2_blacklist']
        layer3 = tiered_result['layers']['layer3_content']
        
        # Map classification to old format for compatibility
        if final_classification == "Safe":
            final_result = "Legitimate"
        elif final_classification == "Phishing":
            final_result = "Phishing"
        else:  # Suspicious
            final_result = "Suspicious"
        
        # Build warnings list
        warnings = []
        
        # Add blacklist warning
        if layer2['is_blacklisted']:
            warnings.append(f"⚠️ Blacklisted by {layer2['source']}: {layer2['details']}")
        
        # Add content analysis warnings
        if layer3 and layer3['success']:
            for indicator in layer3['indicators']:
                warnings.append(f"Content: {indicator}")
        
        # Add rule-based warnings (keep existing logic for trusted domains, etc.)
        parsed = urlparse(url)
        domain = parsed.netloc
        ext = tldextract.extract(url)
        clean_domain = f"{ext.domain}.{ext.suffix}"
        is_trusted = is_trusted_domain(domain, clean_domain)
        
        if is_trusted and final_result == "Phishing":
            warnings.append(f"Note: {clean_domain} is a trusted domain - review carefully")
        
        # Prepare comprehensive response
        response = {
            'success': True,
            'scan_id': scan_id,  # Unique identifier for this scan session
            'url': url,
            'prediction': final_result,
            'confidence': round(final_confidence, 2),
            'processing_time_ms': processing_time,
            'detection_method': 'Tiered Detection (3 Layers)',
            'detection_path': detection_path,
            'warnings': warnings,
            
            # Layer 1: ML Detection
            'ml_detection': {
                'classification': layer1['classification'],
                'phishing_probability': round(layer1['phishing_prob'] * 100, 2),
                'legitimate_probability': round(layer1['legitimate_prob'] * 100, 2),
                'confidence': round(layer1['confidence'], 2)
            },
            
            # Layer 2: Blacklist Check
            'blacklist_check': {
                'is_blacklisted': layer2['is_blacklisted'],
                'source': layer2['source'],
                'details': layer2['details']
            },
            
            # Layer 3: Content Analysis (if performed)
            'content_analysis': {
                'performed': tiered_result['content_analysis_performed'],
                'risk_score': layer3['risk_score'] if layer3 and layer3['success'] else None,
                'indicators': layer3['indicators'] if layer3 and layer3['success'] else [],
                'details': layer3['details'] if layer3 else None
            } if tiered_result['content_analysis_performed'] else None,
            
            # WHOIS and Features
            'whois': whois_info,
            'features': {
                'url_length': features.get('url_length', 0),
                'has_https': bool(features.get('has_https', 0)),
                'has_ip_address': bool(features.get('has_ip', 0)),
                'subdomain_count': features.get('subdomain_count', 0),
                'domain_age_days': whois_data['domain_age_days'],
                'has_suspicious_words': bool(features.get('has_suspicious_words', 0)),
                'is_shortened': bool(features.get('is_shortened', 0)),
                'tld_suspicious': bool(features.get('tld_suspicious', 0)),
                'uppercase_ratio': round(features.get('uppercase_ratio', 0), 3),
                'privacy_protection': whois_info['privacy_protection']
            },
            'message': _get_result_message(final_result, tiered_result)
        }
        
        # ========== SAVE SCAN RESULT TO DATABASE ==========
        try:
            from datetime import datetime
            scan_record = {
                'user_id': session.get('user_id', 'unknown'),
                'email': session.get('email', 'unknown'),
                'url': url,
                'domain': clean_domain,
                'prediction': final_result,
                'confidence': round(final_confidence, 2),
                'processing_time_ms': processing_time,
                'detection_method': 'Tiered Detection (3 Layers)',
                'detection_path': detection_path,
                'ml_classification': layer1['classification'],
                'ml_phishing_prob': round(layer1['phishing_prob'] * 100, 2),
                'is_blacklisted': layer2['is_blacklisted'],
                'blacklist_source': layer2['source'],
                'content_analysis_performed': tiered_result['content_analysis_performed'],
                'content_risk_score': layer3['risk_score'] if layer3 and layer3['success'] else None,
                'warnings': warnings,
                'whois_info': whois_info,
                'timestamp': datetime.utcnow(),
                'ip_address': request.remote_addr
            }
            
            # Insert into MongoDB
            if scans_collection is not None:
                scans_collection.insert_one(scan_record)
                print(f"✓ Scan result saved to database for user: {session.get('email', 'unknown')}")
            
        except Exception as db_error:
            print(f"⚠️  Failed to save scan to database: {str(db_error)}")
            # Don't fail the request if database save fails
        
        # ========== DEDUCT CREDIT AFTER SUCCESSFUL SCAN ==========
        success_deduct, remaining_credits = deduct_credit(users_collection, user_id, 1)
        if success_deduct:
            print(f"[CREDITS] Deducted 1 credit. Remaining: {remaining_credits}")
        else:
            print(f"[CREDITS] Failed to deduct credit")
        
        # Get updated user state for complete credit info
        from user_plan_helper import get_user_plan_state
        plan_state = get_user_plan_state(users_collection, user_id)
        
        # Add complete credits info to response
        if plan_state:
            response['credits_remaining'] = plan_state['credits_remaining']
            response['credits_used'] = plan_state['credits_used']
            response['total_credits'] = plan_state['total_credits']
            response['has_credits'] = plan_state['credits_remaining'] > 0 or plan_state['credits_remaining'] == -1
        else:
            response['credits_remaining'] = remaining_credits
            response['has_credits'] = remaining_credits > 0
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error during prediction: {str(e)}")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'An error occurred while analyzing the URL: {str(e)}'
        }), 500


def _get_result_message(final_result, tiered_result):
    """
    Generate a user-friendly message based on detection results.
    
    Args:
        final_result (str): Final classification
        tiered_result (dict): Tiered detection result
        
    Returns:
        str: User-friendly message
    """
    content_performed = tiered_result['content_analysis_performed']
    blacklisted = tiered_result['layers']['layer2_blacklist']['is_blacklisted']
    
    if final_result == "Phishing":
        if blacklisted:
            source = tiered_result['layers']['layer2_blacklist']['source']
            return f"⚠️ PHISHING DETECTED! This URL is blacklisted by {source}. Do not visit this site."
        elif content_performed:
            return "⚠️ PHISHING DETECTED! Multiple suspicious indicators found in content analysis."
        else:
            return "⚠️ PHISHING DETECTED! High probability based on URL analysis."
    
    elif final_result == "Suspicious":
        if content_performed:
            return "⚠️ SUSPICIOUS URL. Some phishing indicators detected. Proceed with caution."
        else:
            return "⚠️ SUSPICIOUS URL. Medium phishing probability. Exercise caution."
    
    else:  # Legitimate/Safe
        return "✓ URL appears to be SAFE based on comprehensive analysis."


@app.route('/api/scan-history', methods=['GET'])
@login_required
def get_scan_history():
    """
    Get scan history for the logged-in user.
    Supports pagination and filtering.
    """
    try:
        user_id = session.get('user_id')
        
        # Get query parameters
        limit = int(request.args.get('limit', 50))
        skip = int(request.args.get('skip', 0))
        prediction_filter = request.args.get('prediction', None)  # 'Phishing', 'Legitimate', 'Suspicious'
        
        # Build query
        query = {'user_id': user_id}
        if prediction_filter:
            query['prediction'] = prediction_filter
        
        # Get scans from database
        scans = list(scans_collection.find(query)
                    .sort('timestamp', -1)
                    .skip(skip)
                    .limit(limit))
        
        # Convert ObjectId to string for JSON serialization
        for scan in scans:
            scan['_id'] = str(scan['_id'])
            # Format timestamp
            if 'timestamp' in scan:
                scan['timestamp'] = scan['timestamp'].isoformat()
        
        # Get total count
        total_count = scans_collection.count_documents(query)
        
        return jsonify({
            'success': True,
            'scans': scans,
            'total': total_count,
            'limit': limit,
            'skip': skip
        }), 200
        
    except Exception as e:
        print(f"Error fetching scan history: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching scan history: {str(e)}'
        }), 500


@app.route('/api/user-stats', methods=['GET'])
@login_required
def get_user_stats():
    """
    Get statistics for the logged-in user.
    """
    try:
        user_id = session.get('user_id')
        
        # Get total scans
        total_scans = scans_collection.count_documents({'user_id': user_id})
        
        # Get counts by prediction
        phishing_count = scans_collection.count_documents({'user_id': user_id, 'prediction': 'Phishing'})
        legitimate_count = scans_collection.count_documents({'user_id': user_id, 'prediction': 'Legitimate'})
        suspicious_count = scans_collection.count_documents({'user_id': user_id, 'prediction': 'Suspicious'})
        
        # Get recent scans
        recent_scans = list(scans_collection.find({'user_id': user_id})
                           .sort('timestamp', -1)
                           .limit(5))
        
        # Convert ObjectId to string
        for scan in recent_scans:
            scan['_id'] = str(scan['_id'])
            if 'timestamp' in scan:
                scan['timestamp'] = scan['timestamp'].isoformat()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_scans': total_scans,
                'phishing_detected': phishing_count,
                'legitimate_urls': legitimate_count,
                'suspicious_urls': suspicious_count,
                'recent_scans': recent_scans
            }
        }), 200
        
    except Exception as e:
        print(f"Error fetching user stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching user stats: {str(e)}'
        }), 500


@app.route('/api/admin/all-scans', methods=['GET'])
@login_required
def get_all_scans():
    """
    Admin endpoint to get all scans from all users.
    Requires admin role.
    """
    try:
        # Check if user is admin
        user_role = session.get('role', 'user')
        if user_role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Unauthorized. Admin access required.'
            }), 403
        
        # Get query parameters
        limit = int(request.args.get('limit', 100))
        skip = int(request.args.get('skip', 0))
        
        # Get all scans
        scans = list(scans_collection.find()
                    .sort('timestamp', -1)
                    .skip(skip)
                    .limit(limit))
        
        # Convert ObjectId to string
        for scan in scans:
            scan['_id'] = str(scan['_id'])
            if 'timestamp' in scan:
                scan['timestamp'] = scan['timestamp'].isoformat()
        
        total_count = scans_collection.count_documents({})
        
        return jsonify({
            'success': True,
            'scans': scans,
            'total': total_count,
            'limit': limit,
            'skip': skip
        }), 200
        
    except Exception as e:
        print(f"Error fetching all scans: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching scans: {str(e)}'
        }), 500


@app.route('/api/admin/users', methods=['GET'])
@login_required
def get_all_users():
    """
    Admin endpoint to get all registered users.
    Requires admin role.
    """
    try:
        # Check if user is admin
        user_role = session.get('role', 'user')
        if user_role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Unauthorized. Admin access required.'
            }), 403
        
        # Get all users (excluding passwords)
        users = list(users_collection.find({}, {'password': 0}))
        
        # Convert ObjectId to string and format dates
        for user in users:
            user['_id'] = str(user['_id'])
            if 'created_at' in user:
                user['created_at'] = user['created_at'].isoformat()
            if 'last_login' in user and user['last_login']:
                user['last_login'] = user['last_login'].isoformat()
            
            # Get scan count for each user
            user['total_scans'] = scans_collection.count_documents({'user_id': user['user_id']})
        
        return jsonify({
            'success': True,
            'users': users,
            'total': len(users)
        }), 200
        
    except Exception as e:
        print(f"Error fetching users: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching users: {str(e)}'
        }), 500


@app.route('/api/admin/stats', methods=['GET'])
@login_required
def get_admin_stats():
    """
    Admin endpoint to get overall system statistics.
    Requires admin role.
    """
    try:
        # Check if user is admin
        user_role = session.get('role', 'user')
        if user_role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Unauthorized. Admin access required.'
            }), 403
        
        # Get overall statistics
        total_users = users_collection.count_documents({})
        total_scans = scans_collection.count_documents({})
        total_phishing = scans_collection.count_documents({'prediction': 'Phishing'})
        total_legitimate = scans_collection.count_documents({'prediction': 'Legitimate'})
        total_suspicious = scans_collection.count_documents({'prediction': 'Suspicious'})
        
        # Get scans from last 24 hours
        from datetime import datetime, timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        scans_24h = scans_collection.count_documents({'timestamp': {'$gte': yesterday}})
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'total_scans': total_scans,
                'total_phishing_detected': total_phishing,
                'total_legitimate': total_legitimate,
                'total_suspicious': total_suspicious,
                'scans_last_24h': scans_24h,
                'detection_rate': round((total_phishing / total_scans * 100) if total_scans > 0 else 0, 2)
            }
        }), 200
        
    except Exception as e:
        print(f"Error fetching admin stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching stats: {str(e)}'
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify the service is running.
    """
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'model_info': model_metadata if model_metadata else None
    }), 200


# ============================================
# ADMIN DASHBOARD ROUTES
# ============================================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """
    Admin dashboard with real-time system analytics.
    All data fetched from MongoDB.
    """
    try:
        # System Overview Stats
        total_users = users_collection.count_documents({'role': {'$ne': 'admin'}})
        total_scans = scans_collection.count_documents({})
        phishing_count = scans_collection.count_documents({
            'prediction': {'$in': ['Phishing', 'phishing']}
        })
        legitimate_count = scans_collection.count_documents({
            'prediction': {'$in': ['Legitimate', 'legitimate', 'Safe', 'safe']}
        })
        
        # Get system config
        config = system_config_collection.find_one({'type': 'detection_settings'})
        if not config:
            # Initialize default config
            config = {
                'type': 'detection_settings',
                'ml_enabled': True,
                'whois_enabled': True,
                'blacklist_enabled': True
            }
            system_config_collection.insert_one(config)
        
        # Recent threat activity (latest 15 scans)
        recent_scans = list(scans_collection.find().sort('timestamp', -1).limit(15))
        for scan in recent_scans:
            scan['_id'] = str(scan['_id'])
            if 'timestamp' in scan:
                scan['date'] = scan['timestamp'].strftime('%b %d, %Y')
        
        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             total_scans=total_scans,
                             phishing_count=phishing_count,
                             legitimate_count=legitimate_count,
                             recent_scans=recent_scans,
                             config=config,
                             admin_email=session.get('email'))
    except Exception as e:
        print(f"Admin dashboard error: {str(e)}")
        return render_template('admin/dashboard.html',
                             total_users=0,
                             total_scans=0,
                             phishing_count=0,
                             legitimate_count=0,
                             recent_scans=[],
                             config={},
                             admin_email=session.get('email'))


# ============================================
# UNUSED ADMIN ROUTES (COMMENTED OUT)
# ============================================
# These routes are disabled to keep the admin panel minimal and clean.
# Only Dashboard and Messages are active.

@app.route('/admin/users')
@admin_required
def admin_users():
    """
    User management page - view all users and their stats.
    """
    try:
        users = list(users_collection.find({'role': {'$ne': 'admin'}}))
        
        for user in users:
            user['_id'] = str(user['_id'])
            # Count user's scans
            user['total_scans'] = scans_collection.count_documents({'user_id': user['user_id']})
            # Get last scan
            last_scan = scans_collection.find_one(
                {'user_id': user['user_id']},
                sort=[('timestamp', -1)]
            )
            if last_scan and 'timestamp' in last_scan:
                user['last_scan'] = last_scan['timestamp'].strftime('%b %d, %Y')
            else:
                user['last_scan'] = 'Never'
            # Format created date
            if 'created_at' in user:
                user['created_at_str'] = user['created_at'].strftime('%b %d, %Y')
            
            # Count total plans purchased (successful payments)
            user['total_plans_purchased'] = payments_collection.count_documents({
                'user_id': user['user_id'],
                'payment_status': 'success'
            })
        
        return render_template('admin/users.html', users=users, admin_email=session.get('email'))
    except Exception as e:
        print(f"Admin users error: {str(e)}")
        return render_template('admin/users.html', users=[], admin_email=session.get('email'))


# @app.route('/admin/users/<user_id>/toggle-status', methods=['POST'])
# @admin_required
# def toggle_user_status(user_id):
#     """
#     Block or unblock a user.
#     """
#     try:
#         user = users_collection.find_one({'user_id': user_id})
#         if not user:
#             return jsonify({'success': False, 'message': 'User not found'}), 404
#         
#         current_status = user.get('status', 'active')
#         new_status = 'blocked' if current_status == 'active' else 'active'
#         
#         users_collection.update_one(
#             {'user_id': user_id},
#             {'$set': {'status': new_status}}
#         )
#         
#         # Log admin action
#         log_admin_action(admin_logs_collection, session.get('email'), 
#                         'user_block' if new_status == 'blocked' else 'user_unblock',
#                         {'target_user': user['email'], 'user_id': user_id})
#         
#         return jsonify({
#             'success': True,
#             'message': f"User {'blocked' if new_status == 'blocked' else 'unblocked'} successfully",
#             'new_status': new_status
#         })
#     except Exception as e:
#         return jsonify({'success': False, 'message': str(e)}), 500


# @app.route('/admin/blacklist')
# @admin_required
# def admin_blacklist():
#     """
#     Blacklist management page.
#     """
#     try:
#         blacklist = list(blacklist_collection.find().sort('added_at', -1))
#         for item in blacklist:
#             item['_id'] = str(item['_id'])
#             if 'added_at' in item:
#                 item['added_at_str'] = item['added_at'].strftime('%b %d, %Y')
#         
#         return render_template('admin/blacklist.html', blacklist=blacklist, admin_email=session.get('email'))
#     except Exception as e:
#         print(f"Admin blacklist error: {str(e)}")
#         return render_template('admin/blacklist.html', blacklist=[], admin_email=session.get('email'))


# @app.route('/admin/blacklist/add', methods=['POST'])
# @admin_required
# def add_to_blacklist():
#     """
#     Add a URL/domain to the blacklist.
#     """
#     try:
#         data = request.get_json()
#         domain = data.get('domain', '').strip().lower()
#         
#         if not domain:
#             return jsonify({'success': False, 'message': 'Domain is required'}), 400
#         
#         # Extract clean domain
#         ext = tldextract.extract(domain)
#         clean_domain = f"{ext.domain}.{ext.suffix}"
#         
#         # Check if already exists
#         existing = blacklist_collection.find_one({'domain': clean_domain})
#         if existing:
#             return jsonify({'success': False, 'message': 'Domain already in blacklist'}), 400
#         
#         # Add to blacklist
#         blacklist_collection.insert_one({
#             'domain': clean_domain,
#             'source': 'Manual',
#             'added_by': session.get('email'),
#             'added_at': datetime.utcnow()
#         })
#         
#         # Log admin action
#         log_admin_action(admin_logs_collection, session.get('email'), 'blacklist_add',
#                         {'domain': clean_domain})
#         
#         return jsonify({
#             'success': True,
#             'message': f'{clean_domain} added to blacklist'
#         })
#     except Exception as e:
#         return jsonify({'success': False, 'message': str(e)}), 500


# @app.route('/admin/blacklist/remove', methods=['POST'])
# @admin_required
# def remove_from_blacklist():
#     """
#     Remove a URL/domain from the blacklist.
#     """
#     try:
#         data = request.get_json()
#         domain = data.get('domain', '')
#         
#         result = blacklist_collection.delete_one({'domain': domain})
#         
#         if result.deleted_count > 0:
#             # Log admin action
#             log_admin_action(admin_logs_collection, session.get('email'), 'blacklist_remove',
#                             {'domain': domain})
#             return jsonify({'success': True, 'message': f'{domain} removed from blacklist'})
#         else:
#             return jsonify({'success': False, 'message': 'Domain not found'}), 404
#     except Exception as e:
#         return jsonify({'success': False, 'message': str(e)}), 500


# @app.route('/admin/config/toggle', methods=['POST'])
# @admin_required
# def toggle_detection_config():
#     """
#     Toggle detection layer settings (ML, WHOIS, Blacklist).
#     """
#     try:
#         data = request.get_json()
#         setting = data.get('setting')
#         
#         if setting not in ['ml_enabled', 'whois_enabled', 'blacklist_enabled']:
#             return jsonify({'success': False, 'message': 'Invalid setting'}), 400
#         
#         # Get current config
#         config = system_config_collection.find_one({'type': 'detection_settings'})
#         if not config:
#             config = {
#                 'type': 'detection_settings',
#                 'ml_enabled': True,
#                 'whois_enabled': True,
#                 'blacklist_enabled': True
#             }
#             system_config_collection.insert_one(config)
#         
#         # Toggle the setting
#         new_value = not config.get(setting, True)
#         system_config_collection.update_one(
#             {'type': 'detection_settings'},
#             {'$set': {setting: new_value}}
#         )
#         
#         # Log admin action
#         log_admin_action(admin_logs_collection, session.get('email'), 'config_change',
#                         {'setting': setting, 'new_value': new_value})
#         
#         return jsonify({
#             'success': True,
#             'setting': setting,
#             'new_value': new_value
#         })
#     except Exception as e:
#         return jsonify({'success': False, 'message': str(e)}), 500


# @app.route('/admin/logs')
# @admin_required
# def admin_logs():
#     """
#     View admin audit logs.
#     """
#     try:
#         logs = list(admin_logs_collection.find().sort('timestamp', -1).limit(50))
#         for log in logs:
#             log['_id'] = str(log['_id'])
#             if 'timestamp' in log:
#                 log['timestamp_str'] = log['timestamp'].strftime('%b %d, %Y %I:%M %p')
#         
#         return render_template('admin/logs.html', logs=logs, admin_email=session.get('email'))
#     except Exception as e:
#         print(f"Admin logs error: {str(e)}")
#         return render_template('admin/logs.html', logs=[], admin_email=session.get('email'))



@app.route('/admin/messages')
@admin_required
def admin_messages():
    """
    Admin messages page - view all contact form submissions.
    """
    try:
        # Get all messages sorted by timestamp (newest first)
        messages_cursor = messages_collection.find().sort('timestamp', -1)
        messages = []
        
        for msg in messages_cursor:
            msg['_id'] = str(msg['_id'])
            if 'timestamp' in msg:
                msg['timestamp_str'] = msg['timestamp'].strftime('%b %d, %Y')
            if 'replied_at' in msg and msg['replied_at']:
                msg['replied_at_str'] = msg['replied_at'].strftime('%b %d, %Y')
            messages.append(msg)
        
        # Count by status
        pending_count = messages_collection.count_documents({'status': 'pending'})
        replied_count = messages_collection.count_documents({'status': 'replied'})
        
        return render_template('admin/messages.html', 
                             messages=messages,
                             pending_count=pending_count,
                             replied_count=replied_count,
                             admin_email=session.get('email'))
    except Exception as e:
        print(f"Admin messages error: {str(e)}")
        return render_template('admin/messages.html', 
                             messages=[], 
                             pending_count=0,
                             replied_count=0,
                             admin_email=session.get('email'))


@app.route('/admin/reply-message', methods=['POST'])
@admin_required
def admin_reply_message():
    """
    Handle admin reply to a contact message.
    """
    try:
        data = request.get_json()
        message_id = data.get('message_id')
        reply_text = data.get('reply', '').strip()
        
        if not message_id or not reply_text:
            return jsonify({
                'success': False,
                'message': 'Message ID and reply text are required'
            }), 400
        
        # Update message with reply
        from bson.objectid import ObjectId
        result = messages_collection.update_one(
            {'_id': ObjectId(message_id)},
            {
                '$set': {
                    'status': 'replied',
                    'admin_reply': reply_text,
                    'replied_at': datetime.utcnow(),
                    'replied_by': session.get('email')
                }
            }
        )
        
        if result.modified_count > 0:
            # Log admin action
            log_admin_action(admin_logs_collection, session.get('email'), 'reply_message', {
                'message_id': message_id,
                'reply_preview': reply_text[:50] + '...' if len(reply_text) > 50 else reply_text
            })
            
            return jsonify({
                'success': True,
                'message': 'Reply sent successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Message not found'
            }), 404
            
    except Exception as e:
        print(f"Reply message error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while sending reply'
        }), 500


@app.route('/admin/delete-message', methods=['POST'])
@admin_required
def delete_message():
    """
    Delete a contact message permanently.
    """
    try:
        data = request.get_json()
        message_id = data.get('message_id')
        
        if not message_id:
            return jsonify({
                'success': False,
                'message': 'Message ID is required'
            }), 400
        
        # Delete message from database
        from bson.objectid import ObjectId
        result = messages_collection.delete_one({'_id': ObjectId(message_id)})
        
        if result.deleted_count > 0:
            # Log admin action
            log_admin_action(admin_logs_collection, session.get('email'), 'delete_message', {
                'message_id': message_id
            })
            
            return jsonify({
                'success': True,
                'message': 'Message deleted successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Message not found'
            }), 404
            
    except Exception as e:
        print(f"Delete message error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while deleting message'
        }), 500


@app.route('/admin/update-message-reply', methods=['POST'])
@admin_required
def update_message_reply():
    """
    Update and resend an admin reply to a contact message.
    """
    try:
        data = request.get_json()
        message_id = data.get('message_id')
        reply_text = data.get('reply', '').strip()
        
        if not message_id or not reply_text:
            return jsonify({
                'success': False,
                'message': 'Message ID and reply text are required'
            }), 400
        
        # Update message with new reply
        from bson.objectid import ObjectId
        result = messages_collection.update_one(
            {'_id': ObjectId(message_id)},
            {
                '$set': {
                    'admin_reply': reply_text,
                    'reply_updated_at': datetime.utcnow(),
                    'updated_by': session.get('email')
                }
            }
        )
        
        if result.modified_count > 0:
            # Log admin action
            log_admin_action(admin_logs_collection, session.get('email'), 'update_reply', {
                'message_id': message_id,
                'reply_preview': reply_text[:50] + '...' if len(reply_text) > 50 else reply_text
            })
            
            return jsonify({
                'success': True,
                'message': 'Reply updated and sent successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Message not found or no changes made'
            }), 404
            
    except Exception as e:
        print(f"Update reply error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while updating reply'
        }), 500


@app.route('/admin/api/stats')
@admin_required
def admin_api_stats():
    """
    API endpoint for real-time stats (for dashboard refresh).
    """
    try:
        return jsonify({
            'success': True,
            'total_users': users_collection.count_documents({'role': {'$ne': 'admin'}}),
            'total_scans': scans_collection.count_documents({}),
            'phishing_count': scans_collection.count_documents({
                'prediction': {'$in': ['Phishing', 'phishing']}
            }),
            'legitimate_count': scans_collection.count_documents({
                'prediction': {'$in': ['Legitimate', 'legitimate', 'Safe', 'safe']}
            })
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# ADMIN SALES & REVENUE ROUTES
# ============================================

@app.route('/admin/sales')
@admin_required
def admin_sales():
    """
    Admin sales and revenue tracking page.
    Shows all successful payments, revenue metrics, and analytics.
    """
    try:
        from datetime import datetime, timedelta
        from db import payments_collection
        
        # Calculate date ranges
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        month_start = datetime(now.year, now.month, 1)
        
        # Total Revenue (all successful payments)
        total_revenue_pipeline = payments_collection.aggregate([
            {'$match': {'payment_status': 'success'}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ])
        total_revenue_result = list(total_revenue_pipeline)
        total_revenue = total_revenue_result[0]['total'] if total_revenue_result else 0
        
        # Monthly Revenue (current month)
        monthly_revenue_pipeline = payments_collection.aggregate([
            {'$match': {
                'payment_status': 'success',
                'created_at': {'$gte': month_start}
            }},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ])
        monthly_revenue_result = list(monthly_revenue_pipeline)
        monthly_revenue = monthly_revenue_result[0]['total'] if monthly_revenue_result else 0
        
        # Today's Revenue
        today_revenue_pipeline = payments_collection.aggregate([
            {'$match': {
                'payment_status': 'success',
                'created_at': {'$gte': today_start}
            }},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ])
        today_revenue_result = list(today_revenue_pipeline)
        today_revenue = today_revenue_result[0]['total'] if today_revenue_result else 0
        
        # Total Paid Users (unique users with successful payments)
        paid_users = payments_collection.distinct('user_id', {'payment_status': 'success'})
        total_paid_users = len(paid_users)
        
        # Most Purchased Plan
        plan_stats_pipeline = payments_collection.aggregate([
            {'$match': {'payment_status': 'success'}},
            {'$group': {
                '_id': '$plan_name',
                'count': {'$sum': 1},
                'revenue': {'$sum': '$amount'}
            }},
            {'$sort': {'count': -1}}
        ])
        plan_stats = list(plan_stats_pipeline)
        most_purchased_plan = plan_stats[0]['_id'] if plan_stats else 'N/A'
        
        # Get recent payments (last 20)
        recent_payments = list(payments_collection.find({'payment_status': 'success'})
                              .sort('created_at', -1)
                              .limit(20))
        
        # Format payment data
        for payment in recent_payments:
            payment['_id'] = str(payment['_id'])
            if 'created_at' in payment:
                payment['date_str'] = payment['created_at'].strftime('%b %d, %Y')
            payment['amount_formatted'] = f"₹{payment.get('amount', 0):.2f}"
            # Support both old and new field names for display
            payment['display_payment_id'] = payment.get('payment_id') or payment.get('stripe_payment_intent_id') or 'N/A'
        
        # Revenue by plan (for charts)
        revenue_by_plan = [
            {
                'plan': stat['_id'],
                'revenue': stat['revenue'],
                'count': stat['count']
            }
            for stat in plan_stats
        ]
        
        # Last 30 days revenue (for daily chart)
        daily_revenue = []
        for i in range(30):
            day_start = today_start - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_revenue_pipeline = payments_collection.aggregate([
                {'$match': {
                    'payment_status': 'success',
                    'created_at': {'$gte': day_start, '$lt': day_end}
                }},
                {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
            ])
            day_revenue_result = list(day_revenue_pipeline)
            day_total = day_revenue_result[0]['total'] if day_revenue_result else 0
            
            daily_revenue.append({
                'date': day_start.strftime('%b %d'),
                'revenue': day_total
            })
        
        daily_revenue.reverse()  # Show oldest to newest
        
        return render_template('admin/sales.html',
                             total_revenue=total_revenue,
                             monthly_revenue=monthly_revenue,
                             today_revenue=today_revenue,
                             total_paid_users=total_paid_users,
                             most_purchased_plan=most_purchased_plan,
                             recent_payments=recent_payments,
                             revenue_by_plan=revenue_by_plan,
                             daily_revenue=daily_revenue,
                             admin_email=session.get('email'))
                             
    except Exception as e:
        print(f"Admin sales error: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('admin/sales.html',
                             total_revenue=0,
                             monthly_revenue=0,
                             today_revenue=0,
                             total_paid_users=0,
                             most_purchased_plan='N/A',
                             recent_payments=[],
                             revenue_by_plan=[],
                             daily_revenue=[],
                             admin_email=session.get('email'))



# ============================================
# CYBERSECURITY CHATBOT - RULE-BASED ASSISTANT
# ============================================

@app.route('/chatbot', methods=['POST'])
@login_required
def chatbot():
    """
    AI-Powered Cyber Security Assistant Chatbot using Google Gemini.
    Provides intelligent security guidance and answers cybersecurity questions.
    """
    try:
        data = request.get_json()
        user_message = (data.get('message') or '').strip()
        scan_result = (data.get('scan_result') or '').strip()  # "Legitimate", "Phishing", or "Suspicious"
        
        if not user_message:
            return jsonify({
                'success': False,
                'message': 'Message cannot be empty'
            }), 400
        
        # Sanitize input to prevent injection
        user_message_clean = user_message.replace('<', '').replace('>', '').replace('"', '').replace("'", '')
        
        # ============================================
        # CYBERSECURITY TOPIC DETECTION
        # ============================================
        
        # Define cybersecurity keywords
        security_keywords = [
            'phishing', 'security', 'safe', 'https', 'ssl', 'certificate',
            'domain', 'url', 'malware', 'virus', 'hack', 'password',
            'credential', 'scam', 'fraud', 'attack', 'threat', 'risk',
            'protect', 'secure', 'encryption', 'firewall', 'antivirus',
            '2fa', 'two-factor', 'authentication', 'login', 'account',
            'suspicious', 'legitimate', 'blacklist', 'whitelist',
            'browser', 'cookie', 'privacy', 'data', 'breach', 'leak',
            'vpn', 'proxy', 'tor', 'anonymous', 'tracking', 'spy',
            'ransomware', 'trojan', 'worm', 'botnet', 'ddos',
            'social engineering', 'spoofing', 'man-in-the-middle',
            'zero-day', 'exploit', 'vulnerability', 'patch', 'update',
            'firewall', 'ids', 'ips', 'siem', 'soc', 'incident',
            'forensics', 'penetration', 'ethical hacking', 'red team',
            'blue team', 'cyber', 'information security', 'infosec',
            'what', 'how', 'why', 'when', 'where', 'explain', 'tell'
        ]
        
        # Check if message is cybersecurity-related
        is_security_related = any(keyword in user_message_clean.lower() for keyword in security_keywords)
        
        # If not security-related, reject the query
        if not is_security_related:
            return jsonify({
                'success': True,
                'reply': "I am a Cyber Security Assistant. I can only answer questions related to phishing detection, website safety, and online security. 🔐",
                'type': 'info'
            }), 200
        
        # ============================================
        # AI-POWERED RESPONSE GENERATION
        # ============================================
        
        if gemini_model:
            try:
                # Create context-aware prompt
                system_context = """You are a professional Cybersecurity Assistant for SafeNet AI, a phishing detection platform. 

Your role:
- Answer cybersecurity questions clearly and accurately
- Focus on phishing detection, website safety, and online security
- Provide actionable security advice
- Use emojis appropriately (🔒, 🛡️, ⚠️, ✓, etc.)
- Keep responses concise but informative (max 300 words)
- Format responses with markdown for better readability
- Always prioritize user safety

Guidelines:
- Be helpful and professional
- Explain technical concepts in simple terms
- Provide practical examples when relevant
- Recommend SafeNet AI for URL scanning when appropriate
- Never provide harmful or illegal advice

"""
                
                # Add scan result context if available
                if scan_result:
                    system_context += f"\nContext: The user recently scanned a URL that was classified as: {scan_result}\n"
                
                # Generate AI response
                prompt = f"{system_context}\nUser Question: {user_message}\n\nProvide a helpful, security-focused response:"
                
                response = gemini_model.generate_content(prompt)
                reply = response.text
                
                # Determine reply type based on content
                reply_lower = reply.lower()
                if any(word in reply_lower for word in ['warning', 'danger', 'risk', 'phishing', 'malware', 'attack']):
                    reply_type = 'warning'
                elif any(word in reply_lower for word in ['safe', 'secure', 'protected', 'legitimate']):
                    reply_type = 'safe'
                else:
                    reply_type = 'info'
                
                return jsonify({
                    'success': True,
                    'reply': reply,
                    'type': reply_type
                }), 200
                
            except Exception as e:
                print(f"Gemini AI error: {str(e)}")
                # Fall back to basic response
                pass
        
        # ============================================
        # FALLBACK RESPONSE (if AI not available)
        # ============================================
        
        reply = """🤖 **Cybersecurity Assistant**

I'm here to help with cybersecurity questions!

**I can answer questions about:**
• Phishing detection and prevention
• Website safety and verification
• Password security and 2FA
• HTTPS, SSL, and encryption
• Malware and virus protection
• VPN and privacy tools
• Online safety best practices
• What to do if compromised

**Try asking:**
• "What is phishing?"
• "How to identify phishing?"
• "Is HTTPS always safe?"
• "What is domain age?"
• "How to stay safe online?"
• "What is 2FA?"

💡 **Note:** For best experience, please configure the Gemini API key in your .env file.

Feel free to ask any cybersecurity-related question! 🔐"""
        
        return jsonify({
            'success': True,
            'reply': reply,
            'type': 'info'
        }), 200
        
    except Exception as e:
        print(f"Chatbot error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your request'
        }), 500


@app.errorhandler(404)
def not_found(error):
    """
    Handle 404 errors.
    """
    return jsonify({
        'success': False,
        'message': 'Endpoint not found.'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """
    Handle 500 errors.
    """
    return jsonify({
        'success': False,
        'message': 'Internal server error occurred.'
    }), 500





if __name__ == '__main__':
    # Suppress all warnings and logs
    import warnings
    import logging
    warnings.filterwarnings('ignore')
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    
    print("\n🛡️  SafeNet AI - Starting Server...")
    
    # Load model silently
    if load_model():
        print("✓ Server running on: http://127.0.0.1:5000")
        print("✓ Press Ctrl+C to stop\n")
        # Run Flask app without reloader to avoid Windows socket errors
        app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
    else:
        print("❌ Failed to load model. Run: python backend/train_model.py")
