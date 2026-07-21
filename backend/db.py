"""
MongoDB Database Connection Module
====================================

This module handles MongoDB connection and provides database collections
for user authentication, scan history, and admin dashboard.
"""

import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection variables
mongodb_available = False
db = None
users_collection = None
scans_collection = None
logs_collection = None
blacklist_collection = None
system_config_collection = None
admin_logs_collection = None
messages_collection = None  # Contact form messages
credit_logs_collection = None  # Credit usage tracking
payments_collection = None  # Stripe payment transactions for sales tracking

try:
    # Get MongoDB URI from environment variable
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    
    if not MONGO_URI or MONGO_URI == 'mongodb://localhost:27017/':
        raise Exception("MONGO_URI not found in .env file")
    
    # Create MongoDB client with timeout and SSL configuration using certifi
    import certifi
    client = MongoClient(
        MONGO_URI, 
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        tlsCAFile=certifi.where(),
        retryWrites=True
    )
    
    # Get database
    db = client['phishing_detection']
    
    # Get collections - Core
    users_collection = db['users']
    scans_collection = db['scans']
    logs_collection = db['logs']
    
    # Get collections - Admin Dashboard
    blacklist_collection = db['blacklist']
    system_config_collection = db['system_config']
    admin_logs_collection = db['admin_logs']
    messages_collection = db['messages']  # Contact form messages
    credit_logs_collection = db['credit_logs']  # Credit usage tracking
    payments_collection = db['payments']  # Stripe payment transactions
    
    # Try to verify connection by attempting a simple operation
    try:
        # This will trigger actual connection
        _ = users_collection.find_one()
        connection_verified = True
    except Exception as verify_error:
        pass  # Connection verification warning
        connection_verified = False
    
    # Create indexes for better performance (with error handling)
    if connection_verified:
        try:
            users_collection.create_index('email', unique=True)
            scans_collection.create_index('user_id')
            scans_collection.create_index('timestamp')
            blacklist_collection.create_index('domain', unique=True)
            admin_logs_collection.create_index('timestamp')
            messages_collection.create_index('user_id')
            messages_collection.create_index('timestamp')
            credit_logs_collection.create_index('user_id')
            credit_logs_collection.create_index('timestamp')
            credit_logs_collection.create_index('date')
            payments_collection.create_index('user_id')
            payments_collection.create_index('created_at')
            payments_collection.create_index('status')
        except Exception as index_error:
            pass  # Index creation warning
    
    mongodb_available = connection_verified
    
    if mongodb_available:
        pass  # MongoDB connected
    else:
        pass  # MongoDB connection not verified
    
except (ConnectionFailure, ServerSelectionTimeoutError) as e:
    pass  # MongoDB connection failed
    mongodb_available = False
    
except Exception as e:
    pass  # Unexpected MongoDB error
    mongodb_available = False
