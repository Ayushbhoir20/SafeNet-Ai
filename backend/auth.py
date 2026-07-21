"""
Authentication Module
=====================

This module handles user registration, authentication, and password hashing.
Uses Werkzeug for secure password hashing.
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password):
    """
    Hash a password using Werkzeug's secure method.
    
    Args:
        password (str): Plain text password
        
    Returns:
        str: Hashed password
    """
    return generate_password_hash(password)


def verify_password(password, password_hash):
    """
    Verify a password against a hash.
    
    Args:
        password (str): Plain text password
        password_hash (str): Hashed password
        
    Returns:
        bool: True if password matches
    """
    # Support both new Werkzeug hash and legacy SHA-256
    if password_hash.startswith('pbkdf2:') or password_hash.startswith('scrypt:'):
        return check_password_hash(password_hash, password)
    else:
        # Legacy SHA-256 hash support
        return hashlib.sha256(password.encode()).hexdigest() == password_hash


def register_user(users_collection, email, password):
    """
    Register a new user in the database.
    
    Args:
        users_collection: MongoDB users collection
        email (str): User email
        password (str): User password
        
    Returns:
        tuple: (success: bool, message: str, user_id: str or None)
    """
    try:
        # Import pricing config
        from pricing_config import DEFAULT_PLAN, get_plan_credits, calculate_next_renewal_date
        
        # Check if user already exists
        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            return False, 'Email already registered', None
        
        # Create new user
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(password)
        
        # Get default plan credits
        default_credits = get_plan_credits(DEFAULT_PLAN)
        
        # Calculate reset date (30 days from now)
        now = datetime.utcnow()
        reset_date = now + timedelta(days=30)
        
        user_data = {
            'user_id': user_id,
            'email': email,
            'password': hashed_password,
            'role': 'user',
            'status': 'active',  # active / blocked
            'created_at': now,
            'last_login': None,
            'total_scans': 0,
            # Pricing & Credits (Enhanced)
            'plan': DEFAULT_PLAN,  # free, basic, pro, pro_plus, enterprise
            'total_credits': default_credits,  # Total credits for billing cycle
            'credits_used': 0,  # Credits used in current cycle
            'credits_remaining': default_credits,  # Remaining credits
            'plan_activated_at': now,  # When plan was activated
            'reset_at': reset_date if default_credits != -1 else None,  # When credits reset
            'last_credit_renewal': now,
            'next_credit_renewal': reset_date if default_credits != -1 else None,
            'low_credit_alert_sent': False,  # Email alert flag
            'updated_at': now
        }
        
        users_collection.insert_one(user_data)
        
        return True, 'Registration successful', user_id
        
    except Exception as e:
        error_msg = str(e)
        print(f"Registration error: {error_msg}")
        
        # Return more specific error message
        if 'duplicate key' in error_msg.lower() or 'dup key' in error_msg.lower():
            return False, 'Email already registered', None
        else:
            return False, f'Registration failed: {error_msg}', None


def authenticate_user(users_collection, email, password):
    """
    Authenticate a user with email and password.
    
    Args:
        users_collection: MongoDB users collection
        email (str): User email
        password (str): User password
        
    Returns:
        tuple: (success: bool, message: str, user_data: dict or None)
    """
    try:
        # Find user by email
        user = users_collection.find_one({'email': email})
        
        if not user:
            return False, 'Invalid email or password', None
        
        # Verify password
        password_valid = verify_password(password, user['password'])
        
        if not password_valid:
            return False, 'Invalid email or password', None
        
        # Check if user is blocked
        if user.get('status') == 'blocked':
            return False, 'Your account has been blocked. Contact administrator.', None
        
        # Update last login
        users_collection.update_one(
            {'email': email},
            {'$set': {'last_login': datetime.utcnow()}}
        )
        
        # Return user data (without password)
        user_data = {
            'id': user['user_id'],
            'email': user['email'],
            'role': user.get('role', 'user'),
            'status': user.get('status', 'active')
        }
        
        return True, 'Login successful', user_data
        
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        return False, 'Authentication failed', None


def create_admin_user(users_collection):
    """
    Create an admin user for system administration.
    Uses the specified admin credentials.
    
    Args:
        users_collection: MongoDB users collection
        
    Returns:
        bool: True if admin user created successfully
    """
    try:
        # Admin credentials as specified
        admin_email = 'ayushbhoir114@gmail.com'
        admin_password = 'Ayush@123'
        
        # Check if admin user already exists
        existing_user = users_collection.find_one({'email': admin_email})
        if existing_user:
            # Ensure the user has admin role and enterprise plan
            if existing_user.get('role') != 'admin' or existing_user.get('plan') != 'enterprise':
                users_collection.update_one(
                    {'email': admin_email},
                    {'$set': {
                        'role': 'admin',
                        'status': 'active',
                        'plan': 'enterprise',
                        'total_credits': -1,  # Unlimited
                        'credits_used': 0,
                        'credits_remaining': -1
                    }}
                )
                print(f"✓ User upgraded to admin with enterprise plan: {admin_email}")
            else:
                print("✓ Admin user already exists")
            return True
        
        # Create admin user with specified credentials
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(admin_password)
        
        now = datetime.utcnow()
        
        user_data = {
            'user_id': user_id,
            'email': admin_email,
            'password': hashed_password,
            'role': 'admin',  # Set role to admin
            'status': 'active',
            'created_at': now,
            'last_login': None,
            'total_scans': 0,
            # Admin gets enterprise plan with unlimited credits
            'plan': 'enterprise',
            'total_credits': -1,  # Unlimited credits
            'credits_used': 0,
            'credits_remaining': -1,
            'plan_activated_at': now,
            'reset_at': None,  # No reset for unlimited
            'last_credit_renewal': now,
            'next_credit_renewal': None,  # No renewal needed for unlimited
            'low_credit_alert_sent': False,
            'updated_at': now
        }
        
        users_collection.insert_one(user_data)
        print(f"✓ Admin user created: {admin_email}")
        print(f"  Role: admin (full system access)")
        print(f"  Plan: Enterprise (unlimited credits)")
        return True
            
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        return False


def log_admin_action(admin_logs_collection, admin_email, action, details=None):
    """
    Log an admin action for audit purposes.
    
    Args:
        admin_logs_collection: MongoDB admin_logs collection
        admin_email (str): Admin email
        action (str): Action type (login, user_block, blacklist_add, etc.)
        details (dict): Additional details
        
    Returns:
        bool: True if logged successfully
    """
    try:
        log_entry = {
            'admin_email': admin_email,
            'action': action,
            'details': details or {},
            'timestamp': datetime.utcnow(),
            'ip_address': None  # Can be set from request.remote_addr
        }
        
        admin_logs_collection.insert_one(log_entry)
        return True
        
    except Exception as e:
        print(f"Error logging admin action: {str(e)}")
        return False
