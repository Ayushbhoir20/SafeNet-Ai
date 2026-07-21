"""
Enhanced Credit Management System
==================================
Production-ready credit system with:
- Proper timestamp tracking
- Real-time updates
- Usage analytics
- Low credit alerts
- Admin controls
"""

from datetime import datetime, timedelta
from math import ceil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class CreditManager:
    """
    Centralized credit management with production-grade features.
    """
    
    def __init__(self, users_collection, credit_logs_collection):
        self.users_collection = users_collection
        self.credit_logs_collection = credit_logs_collection
    
    def initialize_user_credits(self, user_id, plan, credits):
        """
        Initialize credits for a new user or plan change.
        
        Args:
            user_id: User ID
            plan: Plan name (free, basic, pro, pro_plus, enterprise)
            credits: Total credits for the plan
            
        Returns:
            bool: Success status
        """
        try:
            now = datetime.utcnow()
            reset_date = now + timedelta(days=30)
            
            update_data = {
                'plan': plan,
                'total_credits': credits if credits != -1 else -1,
                'credits_remaining': credits if credits != -1 else -1,
                'credits_used': 0,
                'plan_activated_at': now,
                'reset_at': reset_date if credits != -1 else None,
                'last_credit_renewal': now,
                'next_credit_renewal': reset_date if credits != -1 else None,
                'low_credit_alert_sent': False,
                'updated_at': now
            }
            
            self.users_collection.update_one(
                {'user_id': user_id},
                {'$set': update_data}
            )
            
            print(f"✓ Credits initialized for user {user_id}: {credits} credits")
            return True
            
        except Exception as e:
            print(f"Error initializing credits: {str(e)}")
            return False
    
    def get_user_credit_info(self, user_id):
        """
        Get comprehensive credit information for a user.
        
        Returns:
            dict: Credit information including usage, remaining, reset date
        """
        try:
            user = self.users_collection.find_one({'user_id': user_id})
            if not user:
                return None
            
            # Handle unlimited credits (enterprise)
            if user.get('total_credits', 0) == -1:
                return {
                    'total_credits': -1,
                    'credits_remaining': -1,
                    'credits_used': 0,
                    'plan': user.get('plan', 'free'),
                    'reset_at': None,
                    'days_until_reset': None,
                    'usage_percentage': 0
                }
            
            total_credits = user.get('total_credits', 0)
            credits_used = user.get('credits_used', 0)
            credits_remaining = total_credits - credits_used
            reset_at = user.get('reset_at')
            
            # Calculate days until reset
            days_until_reset = None
            if reset_at:
                diff = reset_at - datetime.utcnow()
                days_until_reset = ceil(diff.total_seconds() / 86400)
                if days_until_reset < 0:
                    days_until_reset = 0
            
            # Calculate usage percentage
            usage_percentage = 0
            if total_credits > 0:
                usage_percentage = (credits_used / total_credits) * 100
            
            return {
                'total_credits': total_credits,
                'credits_remaining': credits_remaining,
                'credits_used': credits_used,
                'plan': user.get('plan', 'free'),
                'plan_activated_at': user.get('plan_activated_at'),
                'reset_at': reset_at,
                'days_until_reset': days_until_reset,
                'usage_percentage': usage_percentage,
                'low_credit_alert_sent': user.get('low_credit_alert_sent', False)
            }
            
        except Exception as e:
            print(f"Error getting credit info: {str(e)}")
            return None
    
    def deduct_credits(self, user_id, amount=1, scan_url=None):
        """
        Deduct credits and log the usage.
        
        Args:
            user_id: User ID
            amount: Credits to deduct (default: 1)
            scan_url: URL being scanned (for logging)
            
        Returns:
            tuple: (success, updated_credit_info)
        """
        try:
            user = self.users_collection.find_one({'user_id': user_id})
            if not user:
                return False, None
            
            # Handle unlimited credits
            if user.get('total_credits', 0) == -1:
                # Log usage even for unlimited
                self._log_credit_usage(user_id, 0, scan_url)
                return True, self.get_user_credit_info(user_id)
            
            total_credits = user.get('total_credits', 0)
            credits_used = user.get('credits_used', 0)
            credits_remaining = total_credits - credits_used
            
            # Check if enough credits
            if credits_remaining < amount:
                return False, self.get_user_credit_info(user_id)
            
            # Deduct credits
            new_credits_used = credits_used + amount
            new_credits_remaining = total_credits - new_credits_used
            
            self.users_collection.update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        'credits_used': new_credits_used,
                        'credits_remaining': new_credits_remaining,
                        'updated_at': datetime.utcnow()
                    },
                    '$inc': {'total_scans': 1}
                }
            )
            
            # Log credit usage
            self._log_credit_usage(user_id, amount, scan_url)
            
            # Check for low credit alert
            usage_percentage = (new_credits_used / total_credits) * 100
            if usage_percentage >= 90 and not user.get('low_credit_alert_sent', False):
                self._send_low_credit_alert(user_id, new_credits_remaining, total_credits)
            
            return True, self.get_user_credit_info(user_id)
            
        except Exception as e:
            print(f"Error deducting credits: {str(e)}")
            return False, None
    
    def _log_credit_usage(self, user_id, credits_used, scan_url=None):
        """
        Log credit usage for analytics.
        """
        try:
            log_entry = {
                'user_id': user_id,
                'credits_used': credits_used,
                'scan_url': scan_url,
                'timestamp': datetime.utcnow(),
                'date': datetime.utcnow().date().isoformat()
            }
            
            self.credit_logs_collection.insert_one(log_entry)
            
        except Exception as e:
            print(f"Error logging credit usage: {str(e)}")
    
    def _send_low_credit_alert(self, user_id, remaining_credits, total_credits):
        """
        Send email alert when credits are low.
        """
        try:
            user = self.users_collection.find_one({'user_id': user_id})
            if not user:
                return
            
            email = user.get('email')
            reset_at = user.get('reset_at')
            
            # Mark alert as sent
            self.users_collection.update_one(
                {'user_id': user_id},
                {'$set': {'low_credit_alert_sent': True}}
            )
            
            # TODO: Implement actual email sending
            print(f"✓ Low credit alert triggered for {email}")
            print(f"  Remaining: {remaining_credits}/{total_credits}")
            print(f"  Reset date: {reset_at}")
            
        except Exception as e:
            print(f"Error sending low credit alert: {str(e)}")
    
    def get_usage_analytics(self, user_id, range_type='daily'):
        """
        Get credit usage analytics.
        
        Args:
            user_id: User ID
            range_type: 'daily', 'weekly', or 'monthly'
            
        Returns:
            list: Usage data points
        """
        try:
            now = datetime.utcnow()
            
            if range_type == 'daily':
                # Last 30 days
                start_date = now - timedelta(days=30)
            elif range_type == 'weekly':
                # Last 12 weeks
                start_date = now - timedelta(weeks=12)
            else:  # monthly
                # Last 12 months
                start_date = now - timedelta(days=365)
            
            # Aggregate usage by date
            pipeline = [
                {
                    '$match': {
                        'user_id': user_id,
                        'timestamp': {'$gte': start_date}
                    }
                },
                {
                    '$group': {
                        '_id': '$date',
                        'credits_used': {'$sum': '$credits_used'},
                        'scan_count': {'$sum': 1}
                    }
                },
                {
                    '$sort': {'_id': 1}
                }
            ]
            
            results = list(self.credit_logs_collection.aggregate(pipeline))
            
            return [{
                'date': r['_id'],
                'credits_used': r['credits_used'],
                'scan_count': r['scan_count']
            } for r in results]
            
        except Exception as e:
            print(f"Error getting usage analytics: {str(e)}")
            return []
    
    def reset_credits(self, user_id):
        """
        Reset credits for monthly renewal.
        
        Returns:
            bool: Success status
        """
        try:
            user = self.users_collection.find_one({'user_id': user_id})
            if not user:
                return False
            
            # Skip for unlimited credits
            if user.get('total_credits', 0) == -1:
                return True
            
            total_credits = user.get('total_credits', 0)
            now = datetime.utcnow()
            next_reset = now + timedelta(days=30)
            
            self.users_collection.update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        'credits_used': 0,
                        'credits_remaining': total_credits,
                        'reset_at': next_reset,
                        'last_credit_renewal': now,
                        'next_credit_renewal': next_reset,
                        'low_credit_alert_sent': False,
                        'updated_at': now
                    }
                }
            )
            
            print(f"✓ Credits reset for user {user.get('email')}: {total_credits} credits")
            return True
            
        except Exception as e:
            print(f"Error resetting credits: {str(e)}")
            return False
    
    def admin_adjust_credits(self, user_id, adjustment, admin_id, reason):
        """
        Admin function to add or deduct credits.
        
        Args:
            user_id: User ID
            adjustment: Credits to add (positive) or deduct (negative)
            admin_id: Admin user ID
            reason: Reason for adjustment
            
        Returns:
            bool: Success status
        """
        try:
            user = self.users_collection.find_one({'user_id': user_id})
            if not user:
                return False
            
            # Skip for unlimited credits
            if user.get('total_credits', 0) == -1:
                return True
            
            current_total = user.get('total_credits', 0)
            new_total = max(0, current_total + adjustment)
            
            credits_used = user.get('credits_used', 0)
            new_remaining = new_total - credits_used
            
            self.users_collection.update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        'total_credits': new_total,
                        'credits_remaining': new_remaining,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            # Log admin action
            log_entry = {
                'user_id': user_id,
                'admin_id': admin_id,
                'adjustment': adjustment,
                'reason': reason,
                'timestamp': datetime.utcnow()
            }
            
            self.credit_logs_collection.insert_one(log_entry)
            
            print(f"✓ Admin adjusted credits for user {user.get('email')}: {adjustment:+d}")
            return True
            
        except Exception as e:
            print(f"Error adjusting credits: {str(e)}")
            return False
