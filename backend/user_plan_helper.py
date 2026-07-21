"""
User Plan State Helper
======================
Centralized function to get user plan state from database.
This is the SINGLE SOURCE OF TRUTH for all pages.
"""

from datetime import datetime
from math import ceil


def get_user_plan_state(users_collection, user_id):
    """
    Get complete user plan state from database.
    This is the SINGLE SOURCE OF TRUTH for:
    - Home page
    - Navbar
    - Pricing page
    - Dashboard
    - Admin panel
    
    Args:
        users_collection: MongoDB users collection
        user_id (str): User ID
        
    Returns:
        dict: Complete user plan state
        {
            'plan_name': str,
            'total_credits': int,
            'credits_used': int,
            'credits_remaining': int,
            'days_remaining': int,
            'plan_activated_at': datetime,
            'reset_at': datetime
        }
        Returns None if user not found
    """
    try:
        user = users_collection.find_one({'user_id': user_id})
        
        if not user:
            return None
        
        # Get plan data from database
        plan_name = user.get('plan', 'free')
        total_credits = user.get('total_credits', 10)
        credits_used = user.get('credits_used', 0)
        
        # Calculate credits_remaining
        if total_credits == -1:  # Unlimited (enterprise)
            credits_remaining = -1
        else:
            credits_remaining = total_credits - credits_used
            # Ensure non-negative
            credits_remaining = max(0, credits_remaining)
        
        # Calculate days_remaining
        reset_at = user.get('reset_at') or user.get('next_credit_renewal')
        days_remaining = 0
        
        if reset_at:
            now = datetime.utcnow()
            time_diff = reset_at - now
            # Use ceil to round up (e.g., 0.1 days = 1 day)
            days_remaining = max(0, ceil(time_diff.total_seconds() / 86400))
        
        # Build complete state
        plan_state = {
            'plan_name': plan_name,
            'total_credits': total_credits,
            'credits_used': credits_used,
            'credits_remaining': credits_remaining,
            'days_remaining': days_remaining,
            'plan_activated_at': user.get('plan_activated_at'),
            'reset_at': reset_at
        }
        
        return plan_state
        
    except Exception as e:
        return None


def update_credits_remaining(users_collection, user_id):
    """
    Update credits_remaining field in database based on total_credits and credits_used.
    Call this after any credit deduction or plan change.
    
    Args:
        users_collection: MongoDB users collection
        user_id (str): User ID
        
    Returns:
        bool: True if updated successfully
    """
    try:
        user = users_collection.find_one({'user_id': user_id})
        
        if not user:
            return False
        
        total = user.get('total_credits', 0)
        used = user.get('credits_used', 0)
        
        if total == -1:  # Unlimited
            remaining = -1
        else:
            remaining = max(0, total - used)
        
        users_collection.update_one(
            {'user_id': user_id},
            {'$set': {'credits_remaining': remaining}}
        )
        
        return True
        
    except Exception as e:
        return False
