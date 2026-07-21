"""
Pricing Configuration for SafeNet AI
=====================================
Defines all pricing plans, features, and credit limits.
"""

from datetime import datetime, timedelta

# Pricing Plans Configuration
PRICING_PLANS = {
    'free': {
        'name': 'Free',
        'display_name': 'Free',
        'price': 0,
        'currency': '₹',
        'credits_per_month': 10,
        'features': {
            'url_scanning': True,
            'ml_detection': True,
            'whois_intelligence': False,
            'blacklist_checking': False,
            'content_analysis': False,
            'bulk_scanning': False,
            'priority_processing': False,
            'advanced_results': False,
            'api_access': False
        },
        'feature_list': [
            'Single URL scan',
            'Basic ML detection only',
            'No WHOIS intelligence',
            'No Blacklist checking',
            'No Bulk scanning'
        ],
        'limitations': [
            'Limited to 10 scans per month',
            'Basic detection only',
            'No advanced features'
        ]
    },
    'basic': {
        'name': 'Basic',
        'display_name': 'Basic',
        'price': 499,
        'currency': '₹',
        'credits_per_month': 1000,
        'features': {
            'url_scanning': True,
            'ml_detection': True,
            'whois_intelligence': False,
            'blacklist_checking': False,
            'content_analysis': False,
            'bulk_scanning': False,
            'priority_processing': False,
            'advanced_results': False,
            'api_access': False
        },
        'feature_list': [
            'URL scanning',
            'ML detection',
            'Basic result view',
            '1,000 scans per month'
        ],
        'limitations': [
            'No WHOIS intelligence',
            'No Blacklist checking',
            'No Bulk scanning'
        ]
    },
    'pro': {
        'name': 'Pro',
        'display_name': 'Pro',
        'price': 999,
        'currency': '₹',
        'credits_per_month': 2500,
        'features': {
            'url_scanning': True,
            'ml_detection': True,
            'whois_intelligence': True,
            'blacklist_checking': True,
            'content_analysis': True,
            'bulk_scanning': False,
            'priority_processing': False,
            'advanced_results': True,
            'api_access': False
        },
        'feature_list': [
            'WHOIS Intelligence',
            'Blacklist checking',
            'Content analysis',
            'Advanced results',
            '2,500 scans per month'
        ],
        'limitations': [
            'No Bulk scanning',
            'No Priority processing'
        ]
    },
    'pro_plus': {
        'name': 'Pro Plus',
        'display_name': 'Pro Plus',
        'price': 1999,
        'currency': '₹',
        'credits_per_month': 6000,
        'features': {
            'url_scanning': True,
            'ml_detection': True,
            'whois_intelligence': True,
            'blacklist_checking': True,
            'content_analysis': True,
            'bulk_scanning': True,
            'priority_processing': True,
            'advanced_results': True,
            'api_access': False
        },
        'feature_list': [
            'Multi-layer detection',
            'Bulk URL scanning',
            'Priority processing',
            'All Pro features',
            '6,000 scans per month'
        ],
        'limitations': []
    },
    'enterprise': {
        'name': 'Enterprise',
        'display_name': 'Custom (Enterprise)',
        'price': None,  # Contact sales
        'currency': '₹',
        'credits_per_month': -1,  # Unlimited
        'features': {
            'url_scanning': True,
            'ml_detection': True,
            'whois_intelligence': True,
            'blacklist_checking': True,
            'content_analysis': True,
            'bulk_scanning': True,
            'priority_processing': True,
            'advanced_results': True,
            'api_access': True
        },
        'feature_list': [
            'Everything unlocked',
            'Unlimited scans',
            'API access',
            'Dedicated support',
            'Custom integrations',
            'Admin-level access'
        ],
        'limitations': []
    }
}

# Default plan for new users
DEFAULT_PLAN = 'free'

# Credit renewal period (days)
CREDIT_RENEWAL_PERIOD = 30


def get_plan_config(plan_name):
    """
    Get configuration for a specific plan.
    
    Args:
        plan_name (str): Plan name (free, basic, pro, pro_plus, enterprise)
        
    Returns:
        dict: Plan configuration or None if not found
    """
    return PRICING_PLANS.get(plan_name.lower())


def has_feature_access(plan_name, feature_name):
    """
    Check if a plan has access to a specific feature.
    
    Args:
        plan_name (str): Plan name
        feature_name (str): Feature name
        
    Returns:
        bool: True if plan has access to feature
    """
    plan = get_plan_config(plan_name)
    if not plan:
        return False
    
    return plan['features'].get(feature_name, False)


def get_plan_credits(plan_name):
    """
    Get monthly credits for a plan.
    
    Args:
        plan_name (str): Plan name
        
    Returns:
        int: Credits per month (-1 for unlimited)
    """
    plan = get_plan_config(plan_name)
    if not plan:
        return 0
    
    return plan['credits_per_month']


def calculate_next_renewal_date():
    """
    Calculate next credit renewal date (30 days from now).
    
    Returns:
        datetime: Next renewal date
    """
    return datetime.utcnow() + timedelta(days=CREDIT_RENEWAL_PERIOD)


def should_renew_credits(last_renewal_date):
    """
    Check if credits should be renewed based on last renewal date.
    
    Args:
        last_renewal_date (datetime): Last credit renewal date
        
    Returns:
        bool: True if credits should be renewed
    """
    if not last_renewal_date:
        return True
    
    days_since_renewal = (datetime.utcnow() - last_renewal_date).days
    return days_since_renewal >= CREDIT_RENEWAL_PERIOD
