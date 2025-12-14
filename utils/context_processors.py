"""
Context processors for global template variables.
"""
from notifications.repo import get_unread_count
from django.db import connection


def personnel_notifications(request):
    """
    Add notification counts to template context for secretary and treasurer modules.
    Note: Recent notifications are fetched dynamically via API when modal opens.
    """
    context = {
        'unread_notifications_count': 0,
        'pending_payments_count': 0,
        'paid_payments_count': 0
    }
    
    # Only process for logged-in personnel
    if not hasattr(request, 'session') or not request.session.get('personnel_id'):
        return context
    
    personnel_id = request.session.get('personnel_id')
    role_name = request.session.get('role_name', '')
    
    try:
        # Get unread notification count for personnel
        unread_count = get_unread_count(
            user_type='PERSONNEL',
            personnel_id=personnel_id
        )
        context['unread_notifications_count'] = unread_count
        
        # For treasurer: get pending and paid payments count
        if 'Treasurer' in role_name:
            try:
                with connection.cursor() as cursor:
                    # Get pending payments count using the treasurer function
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM treasurer_get_all_application(NULL, 'Pending', NULL, 1000000, 0)
                    """)
                    result = cursor.fetchone()
                    context['pending_payments_count'] = result[0] if result else 0
                    
                    # Get paid payments count
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM treasurer_get_all_application(NULL, 'Paid', NULL, 1000000, 0)
                    """)
                    result = cursor.fetchone()
                    context['paid_payments_count'] = result[0] if result else 0
            except Exception as db_error:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting payment counts for treasurer: {db_error}")
                # Keep defaults at 0
    
    except Exception as e:
        # Log error but don't break the page
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in personnel_notifications context processor: {e}")
    
    return context
