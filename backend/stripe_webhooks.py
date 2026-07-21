"""
Stripe Webhook Handlers for SafeNet AI
=======================================
Handles Stripe webhook events for subscription management.
"""

import stripe
from datetime import datetime, timedelta
from pricing_config import get_plan_credits


def handle_checkout_completed(event_data, users_collection, credit_logs_collection, payments_collection=None):
    """
    Handle successful checkout session completion.
    This is called when a customer completes payment.
    
    Args:
        event_data (dict): Stripe event data
        users_collection: MongoDB users collection
        credit_logs_collection: MongoDB credit logs collection
        payments_collection: MongoDB payments collection (for revenue tracking)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        session = event_data['object']
        
        # Extract metadata
        user_id = session.get('metadata', {}).get('user_id')
        plan_name = session.get('metadata', {}).get('plan')
        
        if not user_id or not plan_name:
            return False, "Missing user_id or plan in metadata"
        
        # Get user from database
        user = users_collection.find_one({'user_id': user_id})
        if not user:
            return False, f"User not found: {user_id}"
        
        # Get plan credits
        plan_credits = get_plan_credits(plan_name)
        if plan_credits == 0:
            return False, f"Invalid plan: {plan_name}"
        
        # Calculate renewal dates
        now = datetime.utcnow()
        plan_activated_at = now
        reset_at = now + timedelta(days=30)
        
        # Get payment amount from session
        amount_total = session.get('amount_total', 0) / 100  # Convert from cents to rupees
        currency = session.get('currency', 'inr').upper()
        
        # Update user with new plan and credits
        users_collection.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'plan': plan_name,
                    'total_credits': plan_credits,
                    'credits_used': 0,
                    'credits_remaining': plan_credits,
                    'plan_activated_at': plan_activated_at,
                    'last_credit_renewal': plan_activated_at,
                    'next_credit_renewal': reset_at,
                    'stripe_customer_id': session.get('customer'),
                    'stripe_subscription_id': session.get('subscription'),
                    'payment_status': 'active',
                    'last_payment_date': now
                }
            }
        )
        
        # Save payment record for revenue tracking
        if payments_collection is not None:
            payment_record = {
                'user_id': user_id,
                'email': user.get('email'),
                'plan_name': plan_name,
                'amount': amount_total,
                'currency': currency,
                'payment_id': session.get('payment_intent') or session.get('id'),
                'stripe_session_id': session.get('id'),
                'stripe_customer_id': session.get('customer'),
                'stripe_subscription_id': session.get('subscription'),
                'payment_status': 'success',
                'payment_method': session.get('payment_method_types', ['card'])[0],
                'created_at': now,
                'metadata': {
                    'credits_granted': plan_credits,
                    'plan_activated_at': plan_activated_at,
                    'next_renewal': reset_at
                }
            }
            payments_collection.insert_one(payment_record)
            print(f"✓ Sales record created: ₹{amount_total} for {plan_name} plan (User: {user.get('email')})")
        else:
            print("⚠️ Warning: payments_collection is None, sales record not created")
        
        # Log credit addition
        if credit_logs_collection is not None:
            credit_logs_collection.insert_one({
                'user_id': user_id,
                'email': user.get('email'),
                'action': 'plan_upgrade',
                'plan': plan_name,
                'credits_added': plan_credits,
                'credits_before': user.get('credits', 0),
                'credits_after': plan_credits,
                'timestamp': now,
                'source': 'stripe_checkout',
                'stripe_session_id': session.get('id'),
                'stripe_customer_id': session.get('customer')
            })
        
        print(f"✓ Checkout completed for user {user.get('email')}: {plan_name} plan, {plan_credits} credits")
        return True, f"Successfully activated {plan_name} plan"
        
    except Exception as e:
        print(f"Error handling checkout completion: {str(e)}")
        return False, str(e)


def handle_invoice_payment_succeeded(event_data, users_collection, credit_logs_collection, payments_collection=None):
    """
    Handle successful invoice payment (recurring subscription renewal).
    This is called on monthly subscription renewals.
    
    Args:
        event_data (dict): Stripe event data
        users_collection: MongoDB users collection
        credit_logs_collection: MongoDB credit logs collection
        payments_collection: MongoDB payments collection (for revenue tracking)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        invoice = event_data['object']
        
        # Get customer and subscription
        customer_id = invoice.get('customer')
        subscription_id = invoice.get('subscription')
        
        if not customer_id:
            return False, "Missing customer ID"
        
        # Find user by Stripe customer ID
        user = users_collection.find_one({'stripe_customer_id': customer_id})
        if not user:
            return False, f"User not found for customer: {customer_id}"
        
        # Get current plan
        plan_name = user.get('plan', 'free')
        plan_credits = get_plan_credits(plan_name)
        
        if plan_credits == 0:
            return False, f"Invalid plan for renewal: {plan_name}"
        
        # Calculate new renewal dates
        now = datetime.utcnow()
        reset_at = now + timedelta(days=30)
        
        # Get payment amount from invoice
        amount_total = invoice.get('amount_paid', 0) / 100  # Convert from cents to rupees
        currency = invoice.get('currency', 'inr').upper()
        
        # Renew credits
        users_collection.update_one(
            {'user_id': user['user_id']},
            {
                '$set': {
                    'total_credits': plan_credits,
                    'credits_used': 0,
                    'credits_remaining': plan_credits,
                    'last_credit_renewal': now,
                    'next_credit_renewal': reset_at,
                    'last_payment_date': now,
                    'payment_status': 'active'
                }
            }
        )
        
        # Save payment record for revenue tracking
        if payments_collection is not None:
            payment_record = {
                'user_id': user['user_id'],
                'email': user.get('email'),
                'plan_name': plan_name,
                'amount': amount_total,
                'currency': currency,
                'payment_id': invoice.get('payment_intent') or invoice.get('id'),
                'stripe_invoice_id': invoice.get('id'),
                'stripe_customer_id': customer_id,
                'stripe_subscription_id': subscription_id,
                'payment_status': 'success',
                'payment_method': 'subscription_renewal',
                'created_at': now,
                'metadata': {
                    'credits_renewed': plan_credits,
                    'renewal_type': 'automatic',
                    'next_renewal': reset_at
                }
            }
            payments_collection.insert_one(payment_record)
            print(f"✓ Renewal sales record created: ₹{amount_total} for {plan_name} plan (User: {user.get('email')})")
        else:
            print("⚠️ Warning: payments_collection is None, renewal sales record not created")
        
        # Log credit renewal
        if credit_logs_collection is not None:
            credit_logs_collection.insert_one({
                'user_id': user['user_id'],
                'email': user.get('email'),
                'action': 'subscription_renewal',
                'plan': plan_name,
                'credits_added': plan_credits,
                'credits_before': user.get('credits', 0),
                'credits_after': plan_credits,
                'timestamp': now,
                'source': 'stripe_invoice',
                'stripe_invoice_id': invoice.get('id'),
                'stripe_customer_id': customer_id
            })
        
        print(f"✓ Subscription renewed for user {user.get('email')}: {plan_name} plan, {plan_credits} credits")
        return True, f"Successfully renewed {plan_name} plan"
        
    except Exception as e:
        print(f"Error handling invoice payment: {str(e)}")
        return False, str(e)


def handle_subscription_deleted(event_data, users_collection, credit_logs_collection):
    """
    Handle subscription cancellation.
    Downgrade user to Free plan.
    
    Args:
        event_data (dict): Stripe event data
        users_collection: MongoDB users collection
        credit_logs_collection: MongoDB credit logs collection
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        subscription = event_data['object']
        customer_id = subscription.get('customer')
        
        if not customer_id:
            return False, "Missing customer ID"
        
        # Find user by Stripe customer ID
        user = users_collection.find_one({'stripe_customer_id': customer_id})
        if not user:
            return False, f"User not found for customer: {customer_id}"
        
        # Downgrade to Free plan
        free_credits = get_plan_credits('free')
        now = datetime.utcnow()
        reset_at = now + timedelta(days=30)
        
        old_plan = user.get('plan', 'free')
        
        users_collection.update_one(
            {'user_id': user['user_id']},
            {
                '$set': {
                    'plan': 'free',
                    'total_credits': free_credits,
                    'credits_used': 0,
                    'credits_remaining': free_credits,
                    'last_credit_renewal': now,
                    'next_credit_renewal': reset_at,
                    'payment_status': 'canceled',
                    'subscription_canceled_at': now
                },
                '$unset': {
                    'stripe_subscription_id': ''
                }
            }
        )
        
        # Log downgrade
        if credit_logs_collection is not None:
            credit_logs_collection.insert_one({
                'user_id': user['user_id'],
                'email': user.get('email'),
                'action': 'subscription_canceled',
                'plan': 'free',
                'old_plan': old_plan,
                'credits_after': free_credits,
                'timestamp': now,
                'source': 'stripe_cancellation',
                'stripe_customer_id': customer_id
            })
        
        print(f"✓ Subscription canceled for user {user.get('email')}: downgraded to Free plan")
        return True, "Successfully downgraded to Free plan"
        
    except Exception as e:
        print(f"Error handling subscription deletion: {str(e)}")
        return False, str(e)


def handle_payment_failed(event_data, users_collection):
    """
    Handle failed payment.
    Mark user's payment status as failed.
    
    Args:
        event_data (dict): Stripe event data
        users_collection: MongoDB users collection
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        invoice = event_data['object']
        customer_id = invoice.get('customer')
        
        if not customer_id:
            return False, "Missing customer ID"
        
        # Find user by Stripe customer ID
        user = users_collection.find_one({'stripe_customer_id': customer_id})
        if not user:
            return False, f"User not found for customer: {customer_id}"
        
        # Update payment status
        users_collection.update_one(
            {'user_id': user['user_id']},
            {
                '$set': {
                    'payment_status': 'failed',
                    'last_payment_failed_at': datetime.utcnow()
                }
            }
        )
        
        print(f"⚠️ Payment failed for user {user.get('email')}")
        return True, "Payment failure recorded"
        
    except Exception as e:
        print(f"Error handling payment failure: {str(e)}")
        return False, str(e)
