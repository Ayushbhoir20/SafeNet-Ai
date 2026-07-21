"""
Stripe Payment Configuration for SafeNet AI
============================================
Handles Stripe API keys and price ID mappings.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Stripe API Keys
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# Stripe Price IDs for each plan (Monthly Recurring Subscriptions)
# These should be created in your Stripe Dashboard
# Format: price_xxxxxxxxxxxxx
STRIPE_PRICE_IDS = {
    'basic': os.getenv('STRIPE_PRICE_ID_BASIC', ''),
    'pro': os.getenv('STRIPE_PRICE_ID_PRO', ''),
    'pro_plus': os.getenv('STRIPE_PRICE_ID_PRO_PLUS', '')
}

# Plans that support Stripe payments
STRIPE_ENABLED_PLANS = ['basic', 'pro', 'pro_plus']

# Success and Cancel URLs
SUCCESS_URL = os.getenv('STRIPE_SUCCESS_URL', 'http://localhost:5000/payment/success?session_id={CHECKOUT_SESSION_ID}')
CANCEL_URL = os.getenv('STRIPE_CANCEL_URL', 'http://localhost:5000/pricing?canceled=true')


def get_stripe_price_id(plan_name):
    """
    Get Stripe Price ID for a given plan.
    
    Args:
        plan_name (str): Plan name (basic, pro, pro_plus)
        
    Returns:
        str: Stripe Price ID or None if not found
    """
    return STRIPE_PRICE_IDS.get(plan_name.lower())


def is_stripe_configured():
    """
    Check if Stripe is properly configured.
    
    Returns:
        bool: True if all required Stripe keys are set
    """
    return bool(STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY and STRIPE_WEBHOOK_SECRET)


def validate_plan_for_stripe(plan_name):
    """
    Validate if a plan supports Stripe payments.
    
    Args:
        plan_name (str): Plan name
        
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    plan_lower = plan_name.lower()
    
    if plan_lower not in STRIPE_ENABLED_PLANS:
        return False, f"Plan '{plan_name}' does not support Stripe payments"
    
    price_id = get_stripe_price_id(plan_lower)
    if not price_id:
        return False, f"Stripe Price ID not configured for plan '{plan_name}'"
    
    return True, None
