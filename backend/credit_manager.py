"""
Credit Management Utilities
============================
Handles credit deduction, renewal, and validation.
"""

from datetime import datetime
from pricing_config import (
    get_plan_credits,
    should_renew_credits,
    calculate_next_renewal_date,
    has_feature_access
)


def check_and_renew_credits(users_collection, user_id):
    """
    Check if user credits need renewal and renew if necessary.
    SINGLE SOURCE OF TRUTH: Updates total_credits, credits_used, credits_remaining.
    
    Args:
        users_collection: MongoDB users collection
        user_id (str): User ID
        
    Returns:
        bool: True if credits were renewed
    """
    try:
        user = users_collection.find_one({'user_id': user_id})
        if not user:
            return False
        
        # Skip renewal for unlimited credits (enterprise plan)
        total_credits = user.get('total_credits', 0)
        if total_credits == -1:
            return False
        
        last_renewal = user.get('last_credit_renewal')
        
        if should_renew_credits(last_renewal):
            # Renew credits based on current plan
            plan = user.get('plan', 'free')
            new_credits = get_plan_credits(plan)
            
            users_collection.update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        'total_credits': new_credits,
                        'credits_used': 0,
                        'credits_remaining': new_credits,
                        'last_credit_renewal': datetime.utcnow(),
                        'next_credit_renewal': calculate_next_renewal_date()
                    }
                }
            )
            
            print(f"✓ Credits renewed for user {user.get('email')}: {new_credits} credits")
            return True
        
        return False
        
    except Exception as e:
        print(f"Error renewing credits: {str(e)}")
        return False


def has_credits(users_collection, user_id):
    """
    Check if user has available credits.
    SINGLE SOURCE OF TRUTH: Uses credits_remaining field.
    
    Args:
        users_collection: MongoDB users collection
        user_id (str): User ID
        
    Returns:
        tuple: (has_credits: bool, current_credits: int)
    """
    try:
        user = users_collection.find_one({'user_id': user_id})
        if not user:
            return False, 0
        
        # Use credits_remaining as the single source of truth
        credits_remaining = user.get('credits_remaining', 0)
        
        # Unlimited credits (enterprise)
        if credits_remaining == -1:
            return True, -1
        
        return credits_remaining > 0, credits_remaining
        
    except Exception as e:
        print(f"Error checking credits: {str(e)}")
        return False, 0


def deduct_credit(users_collection, user_id, amount=1):
    """
    Deduct credits from user account.
    SINGLE SOURCE OF TRUTH: Updates credits_used and credits_remaining.
    
    Args:
        users_collection: MongoDB users collection
        user_id (str): User ID
        amount (int): Number of credits to deduct (default: 1)
        
    Returns:
        tuple: (success: bool, remaining_credits: int)
    """
    try:
        user = users_collection.find_one({'user_id': user_id})
        if not user:
            return False, 0
        
        total_credits = user.get('total_credits', 0)
        credits_used = user.get('credits_used', 0)
        credits_remaining = user.get('credits_remaining', 0)
        
        # Unlimited credits - don't deduct
        if total_credits == -1 or credits_remaining == -1:
            return True, -1
        
        # Check if user has enough credits
        if credits_remaining < amount:
            return False, credits_remaining
        
        # Deduct credits
        new_credits_used = credits_used + amount
        new_credits_remaining = total_credits - new_credits_used
        
        # Ensure non-negative
        new_credits_remaining = max(0, new_credits_remaining)
        
        users_collection.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'credits_used': new_credits_used,
                    'credits_remaining': new_credits_remaining
                }
            }
        )
        
        print(f"✓ Credit deducted. Used: {new_credits_used}/{total_credits}, Remaining: {new_credits_remaining}")
        return True, new_credits_remaining
        
    except Exception as e:
        print(f"Error deducting credit: {str(e)}")
        return False, 0


def get_user_credits(users_collection, user_id):
    """
    Get current credit balance for user.
    SINGLE SOURCE OF TRUTH: Returns credits_remaining.
    
    Args:
        users_collection: MongoDB users collection
        user_id (str): User ID
        
    Returns:
        int: Current credits_remaining (-1 for unlimited, 0 if user not found)
    """
    try:
        user = users_collection.find_one({'user_id': user_id})
        if not user:
            return 0
        
        return user.get('credits_remaining', 0)
        
    except Exception as e:
        print(f"Error getting user credits: {str(e)}")
        return 0


def update_user_plan(users_collection, user_id, new_plan):
    """
    Update user's pricing plan and reset credits.
    SINGLE SOURCE OF TRUTH: Updates total_credits, credits_used, credits_remaining.
    
    Args:
        users_collection: MongoDB users collection
        user_id (str): User ID
        new_plan (str): New plan name (free, basic, pro, pro_plus, enterprise)
        
    Returns:
        bool: True if plan updated successfully
    """
    try:
        # Get credits for new plan
        new_credits = get_plan_credits(new_plan)
        
        users_collection.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'plan': new_plan,
                    'total_credits': new_credits,
                    'credits_used': 0,
                    'credits_remaining': new_credits,
                    'last_credit_renewal': datetime.utcnow(),
                    'next_credit_renewal': calculate_next_renewal_date() if new_credits != -1 else None
                }
            }
        )
        
        print(f"✓ Plan updated to {new_plan} with {new_credits} credits")
        return True
        
    except Exception as e:
        print(f"Error updating user plan: {str(e)}")
        return False


def check_feature_access(users_collection, user_id, feature_name):
    """
    Check if user has access to a specific feature based on their plan.
    
    Args:
        users_collection: MongoDB users collection
        user_id (str): User ID
        feature_name (str): Feature name to check
        
    Returns:
        tuple: (has_access: bool, user_plan: str)
    """
    try:
        user = users_collection.find_one({'user_id': user_id})
        if not user:
            return False, 'free'
        
        plan = user.get('plan', 'free')
        has_access = has_feature_access(plan, feature_name)
        
        return has_access, plan
        
    except Exception as e:
        print(f"Error checking feature access: {str(e)}")
        return False, 'free'
